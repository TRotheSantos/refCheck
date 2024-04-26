import os
import re

import chromadb
from chromadb.utils import embedding_functions
from django.utils.crypto import get_random_string
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_openai import ChatOpenAI
from langchain.llms.openai import OpenAI
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from RefCheck.settings import PERSISTENT_DIR


# Check if the OPENAI_API_KEY environment variable is set
# This key is required to communicate with the OpenAI API or at least set to "sk-" for LocalAI
# If it's not set, a RuntimeError is raised with a message instructing the user to set it
if "OPENAI_API_KEY" not in os.environ:
    raise RuntimeError("You need to set the OPENAI_API_KEY as a environemnt variable (configure in the .env file). It is also used for LocalAI. LocalAI only checks for 'sk-'")

# Check if the OPENAI_API_KEY environment variable is set to "sk-"
# If it is, it means the user wants to use LocalAI TODO: implement user configuration: initiating all covered models, then always using user specified one
# In this case, the LOCALAI_API_BASE and DEFAULT_MODEL environment variables also need to be set
# If they're not, a RuntimeError is raised with a message instructing the user to set them
if os.environ["OPENAI_API_KEY"] == "sk-" and ("LOCALAI_API_BASE" not in os.environ or "DEFAULT_MODEL" not in os.environ):
    raise RuntimeError("If you want to use LocalAI you also need to set LOCALAI_API_BASE and DEFAULT_MODEL as environemnt variables (configure in the .env file)")

"""
This block of code is responsible for initializing the language model (llm) that will be used for generating text. 
The type of model used depends on the value of the OPENAI_API_KEY environment variable.

If the OPENAI_API_KEY is set to "sk-", it means the user wants to use LocalAI, a local version of the OpenAI model. 
In this case, the OpenAI model is initialized with a temperature of 0, a DEFAULT_MODEL specified by the user, and a maximum token limit of 3000.

If the OPENAI_API_KEY is not set to "sk-", it means the user wants to use the ChatOpenAI model, which communicates directly with the OpenAI API. 
In this case, the ChatOpenAI model is initialized with a temperature of 0.0.

The temperature parameter controls the randomness of the model's output. 
A lower value like 0.0 makes the output more deterministic, while a higher value makes it more diverse.
"""
if os.environ["OPENAI_API_KEY"] == "sk-":
    llm = OpenAI(temperature=0,  DEFAULT_MODEL=os.environ["DEFAULT_MODEL"], max_tokens=3000)
else:
    llm = ChatOpenAI(temperature=0.0)


'''Chroma DB Setup and configuration of the embeddings we use'''
"""
Initialize the SentenceTransformerEmbeddings with the model "all-MiniLM-L6-v2". 
The SentenceTransformerEmbeddings is used to generate embeddings for the documents in the Chroma database.
"""
embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
if "OPENAI_EMBEDDING_MODEL" in os.environ:
    embeddings = embedding_functions.OpenAIEmbeddingFunction(api_key=os.environ["OPENAI_API_KEY"],
                                                             model_name=os.environ["OPENAI_EMBEDDING_MODEL"])



"""
Initialize the PersistentClient for the Chroma database. 
The PersistentClient is used to interact with the Chroma database.
"""
# TODO define ((only) external) http chroma client here (need to be configured in docker too), if used only need for $ pip install chromadb-client
# maybe then need to alter chroma calls to async (longer waiting times)
# https://docs.trychroma.com/usage-guide?lang=py#running-chroma-in-clientserver-mode
if "CHROMA_HTTP_HOST" in os.environ and "CHROMA_HTTP_PORT" in os.environ:
    client = chromadb.HTTPClient(os.environ["CHROMA_HTTP_HOST"], int(os.environ["CHROMA_HTTP_PORT"]))
else:
    client = chromadb.PersistentClient(str(PERSISTENT_DIR.joinpath("chromadb")))


def parseNewCollectionName(name: str):
    """
    Returns a collection name from given name, which is a valid collection name for a chroma db and free to use
    https://docs.trychroma.com/usage-guide#creating-inspecting-and-deleting-collections

    :param name: The name of the document to be embedded
    :return: valid and unique collection name
    """
    # replacing not allowed characters, consecutive dots and dots between numbers to prevent valid IP addresses
    cleaned_name = re.sub(r'[^a-zäöüßA-ZÄÖÜ0-9.\-_]|[.]{2,}|(?<=\d)\.(?=\d)', '_', name)
    # more restrictive constraints at the beginning and at the end
    cleaned_name = re.sub(r'^[^a-zäöüßA-ZÄÖÜ0-9]*|[^a-zäöüßA-ZÄÖÜ0-9]*$', '', cleaned_name)
    # length constraints
    if len(cleaned_name) > 63:
        cleaned_name = cleaned_name[:63]
    if len(cleaned_name) < 3:
        cleaned_name = "collection-" + cleaned_name
    # uniqueness
    if cleaned_name in [collection.name for collection in client.list_collections()]:
        cleaned_name = f"{cleaned_name[:59]}_{get_random_string(length=3)}"
        return parseNewCollectionName(cleaned_name)  # if somehow same unique string is appended again to existing name
    return cleaned_name


def createChromaCollection(document_name: str, chunked_document: list[Document]) -> tuple[str, Chroma]:
    """
    Creates a new langchain chroma collection with the documents name and returns
    the collection as langchain vectorstore and the possibly edited collection name (to be valid and unique).

    Note:
    The Chroma object is initialized with the following parameters:
    - embedding_function: The specified default embedding function used to generate embeddings for the documents.
    - persist_directory: (If local and not in http mode) the Chroma database is stored in the PERSISTENT_PATH.
    - client: The client used to interact with the Chroma database.

    :param document_name: The name of the document to be embedded as collection
    :param chunked_document: The into langchain Documents chunked document
    :return: The name of the created collection and the langchain chroma vectorstore
    """
    collection_name = parseNewCollectionName(document_name)
    ids = [str(doc.metadata["chunk_id"]) for doc in chunked_document]  # filterable chunk ids, 1-based
    client.create_collection(name=collection_name)
    return collection_name, Chroma.from_documents(chunked_document,
                                                  embedding=embeddings,
                                                  ids=ids,
                                                  collection_name=collection_name,
                                                  persist_directory=str(PERSISTENT_DIR.joinpath("chromadb")),
                                                  client=client)


def getChromaCollection(collectionName: str) -> Chroma:
    """
    Returns from persistence loaded langchain chroma DB vectorstore with the given collection.
    In langchain chroma DB is always instanced with only one collection.

    :param collectionName: The name of the collection the document got embedded in
    :return: langchain vector db associated with requested collection

    """
    return Chroma(collection_name=collectionName,
                  embedding_function=embeddings,
                  persist_directory=str(PERSISTENT_DIR.joinpath("chromadb")),
                  client=client)
