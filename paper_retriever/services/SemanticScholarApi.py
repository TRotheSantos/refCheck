from aiolimiter import AsyncLimiter

from paper_retriever.services.BasicApi import BasicApi
from paper_manager.models import Paper, FileFormat


class SemanticScholarApi(BasicApi):
    """
    SemanticScholarApi provides an interface to query the Semantic Scholar Graph API for academic papers.
    It leverages the BasicApi structure for making HTTP requests and handling responses, tailored specifically
    to the Semantic Scholar API's requirements, including endpoint configurations, response formats,
    and rate limiting.

    Attributes:
        BASE_URL (str): Base URL for the Semantic Scholar Graph API.
        SEARCH_ENDPOINT (str): Endpoint for searching papers in the Semantic Scholar database.
        RESPONSE_FORMAT (str): Expected response format (JSON).
        RATE_LIMIT (int): The maximum number of requests per time frame allowed by the API for unregistered users:
                          All unauthenticated users share a limit of 5,000 requests per 5 minutes = 300 seconds.
                          From these 5k requests, a single user can only use a maximum of 100 requests per 5 minutes.
                          -> Registration in future required to increase rate limits.
                          -> Well-formatted requests may fail unpredictably if the shared limit was reached in the 
                            current period.
        limiter (AsyncLimiter): An instance of AsyncLimiter to enforce rate limits.
    """
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    SEARCH_ENDPOINT = "/paper/search?"
    RESPONSE_FORMAT = "json"
    RATE_LIMIT = 100
    limiter = AsyncLimiter(RATE_LIMIT, 300)  

    @staticmethod
    def build_query(paper: Paper):
        """
        Constructs the search query parameters for the Semantic Scholar API based on a Paper instance's attributes.

        Parameters:
            paper (Paper): An instance of the Paper model containing the search criteria.

        Returns:
            dict: A dictionary containing the query parameters for the API request.
        """
        # The params should NOT be separated by a comma as the whitespace causes the request to fail.
        query_params = {'fields': 'title,authors,year,venue,url,isOpenAccess,openAccessPdf,publicationDate,journal,externalIds'}
        if paper.title:
            query_params['query'] = paper.title
        if paper.pub_year:
            query_params['year'] = paper.pub_year
        if paper.authors.exists():
            last_names = [author.name.split()[-1] for author in paper.authors.all()]
            query_params['authors'] = " OR ".join(last_names)
        return query_params

    @staticmethod
    def process_search_results(json_data, paper: Paper):
        """
        Processes the search results returned by the Semantic Scholar API to find matches based on a Paper instance.

        Parameters:
            data (dict): The JSON data returned by the Semantic Scholar API search query.
            paper (Paper): The Paper instance used as the search criteria.

        Returns:
            dict or None: A dictionary with the matched paper details or None if no match is found.
        """
        for result in json_data.get("data", []):
            if SemanticScholarApi.is_match(result, paper):
                return SemanticScholarApi.format_match_result(result)
        return None

    @staticmethod
    def is_match(result, paper: Paper):
        """
        Determines if a search result matches the given Paper instance based on the title.

        Parameters:
            result (dict): A single search result.
            paper (Paper): The Paper instance to match against.

        Returns:
            bool: True if the result matches the Paper instance, False otherwise.
        """
        title_match = paper.title.lower() == result.get("title", "").lower()
        return title_match
    
    @staticmethod
    def format_match_result(result):
        """
        Formats a matching search result into a structured dictionary for easier access and use.

        Parameters:
            result (dict): A dictionary representing a matching search result.

        Returns:
            dict: A dictionary containing formatted details of the matching result, including
                  source, title, open access status, links, DOI, and other relevant information.
        """
        title = result.get("title")
        authors = ", ".join([author.get('name', 'N/A') for author in result.get("authors", [])])
        year = result.get("year")
        venue = result.get("venue")
        url = result.get("url")
        isOpenAccess = result.get("isOpenAccess", False)
        openAccessPdf = result.get("openAccessPdf", {}).get("url")

        openAccessType = result.get("openAccessPdf", {}).get("status") # The Open Access color type (green, hybrid, gold,...).
        publicationDate = result.get("publicationDate")
        doi = result.get("externalIds", {}).get('DOI')
        journalDict = result.get("journal")
        journal = None if not journalDict else journalDict.get("name")

        returning = {
            'source': 'Semantic Scholar',
            'title': title,
            'open_access': isOpenAccess,
            'full_text_link': openAccessPdf,
            'doi_link': doi,

            # Optional attributes.
            'authors': authors.split(', '),
            'year': year,
            'venue': venue,
            'publicationDate': publicationDate,
            'journal': journal,
            'Semantic Scholar page': url,  # Link to the Semantic Scholar entry.
            'openAccessType': openAccessType
        }
        if openAccessPdf:
            returning['download_link'] = openAccessPdf
            returning['file_format'] = FileFormat.PDF

        return returning
