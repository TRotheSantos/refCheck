import asyncio
import os

import aiohttp  # required for the suggested doi link handling
import requests
from asgiref.sync import sync_to_async
from django.core.files.base import ContentFile
from langchain.text_splitter import TextSplitter, RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, UnstructuredFileLoader, UnstructuredMarkdownLoader, \
    UnstructuredHTMLLoader, UnstructuredEPubLoader, UnstructuredPowerPointLoader, \
    UnstructuredWordDocumentLoader, UnstructuredODTLoader, UnstructuredXMLLoader, TextLoader
from langchain_core.documents import Document

from RefCheck.settings import COPYRIGHT_LEVEL
from RefCheck.CopyrightLevels import CopyrightLevel
from llm.models import createChromaCollection, getChromaCollection
from paper_manager.models import Paper, FileFormat as Type, FileFormat
from paper_retriever.QueryEngine import QueryEngine
from paper_retriever.services.BasicApi import BasicApi
from paper_retriever.services.ArxivApi import ArxivApi
from paper_retriever.services.CoreApi import CoreApi
from paper_retriever.services.CrossrefApi import CrossrefApi
from paper_retriever.services.ElsevierApi import ElsevierApi
from paper_retriever.services.SemanticScholarApi import SemanticScholarApi
from paper_retriever.services.SpringerApi import SpringerApi
from paper_retriever.services.UnpaywallApi import UnpaywallApi  # required for the suggested doi link handling


class PaperImporter:
    """
    The PaperImporter class is designed to provide all the functionality to load and store a paper's content to enable further processing on the internal datastructure.
    It can crawl (delegated) & download PDF files from the web and attach them to a Paper model instance.
    This is useful in scenarios where academic papers or documents need to be programmatically downloaded and saved.
    Further it mainly extracts the text from the files with different langchain loaders, splits the text into chunks of
    required size and stores them in a vector store (Chroma) as collection.

    Attributes:
    - paper (Paper): The Paper object that is being imported.
    - query_engine (QueryEngine): The QueryEngine object used to crawls for a papers file and supplementary metadata.
    """

    def __init__(self, paper: Paper, query_engine: QueryEngine = None, apis: [BasicApi] = None):
        """
        Constructs a new PaperImporter instance.

        Parameters:
        - paper (Paper): The Paper object that is being imported.
        - query_engine (QueryEngine, optional): The QueryEngine object used to query APIs for paper information.
            If not provided, a default QueryEngine is created with list of given or default APIs.
        - apis (list, optional): A list of APIs to use if no QueryEngine is provided.
        """
        self.paper = Paper.objects.select_for_update().prefetch_related('authors').get(id=paper.id)
        self.query_engine = query_engine or QueryEngine(apis if apis else [ArxivApi(), CoreApi(), CrossrefApi(), ElsevierApi(), SemanticScholarApi(), SpringerApi()])
        # TODO: make default APIs User configurable via frontend/user settings

    async def obtain_paper(self, splitter: TextSplitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=50), insert_chunk_ids=False):
        """
        This method is an aggregator method that is responsible for obtaining a paper. Either way crawl source papers or load from stored source link.
        It first checks if the paper's source link or file exists. If not, it crawls APIs to obtain a source link
        to download from. On the way the paper information get updated with API data too.
        Then, it attempts to download the paper. On success, it imports the paper similar to the import_paper method.

        Parameters:
        - splitter (TextSplitter, optional): The text splitter to use for splitting the documents into chunks.
            If not provided, a RecursiveCharacterTextSplitter with a chunk size of 200 and a overlap of 50 is used.
        - insert_chunk_ids (bool, optional): Whether to insert the chunk ID into the page content of each chunk.
            Defaults to False. May/historically needed for some LLM processes.

        Returns:
        - tuple: A tuple containing the name of the Chroma collection (inspired by the name of the paper but
            maybe altered to match requirements) and the collection itself if the embedding is successful, else None.

        Note:
        This method is asynchronous and should be called with await in an async context, or using asyncio.run in a sync context.
        """

        # if there is already a source-link, paper is a website or already a downloaded file we don't need to crawl APIs
        # to force crawling and downloading a paper if file already exists, directly call crawls_apis and download
        if ((not self.paper.origin) or 'doi.org' in self.paper.origin) and not self.paper.file:
            # TODO define method to only crawl Unpaywall (optimized for DOI, finds a source if there is an open access version) in Query Engine
            '''
            if 'doi.org' in self.paper.origin:
                    async with aiohttp.ClientSession() as session:
                    unpaywall_result = await UnpaywallApi.query_api(self.paper, session)
                    if unpaywall_result and unpaywall_result.get('url_for_pdf'):
                        self.paper.origin = unpaywall_result['url_for_pdf']
                        await self.paper.asave()
            else:
            '''
            await self.async_crawl_apis()
        if not await self.download():
            return None
        return await self.embedd(splitter=splitter, insert_chunk_id=insert_chunk_ids)

    async def import_paper(self, splitter: TextSplitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200), insert_chunk_ids=False):  # TODO remove insert chunk ids
        """
        This method is responsible for importing a paper. It first loads the paper content from its file and
        then uses the embedd method to chunk, embedd and store the chunks in a vector store (Chroma) as a collection.

        Parameters:
        - splitter (TextSplitter, optional): The text splitter to use for splitting the documents into chunks. If not provided,
          a RecursiveCharacterTextSplitter with a chunk size of 1200 and a chunk overlap of 200 is used.
        - insert_chunk_ids (bool, optional): Whether to insert the chunk ID into the page content of each chunk. Defaults to False.

        Returns:
        - tuple: A tuple containing the name of the Chroma collection and the collection itself if the embedding is successful, None otherwise.

        Note:
        This method is asynchronous and should be called with await in an async context, or using asyncio.run in a sync context.
        """
        return await self.embedd(splitter=splitter, insert_chunk_id=insert_chunk_ids)  # includes loading & chunking

    def crawl_apis(self):
        """
        This method is a synchronous wrapper for the asynchronous method async_crawl_apis. It uses asyncio.run to
        execute the async_crawl_apis method in an event loop.
        """
        asyncio.run(self.async_crawl_apis())

    async def async_crawl_apis(self):
        """
            This asynchronous method is responsible for querying all APIs to obtain a source (link) to
            download the paper file from. It uses the query engine associated with the PaperImporter instance to query
            a set of APIs. On the way it also updates the paper with API data.

            Behavior:
            1. Calls the query_all_apis method of the query engine, passing the paper instance as an argument. This method
               queries all APIs for information about the paper.

            Note:
            This method is asynchronous and should be called with await in an async context, or using asyncio.run in a sync context.
            """
        # Asynchronous call to query APIs
        await self.query_engine.query_all_apis(self.paper)

    async def download(self, url: str = None):
        """
        Downloads a PDF from the URL stored in the Paper or if specified the provided URL and saves it in the
        Paper model instance, a users storage or refuses download according to copyright settings.

        Parameters:
        - url:optional A string representing the URL from which the PDF file should be downloaded. Setting this
            parameter enforces the download. Otherwise, would be skipped if file already exists.

        Behavior:
        1. Check if the COPYRIGHT_LEVEL allows downloading.
        2. If no URL is provided, downloads from the URL stored in the paper.
            -> enforce download & override by setting url, override & link update only on download success
        3. Sends a GET request to the provided URL.
        4. If the response status is 200 (OK), proceeds with the download.
        5. Either way saves the File with the Paper instance's title as filename in the
           'file' field of the Paper instance (server storage) or user storage (to be implemented).
        6. Updates the Paper instance's origin if the download succeeded from provided URL.

        Returns:
        - bool: True if the download was successful, False otherwise. The Paper instance is updated directly.

        Raises:
        - ConnectionError: Network-related exceptions can arise from the requests.get call.
        - Exception: Exceptions related to file handling and saving in Django models.
        """

        # TODO (in future): alter download restriction if download, analyze and delete afterwards again is possible too.
        if COPYRIGHT_LEVEL > CopyrightLevel.SAVE_TO_USER_STORAGE:
            return False

        if not url:  # option to enforce (re)download by setting url to origin
            if self.paper.file:
                return False
            url = self.paper.origin
            if not url or 'doi.org' in url: return False
        print("Try downloading from ", url)
        try:
            response = requests.get(url)
        except ConnectionError as e:
            print(e)
            return False

        if response.status_code == 200:
            if COPYRIGHT_LEVEL <= CopyrightLevel.DOWNLOAD:
                print("saving")
                CONTENT_TYPE_MAPPING = {
                    "text/plain": Type.TXT,
                    "text/html": Type.HTML,
                    "text/markdown": Type.MD,
                    "application/pdf": Type.PDF,
                    "application/epub+zip": Type.EPUB,
                    "application/msword": Type.DOCX,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": Type.DOCX,
                    "application/vnd.oasis.opendocument.text": Type.ODT,
                    "application/vnd.ms-powerpoint": Type.PPTX,
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation": Type.PPTX,
                    "application/xml": Type.XML,
                    "application/xhtml+xml": Type.XML,
                    "application/x-latex": Type.LATEX,
                    # "application/x-research-info-systems": Type.RIS,

                }
                content_type = response.headers.get('content-type').split(';')[0]
                print("content type: ", content_type)
                self.paper.file_format = CONTENT_TYPE_MAPPING.get(content_type, Type.UNDEFINED)  # this may require splitting of eg. ppt & pptx or doc & docx in class Type
                print("file format: ", self.paper.file_format)
                await sync_to_async(self.paper.file.save)(f"{self.paper.title}.{self.paper.file_format}", ContentFile(response.content))
                self.paper.origin = url
            else:
                # TODO (in future): save to user storage, set paper.origin to user storage url or temporarily download
                pass
            await self.paper.asave()
            return True
        return False

    async def load(self, filepath: str=None, url=None) -> list[Document] | None:
        """
        This method is responsible for loading a papers document file stored as attribute and optionally from
        a given file path or URL. In the later case, it updates corresponding attributes of the paper instance too.
        It uses a mapping of file types to specific loaders to handle different file formats.
        If the file format is not specified, it defaults to using the UnstructuredFileLoader.

        Parameters:
        - filepath (str, optional): The path to the file to be loaded. If not provided, the method will attempt to load
        the file from the URL or the file associated with the paper instance.
        - url (str, optional): The URL from which to load the document. If not provided, the method will attempt to load
        the file from the filepath or the file associated with the paper instance.

        Returns:
        - list[Document] | None: A list of Document objects if the loading is successful, None otherwise.

        Raises:
        - Exception: Any exceptions that occur during the loading process are caught and printed to the console.
        """
        # Mapping of file types to their respective loaders
        # file type: loader, additional kwargs, required resources ("path" if file with path, "url" if url is required)
        # langchain integrated loaders: https://python.langchain.com/docs/integrations/document_loaders/
        LOADER_MAPPING = {
            Type.DOCX: (UnstructuredWordDocumentLoader, {}, ["path"]),
            Type.EPUB: (UnstructuredEPubLoader, {"mode": "elements"}, ["path"]),  # maybe don't use elements mode
            # TODO load complete sitemap of a website, not only index page, analysis of best approach needed
            # Type.URL: (SeleniumURLLoader, {}, ["url"]),  # for only text, maybe need SeleniumURLLoader for js loaded content + HtmlToTextTransformer
            Type.HTML: (UnstructuredHTMLLoader, {}, ["path"]),  # alternatively use WebBaseLoader, UnstructuredHTMLLoader, 2markdown, AsyncHTMLLoader togehter withHtmlToTextTransformer, RecursiveUrlLoader or SitemapLoader since often only the base url is referenced to directly load from the url and not a downloaded html file
            # Type.HTML: (RecursiveUrlLoader, {"max_depth": 5, "extractor": lambda x: Soup(x, "html.parser").text}, ["url"]),  # TODO adopt parameters
            Type.MD: (UnstructuredMarkdownLoader, {"mode": "elements"}, ["path"]),  # maybe don't use elements mode
            Type.ODT: (UnstructuredODTLoader, {"mode": "elements"}, ["path"]),  # maybe don't use elements mode
            Type.PDF: (PyPDFLoader, {}, ["path", "url"]),  # TODO maybe alter to PyMuPDFLoader, pdfminerloader or on scientific papers ML-trained GrobidLoader https://python.langchain.com/docs/integrations/document_loaders/grobid
            Type.PPTX: (UnstructuredPowerPointLoader, {}, ["path"]),
            Type.TXT: (TextLoader, {"encoding": "utf8"}, ["path"]),
            Type.XML: (UnstructuredXMLLoader, {}, ["path"]),
        }

        # Determine the file format if it's undefined
        # https://stackoverflow.com/questions/77057531/loading-different-document-types-in-langchain-for-an-all-data-source-qa-bot
        # https://github.com/langchain-ai/langchain/discussions/9605
        print("File suffix: ", os.path.splitext(self.paper.file.path)[-1][1:])
        if self.paper.file_format == Type.UNDEFINED and os.path.splitext(self.paper.file.path)[-1][1:] in FileFormat.values:
            self.paper.file_format = FileFormat[os.path.splitext(self.paper.file.path)[-1][1:].upper()]
            await self.paper.asave()

        # Select the appropriate loader based on the file format
        if self.paper.file_format in LOADER_MAPPING:
            loader, kwargs, resources = LOADER_MAPPING[self.paper.file_format]
        else:
            loader, kwargs, resources = UnstructuredFileLoader, {}, ["path"]

        # Update the papers document with file from the given filepath if specified
        if filepath and filepath != self.paper.file.path and "path" in resources:
            try:
                docs = await sync_to_async(loader(filepath, **kwargs).load)()
                # if succeeded (no exception) save file to paper instance
                with open(filepath, 'rb') as f:
                    self.paper.file.save(f"{self.paper.title}.{self.paper.file_format}", ContentFile(f.read()))
                if not self.paper.origin:
                    self.paper.origin = filepath
                self.paper.save()
                return docs
            except Exception as e:
                print(e)

        # Download the document from the given URL if specified
        if url and url != self.paper.origin:
            await self.download(url)

        # Load the document from the (updated) file associated with the paper instance
        if self.paper.file and "path" in resources:
            try:
                docs = await sync_to_async(loader(self.paper.file.path, **kwargs).load)()
                self.paper.pages = len(docs)
                await self.paper.asave()
                return docs
            except Exception as e:
                print(e)
                return None

        # Load the document from the (updated) URL associated with the paper instance
        elif self.paper.origin and "url" in resources:
            try:
                loader_instance = loader([url], **kwargs)
                if hasattr(loader_instance, 'aload') and callable(getattr(loader_instance, 'aload')):  # check if async load is available
                    docs = await loader_instance.aload()
                else:
                    docs = await sync_to_async(loader_instance.load)()
                self.paper.pages = len(docs)
                await self.paper.asave()
                return docs
            except Exception as e:
                print(e)
        return None

    async def embedd(self, splitter: TextSplitter = None, docs: list[Document] = None, insert_chunk_id=False, filepath: str = None, url=None):
        """
        This method is responsible for chunking the papers extracted documents and embedding the chunks in
        a vector store (Chroma) as a collection associated with the paper.

        :param splitter: The text splitter to use for splitting the documents into chunks, instantiated with required
            splitting parameters. If not provided, a RecursiveCharacterTextSplitter with a chunk size of 600 and
            chunk overlap of 100 is used.
        :param docs: The list of loaded documents to embedd. If not provided, the method will attempt to load the
            documents from the papers file or if provided, from the given filepath or URL.
        :param insert_chunk_id: Whether to insert the chunk ID into the page content of each chunk. Defaults to False.
        :param filepath: The path to the file to load from.
            Passed to the load method and only used if (re)load is required (no or empty docs).
        :param url: The URL from which to load the paper.
            Passed to the load method and only used if (re)load is required (no or empty docs).
        :return: A tuple containing the name of the Chroma collection (inspired by the name of the paper but
            maybe altered to match requirements) and the collection itself if the embedding is successful, else None.
        """
        if not splitter:
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        if not docs:
            docs = await self.load(filepath, url)
            if not docs:
                return None
        chunks = splitter.split_documents(docs)
        if not chunks:  # may occur if document(s) were empty
            return None

        # For every chunk add the chunk ID to page content
        for i, chunk in enumerate(chunks, 1):
            chunk.metadata["chunk_id"] = i
            if insert_chunk_id:
                chunk.page_content = "chunk_id = " + str(i) + "\n\n" + chunk.page_content
        if self.paper.chroma_collection:
            getChromaCollection(self.paper.chroma_collection).delete_collection()
        collection_name, collection = createChromaCollection(self.paper.title, chunks)
        self.paper.chroma_collection = collection_name
        await self.paper.asave()
        print("embedd in: ", collection_name)
        return collection, chunks
