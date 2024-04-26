import asyncio
import json

from asgiref.sync import sync_to_async
from langchain_community.vectorstores.chroma import Chroma

from llm import models as llm_module
from paper_analytics import prompts_compare
from paper_manager.models import Paper, Source, Check


class PaperChecker:
    used_source_chunks = 10


    def __init__(self, paper: Paper, ):
        self.paper = paper

    async def score(self, new_source_papers: [Paper] = None):
        """
        Scores all citations the (new) source papers are referenced by. If those are not specified, all source papers
        of the wrapped paper are scored.
        :param new_source_papers: the source papers that now are imported and can be used to score referencing citations
        :return: void, but the checks and references are directly updated in the database
        """
        if not new_source_papers:
            new_source_papers = await self.get_source_papers()
        print(new_source_papers)
        await asyncio.gather(*[self.score_source_paper(paper) for paper in new_source_papers[:]])

    @staticmethod
    async def score_source_paper(new_source_paper: Paper):
        """
        Scores all bibliography entries (with the citations that link to it) that reference/represent the given paper
        :param new_source_paper: the paper to be processed whose file got (recently) added/embedded
        """
        if not new_source_paper.chroma_collection:
            return
        chroma = llm_module.getChromaCollection(new_source_paper.chroma_collection)
        sources = await PaperChecker.get_source_references(new_source_paper)
        await asyncio.gather(*[PaperChecker.score_source(source, chroma) for source in sources])

    @staticmethod
    async def score_source(source: Source, chroma: Chroma = None):
        """
        Scores the similarity between the sources citations and the source paper
        :param source: the source whose linking citations are to be checked
        :param chroma: the chroma collection of the sources paper
        """
        if not chroma:
            source_paper = await sync_to_async(getattr)(source, 'paper')
            chroma = llm_module.getChromaCollection(source_paper.chroma_collection)
            print("Chroma: ", chroma)
        checks = await PaperChecker.get_checks(source)
        await asyncio.gather(*[PaperChecker.score_check(check, chroma) for check in checks])

    @staticmethod
    async def score_check(check: Check, chroma: Chroma):  # TODO add constraints like pages
        """
        Scores the similarity between the check/citation and the source paper
        :param check: the check to be scored
        :param chroma: the chroma collection of the sources paper
        """
        citation = await sync_to_async(getattr)(check, 'citation')
        reference = await sync_to_async(getattr)(check, 'reference')
        relevant_chunks = await chroma.asimilarity_search(citation.text, PaperChecker.used_source_chunks)  # maybe use similarity search with relevance score as indicator or to check the llm response for a too high gap?
        chunk_string = ""
        for chunk in relevant_chunks:
            chunk_string += f"chunk {chunk.metadata['chunk_id']}:\n\"{chunk.page_content}\"\n"
        # TODO seperate scoring in multiple steps: 1. extract the validating passage and corresponding chunk_id
        #                                          2. score the passage including an explanation
        prompt = prompts_compare.score_claim_prompt.format(claim=citation.text, chunks=chunk_string)
        llm_return = (await llm_module.llm.ainvoke(prompt)).content  # TODO .content only for openAI --> use lanchain Chain
        print("Prompt:")
        print(prompt)
        print(llm_return)
        try:
            check_json = json.loads(llm_return)
        except json.JSONDecodeError:
            print(f"LLM return {llm_return} is not a valid json")
            return
        print(check_json)
        check.score = check_json['score']
        # TODO set default differences for score of 100 & 0
        check.difference_short = check_json['explanation-short']
        check.semantic_difference = check_json['explanation']
        if check_json['chunk_id']:
            try:
                reference.reference_paper_chunk_id = int(check_json['chunk_id'])
            except ValueError:
                print(f"LLM return {check_json['chunk_id']} is not a valid chunk id")
                reference.reference_paper_chunk_id = relevant_chunks[0].metadata['chunk_id']  # TODO use string search to find the correct chunk
        reference.extraction = check_json['proof']
        await check.asave()
        await reference.asave()
        print("Relevant chunks:")
        print(relevant_chunks)
        # print("Check: ", check)
        print("Citation: ", citation)
        print("Reference: ", reference)

   # Helper functions to query objects from the database in an asynchroneous context
    @sync_to_async
    def get_source_papers(self) -> [Paper]:
        return list(Paper.objects.filter(chroma_collection__isnull=False,
                                    source_references__referenced_in=self.paper).distinct())

    @staticmethod
    @sync_to_async
    def get_source_references(paper: Paper) -> [Source]:
        return list(Source.objects.filter(paper=paper).distinct())

    @staticmethod
    @sync_to_async
    def get_checks(source: Source) -> [Check]:
        return list(Check.objects.prefetch_related('citations', 'references').filter(false_positive=False, references__source=source).distinct())
