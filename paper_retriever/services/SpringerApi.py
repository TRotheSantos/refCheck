import os

from aiolimiter import AsyncLimiter

from paper_retriever.services.BasicApi import BasicApi
from paper_manager.models import Paper, FileFormat


class SpringerApi(BasicApi):
    """
    SpringerApi provides an interface to interact with the Springer Nature API for academic papers.
    It extends BasicApi, customizing it for Springer's API specifics, such as endpoint configurations,
    response formats, API key handling, and rate limiting.

    Attributes:
        BASE_URL (str): The base URL for the Springer Nature API.
        SEARCH_ENDPOINT (str): An empty string as Springer API does not use a specific search endpoint.
                               The "None" string problem when building the query is avoided in BasicApi class.
        RESPONSE_FORMAT (str): The expected response format, set to 'json'.
        API_KEY (str): The API key for authenticating requests to the Springer API.
        PARAMS (dict): A dictionary containing the API key to be included in query parameters.
                       Note: Springer wants the key in params not inside the header!
        RATE_LIMIT (int): The number of requests per minute allowed by the API: 300 calls per minute
        limiter (AsyncLimiter): An instance of AsyncLimiter to enforce rate limits.
    """
    BASE_URL = "http://api.springernature.com/meta/v2/json"
    SEARCH_ENDPOINT = ""
    RESPONSE_FORMAT = "json"
    API_KEY = os.environ.get('SPRINGER_API_KEY')
    PARAMS = {'api_key': API_KEY}
    RATE_LIMIT = 300
    limiter = AsyncLimiter(RATE_LIMIT, 60)

    @staticmethod
    def build_query(paper: Paper):
        """
        Constructs the search query for the Springer API based on a Paper instance's attributes.

        Parameters:
            paper (Paper): An instance of the Paper model containing the search criteria.

        Returns:
            dict: A dictionary with the constructed query to be used in the API request.
        """
        query_parts = [f"title:\"{paper.title}\""]
        if paper.authors.exists():
            # Extract last names, enclose them in quotes with name:, and join with OR.
            author_queries = [f"name:\"{author.name.split()[-1]}\"" for author in paper.authors.all()]
            authors_query = " OR ".join(author_queries)
            query_parts.append(f"({authors_query})")

        # TODO: Add a publication year check.
        # Uncomment the following lines if publication year is to be included in the search query. 
        # if paper.pub_year:
        #     query_parts.append(f"year:{paper.pub_year}")
        # Year issues are currently preventing a check as Springer seems to default to setting dates to the first 
        # day of the year a paper was featured on Springer instead of the actual publication date (?).
        # -> Unable to fix this issue yet. Should be tackled in the future.
        
        full_query = " AND ".join(query_parts)
        return {'q': full_query}
    
    @staticmethod
    def process_search_results(json_data, paper: Paper):
        """
        Processes the search results returned by the Springer API to find matches based on a Paper instance.

        Parameters:
            data (dict): The JSON data returned by the Springer API search query.
            paper (Paper): The Paper instance used as the search criteria.

        Returns:
            dict or None: A dictionary with the matched paper details or None if no match is found.
        """
        for result in json_data.get("records", []):
            if SpringerApi.is_match(result, paper):
                return SpringerApi.format_match_result(result)
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
        title_match = paper.title.lower() in result.get("title", "").lower()
        return title_match

    @staticmethod
    def format_match_result(result):
        """
        Formats a matching search result into a structured dictionary for easier access and use.

        Parameters:
            result (dict): A dictionary representing a matching search result.

        Returns:
            dict: A dictionary containing formatted details of the matching result, including
                  source, title, open access status, full text and download links, and DOI information.
        """
        title = result.get("title", None)
        oa_status = result.get("openaccess", False)
        doi = result.get("identifier", "").split("doi:")[-1]
        doi_link = f"https://doi.org/{doi}" if doi else None

        # Go trough all url entries in matching record and find a "pdf" entry. 
        # -> Found entries can be used for downloading and displaying.
        full_text_link = next((url["value"] for url in result.get("url", []) if url["format"] == "pdf"), None)
        download_link = full_text_link

        returning = {
            'source': 'Springer Nature',
            'title': title,
            'open_access': oa_status,
            'full_text_link': full_text_link,
        }
        if download_link:
            returning['download_link'] = download_link
            returning['file_format'] = FileFormat.PDF
        if doi:
            returning['doi_link'] = doi_link
        return returning
