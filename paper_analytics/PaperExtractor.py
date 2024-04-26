import asyncio
import time
import json
import re

from asgiref.sync import sync_to_async
from langchain.chains.base import Chain
from langchain_core.documents import Document
from langchain.chains import create_extraction_chain, LLMChain

from llm import models as llm_module
from paper_analytics.SourceMatcher import SourceMatcher
from paper_manager.models import Paper, Source, Check, CitationStyle
from paper_analytics import prompts_extract_claims as claim_prompts, prompts_bibliography as bib_prompts
from paper_retriever.PaperImporter import PaperImporter

"""
The extractor was mainly developed using IEEE and APA citation style, but a recently added function for querying
the extraction of citations/claims is missing the APA specific component of splitting citation marker that contain 
multiple references, so it is not fully functional for APA citation style yet.
"""


class PaperExtractor:
    @staticmethod
    def docs_list_to_dict(docs_list) -> dict[int, Document]:
        """
        helper function to convert a list of documents to a dictionary to easily access chunks by id.
        :param docs_list:
        :return:
        """
        return {doc.metadata["chunk_id"]: doc for doc in docs_list}
    @staticmethod
    def chroma_get_chunks_to_docs_dict(chroma_get) -> dict[int, Document]:
        """
        helper function to convert the chroma get result to a dictionary of chunk_id: Document, since the chroma get
        result not the best format.
        :param chroma_get: The reusult of a chroma get query
        :return: the parsed dictionary
        """
        # maybe need to alter to list
        return {int(chunk[0]): Document(page_content=chunk[1], metadata=chunk[2] or {}) for chunk in zip(chroma_get["ids"], chroma_get["documents"], chroma_get["metadatas"])}

    def __init__(self, paper: Paper, chromadb=None, chunked_document: list[Document] = None, llm=None):
        self.paper = paper
        self.chroma = chromadb or llm_module.getChromaCollection(self.paper.chroma_collection) if self.paper.chroma_collection else None
        if chunked_document:
            self.chunked_document = self.docs_list_to_dict(chunked_document)
        else:
            self.chunked_document = self.chroma_get_chunks_to_docs_dict(self.chroma.get())
        self.first_bib_chunk_id = None
        self.last_bib_chunk_id = None
        self.llm = llm or llm_module.llm
        # TODO extend for other types and engineer default prompt for unknown citation style
        # the citation style specific prompts for the different llm queries
        self.clean_bib_chunks = {CitationStyle.IEEE: bib_prompts.cleaning_prompt_with_identifier, CitationStyle.APA: bib_prompts.cleaning_prompt, CitationStyle.UNKNOWN: bib_prompts.cleaning_prompt}
        self.extract_bib_prompts = {CitationStyle.IEEE: bib_prompts.extraction_prompt_IEEE, CitationStyle.APA: bib_prompts.extraction_prompt___, CitationStyle.UNKNOWN: bib_prompts.extraction_prompt___}
        self.extract_claims_prompts = {CitationStyle.IEEE: claim_prompts.extraction_prompt_IEEE, CitationStyle.APA: claim_prompts.APA}
        # RegEx functions for citation marker extraction from the checked paper
        self.citation_marker_extractor = {CitationStyle.IEEE: self.extract_ieee_citation_marker, CitationStyle.APA: self.extract_apa_citation_marker}
        # RegEx functions for splitting aggregated citation markers to store a Check for all combinations of
        # the citation with each associated marker. Not necessary, but then the retrieval has to operate on multiple
        # chroma collections and collect the most relevant of each referenced source
        self.citation_marker_splitter = {CitationStyle.IEEE: self.split_ieee_citation_marker, CitationStyle.APA: self.split_apa_citation_marker}
        # definition of the entity schemas for extracting them with function calling
        self.source_schema = {
            "properties": {
                "reference": {"type": "string"},
                "title": {"type": "string"},
                "authors": {"type": "array", "items": {"type": "string"}},
                "identifier": {"type": "string"},
                "publisher": {"type": "string"},
                "year": {"type": "integer"},
                "url": {"type": "string"},
                "pages": {"type": "string"},
                "location": {"type": "string"},
                "volume": {"type": "string"},
                "ISBN": {"type": "string"},
                "DOI": {"type": "string"},
                "type": {"type": "string"},
                "language": {"type": "string"},
            },
            "required": ["reference", "title", "authors"],
        }
        self.check_schema = {
            "properties": {
                "claim": {"type": "string"},
                "citation_marker": {"type": "string"},
                "type": {"type": "string"},
            },
            "required": ["claim", "citation_marker", "type"],
        }

    async def extract(self):
        print("Extracting")
        # maybe change whole process from parallelized steps to parallelized pipeline/queues of each chunk includig the whole process with asyncio.Queue()
        obtain_paper_tasks = []

        # first extract bibliography entries and claims
        # await asyncio.gather(self.extract_bibliography(obtain_paper_tasks), self.extract_claims())
        # for testing purposes only run worked on processes
        await self.extract_claims()
        # await self.extract_bibliography(obtain_paper_tasks)

        # then match citations with sources while querying the APIs and importing found source files
        await asyncio.gather(*obtain_paper_tasks, SourceMatcher.match_refs_and_sources(self.paper))

    async def extract_bibliography(self, query_task_list: list[asyncio.Task]):
        print("Extracting Bibliography")
        self.calculate_bibliography_scope()
        bibliography = self.get_bibliography_chunks()
        print("Bibliography: ", bibliography)

        # Improvement: Maybe self create extraction chain for improved function specification
        start_time = time.time()
        cleaning_chain = LLMChain(llm=self.llm, prompt=self.clean_bib_chunks[self.paper.citation_style], verbose=True)
        extraction_chain = create_extraction_chain(self.source_schema, self.llm, bib_prompts.extraction_prompt___, verbose=True)

        # Parallelized extracting of the bibliography entries for each chunk
        for chunk_extraction in asyncio.as_completed([self.extract_bib_chunk(cleaning_chain, extraction_chain, chunk) for chunk in bibliography.values()]):
            chunk_id, entry_list = await chunk_extraction
            print(f"llm_returns for chunk {str(chunk_id)}: ", entry_list)

            # Parallelized creating of the source & source-paper objects and pdf retrieval for each entry
            for source_creation in asyncio.as_completed([Source.from_json(self.paper, json_representation, chunk_id) for json_representation in entry_list["text"]]):
                source, paper = await source_creation
                if not paper:
                    continue
                print(f"source creation for chunk {chunk_id}: ", source, paper)

                # Parallelized pdf retrieval for each source-paper
                importer = await sync_to_async(PaperImporter)(paper)
                query_task_list.append(asyncio.create_task(importer.obtain_paper()))

    async def extract_bib_chunk(self, cleaning_chain: Chain, extraction_chain: Chain, chunk: Document) -> (int, list[dict]):
        # TODO: improve prompts (especially also extracting the citation marker) and the interaction between the two prompts
        cleaned_chunk = await cleaning_chain.ainvoke({"bib_chunk": chunk.page_content})
        print(f"cleaned_chunk for chunk {str(chunk.metadata['chunk_id'])}: ", "\n", cleaned_chunk, "\n", chunk.page_content)
        return int(chunk.metadata["chunk_id"]), await extraction_chain.ainvoke({"bib_chunk": cleaned_chunk})
        # return int(chunk.metadata["chunk_id"]), await extraction_chain.ainvoke({"bib_chunk": cleaned_chunk})

    async def extract_claims(self):
        print(".\n.\n.\n.")
        print("--- EXTRACTION OF CLAIMS (function calling)")
        chunks = self.get_content_chunks()

        chain = create_extraction_chain(self.check_schema,
                                        self.llm,
                                        claim_prompts.extraction_prompt_IEEX,   # hier APA
                                        verbose=False)
        for chunk_extraction in asyncio.as_completed([self.extract_content_chunk_claims(chain, chunk) for chunk in chunks.values()]):
            chunk_id, llm_output = await chunk_extraction
            print(f"llm_returns for chunk {str(chunk_id)}: ", json.dumps(llm_output["text"], indent=4))
            if not llm_output["text"]:
                continue
            for extraction in llm_output["text"]:
                for marker in self.citation_marker_splitter[self.paper.citation_style](extraction["citation_marker"]):
                    # directly await since creation way faster than chunk extraction
                    await Check.from_extraction(self.paper, chunk_id, extraction["claim"], marker, extraction.get("type", "Unknown"))

    async def extract_content_chunk_claims(self, chain: Chain, chunk: Document) -> (int, list[dict]):
        marker = self.citation_marker_extractor[self.paper.citation_style](chunk.page_content)
        if not marker:
            return int(chunk.metadata["chunk_id"]), {"text_chunk": chunk.page_content, "marker": marker, "text": []}
        # maybe implement 2-step extraction: 1. extract list of claim-marker tuples with one claim for each marker
        #                                    2. extract citations type
        return int(chunk.metadata["chunk_id"]), await chain.ainvoke({"text_chunk": chunk.page_content, "marker": marker}, verbose=True)

    @staticmethod
    def extract_ieee_citation_marker(text) -> list[str]:
        # Define IEEE citation pattern for single or multiple references
        pattern = r'\[\s*\d+\s*(?:,\s*\d+\s*)*\]'

        # Find all matches using regular expression
        citations = re.findall(pattern, text)

        if not citations:
            return []

        return citations

    @staticmethod
    def split_ieee_citation_marker(marker):
        return ["[" + i + "]" for i in re.findall(r'\d+', marker)]

    @staticmethod
    def extract_apa_citation_marker(text):
        # Define APA citation pattern for single or multiple references
        pattern = r'\((?:[A-Za-z]+(?:\s+et al\.)?,?\s\d+(?:;\s[A-Za-z]+(?:\s+et al\.)?,\s\d+)*)\)'

        # Find all matches using regular expression
        citations = re.findall(pattern, text)

        return citations

    @staticmethod
    def split_apa_citation_marker(marker):
        raise NotImplementedError("APA citation marker splitting not implemented yet")
        # return []  # TODO implement

    async def categorize_chunks(self):
        """
        Categorizes the chunks of the paper into bibliography and content chunks using the LLM model. This makes the
        current required user input of the first and last bibliography entry obsolete and
        simplifies the process for the user.
        :param citation_style:
        :return:
        """
        # TODO integrate this method, either way substitute calculate_bibliography_scope or
        # integrate the LLM query into a method extract chunk that calls the functionality of
        # within extract_bibliography or extract_claims based on the category
        content_chunks = []
        biblio_chunks = []

        for chunk in self.chunked_document:
            if self.paper.citation_style == "APA":
                prompt = "Can you find a list of academic papers or articles in this string? Respond 'yes' or 'no', only one word \n"
            elif self.paper.citation_style == "IEEE":                   # IEEE
                prompt = "is there a bibliography in this string? Respond 'yes' or 'no', only one word \n"
            else: # UNKNOWN
                prompt = "is there a bibliography in this string? Respond 'yes' or 'no', only one word \n"
            category_prompt = prompt + "this is the text: \n" + chunk.page_content
            response = llm_module.llm.invoke(category_prompt).content
            if "yes" in response.lower():
                biblio_chunks.append(chunk)
            else:
                content_chunks.append(chunk)

        return content_chunks, biblio_chunks

    def calculate_bibliography_scope(self):
        # self.first_bib_chunk_id = self.chroma.get(where_document={"$contains": self.paper.start_bibliography}, limit=1)["ids"][0]
        # print("first id", self.first_bib_chunk_id)
        # self.last_bib_chunk_id = self.chroma.get(where_document={"$contains": self.paper.end_bibliography}, limit=1)["ids"][0]
        # print("last id", self.last_bib_chunk_id)

        # similarity_search instead of actual string comparison/filtering to be resilient against
        # misspellings & import/loading errors
        self.first_bib_chunk_id = int(self.chroma.similarity_search(self.paper.start_bibliography, k=1)[0].metadata["chunk_id"])
        self.last_bib_chunk_id = int(self.chroma.similarity_search(self.paper.end_bibliography, k=1)[0].metadata["chunk_id"])
        if self.first_bib_chunk_id > self.last_bib_chunk_id:
            raise ValueError("bibliography entries incorrect - firstEntry must be before lastEntry, may due to incorrect similarity search, try to play with the scope of the entered bibliography entries")
        # working on cached chunks for performance gains, could actually work on the chroma db directly
        # return self.chroma_get_chunks_to_docs_dict(self.chroma.get(where={"$gte": firstID, "$lte": lastID}, include=["metadata", "documents"]))

    def get_bibliography_chunks(self) -> dict[int, Document]:
        if not (self.first_bib_chunk_id and self.last_bib_chunk_id):
            self.calculate_bibliography_scope()
        return {id: doc for id, doc in self.chunked_document.items() if self.first_bib_chunk_id <= id <= self.last_bib_chunk_id}
        # working on cached chunks for performance gains, could actually work on the chroma db directly
        # return self.chroma.get(where={"chunk_id":{"$in": [self.first_bib_chunk_id, self.last_bib_chunk_id]}})

    def get_content_chunks(self) -> dict[int, Document]:
        if not (self.first_bib_chunk_id and self.last_bib_chunk_id):
            self.calculate_bibliography_scope()
        return {id: doc for id, doc in self.chunked_document.items() if id <= self.first_bib_chunk_id or id >= self.last_bib_chunk_id}
