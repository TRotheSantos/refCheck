import os

from aiolimiter import AsyncLimiter

from paper_retriever.services.BasicApi import BasicApi
from paper_manager.models import Paper, FileFormat


class CoreApi(BasicApi):
    """
    CoreApi provides an interface to query the CORE API for academic papers.
    It extends BasicApi, using its structure for making HTTP requests and handling responses,
    tailored specifically to the CORE API's requirements, including endpoint configurations,
    response formats, and rate limiting.

    Attributes:
        BASE_URL (str): The base URL for the CORE API.
        SEARCH_ENDPOINT (str): The endpoint for searching works in the CORE database.
        RESPONSE_FORMAT (str): The expected response format (JSON).
        API_KEY (str): The API key for authenticating requests to the CORE API.
        HEADERS (dict): Headers to include in the API request, including Authorization.
        PARAMS (dict): Default parameters to include in every search request.
        RATE_LIMIT (int): The maximum number of requests per minute allowed: 60 requests per minute.
        limiter (AsyncLimiter): An instance of AsyncLimiter to enforce rate limits.
    """
    BASE_URL = "https://api.core.ac.uk/v3/"
    SEARCH_ENDPOINT = "search/works?"
    RESPONSE_FORMAT = "json"
    API_KEY = os.environ.get("CORE_API_KEY")
    HEADERS = {"Authorization": f"Bearer {API_KEY}"}
    PARAMS = {"limit": 5}
    RATE_LIMIT = 10
    limiter = AsyncLimiter(RATE_LIMIT, 60)
        
    @staticmethod
    def build_query(paper: Paper):
        """
        Constructs a query for the CORE API based on a Paper instance's attributes.

        Parameters:
            paper (Paper): An instance of the Paper model containing the search criteria.

        Returns:
            dict: A dictionary containing the query parameter for the API request.
        """
        query_parts = []
        if paper.title:
            query_parts.append(f'title:"{paper.title}"')
        if paper.authors.exists():
            authors_query = " OR ".join([f'authors:"{author.name.split()[-1]}"' for author in paper.authors.all()])
            query_parts.append(f"({authors_query})")
        if paper.pub_year:
            query_parts.append(f'yearPublished:{paper.pub_year}')

        query = " AND ".join(query_parts) # Documentation recommends using a single query string inside params.
        return {"q": query}

    @staticmethod
    def process_search_results(json_data, paper: Paper):
        """
        Processes the search results returned by the CORE API.

        Parameters:
            data (dict): The JSON data returned by the CORE API.
            paper (Paper): The Paper instance used as the search criteria.

        Returns:
            dict or None: A dictionary with the matched paper details or None if no match is found.
        """
        results = json_data.get('results', [])
        for result in results:
            if CoreApi.is_match(result, paper):
                return CoreApi.format_match_result(result)
        return None

    @staticmethod
    def is_match(result, paper: Paper):
        """
        Determines if a search result matches the search criteria.

        Parameters:
            result (dict): A dictionary representing a single search result.
            paper (Paper): The Paper instance used as the search criteria.

        Returns:
            bool: True if the result matches the criteria, False otherwise.
        """
        result_title = result.get('title', '').lower().strip()
        paper_title = paper.title.lower().strip()
        title_match = result_title == paper_title

        year_match = True
        if paper.pub_year:
            result_year = result.get('yearPublished')
            year_match = result_year == paper.pub_year

        return title_match and year_match

    @staticmethod
    def format_match_result(result):
        """
        Formats a matching search result into a structured dictionary.

        Parameters:
            result (dict): A dictionary representing a matching search result.

        Returns:
            dict: A dictionary containing formatted details of the matching result.
        """
        # TODO: Fix the unclear download issue.
        # This is a "working" full text link based on the documentation and was checked multiple times.
        # However, downloading still doesn't work for unclear reasons. It was tried with GET requests according to API.
        # -> Try to fix this in the future to provide a working download functionality for CORE links.
        download_link = result.get('downloadUrl')
        returning = {
            'source': 'CORE',
            'title': result.get('title'),
            'open_access': result.get('isOpenAccess', False),
            'download_link': result.get('fullTextLink'),
            'full_text_link': result.get('fullTextLink'),
            'doi_link': "https://doi.org/" + result.get('doi'),
        }
        if download_link:
            returning['download_link'] = download_link
            returning['file_format'] = FileFormat.PDF
        return returning
