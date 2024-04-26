import os
import urllib

from aiolimiter import AsyncLimiter

from paper_retriever.services.BasicApi import BasicApi
from paper_manager.models import Paper, FileFormat


class ElsevierApi(BasicApi):
    """
    ElsevierApi provides an interface to interact with the Elsevier ScienceDirect Search API.
    It extends BasicApi, adapting it to handle requests to Elsevier's API, including constructing
    search queries, processing results, and handling rate limits.

    Attributes:
        BASE_URL (str): The base URL for the Elsevier ScienceDirect Search API.
        SEARCH_ENDPOINT (str): The endpoint for querying the API.
        RESPONSE_FORMAT (str): The format of the response data, expected to be JSON.
        API_KEY (str): The API key used for authentication with the Elsevier API.
        HEADERS (dict): Headers to be included in each API request.
        RATE_LIMIT (int): The number of requests per second allowed by the API: 50 requests per second
        limiter (AsyncLimiter): An instance of AsyncLimiter to enforce rate limits.
    """
    BASE_URL = "https://api.elsevier.com/content/search/sciencedirect"
    SEARCH_ENDPOINT = "?query="
    RESPONSE_FORMAT = "json"
    API_KEY = os.environ.get("ELSEVIER_API_KEY")
    HEADERS = {
        'X-ELS-APIKey': API_KEY,
        'Accept': 'application/json'
    }
    RATE_LIMIT = 50  
    limiter = AsyncLimiter(RATE_LIMIT, 1)

    @staticmethod
    def build_query(paper: Paper):
        """
        Constructs a search query URL for the Elsevier API based on a Paper instance's attributes.

        Parameters:
            paper (Paper): An instance of the Paper model containing the search criteria.

        Returns:
            dict: A dictionary with a key 'useDirectPath' containing the constructed search query.
        """
        query_parts = []
        if paper.title:
            # Properly enclose the title in parentheses and URL-encode.
            title_part = urllib.parse.quote(f"title({paper.title})", safe='')
            query_parts.append(title_part)

        if paper.authors.exists():
            # Extract the last name, URL-encode, enclose in parentheses because of the "AND" before and join all with "OR".
            authors_query = "(" + " OR ".join([urllib.parse.quote(f"authors({author.name.split()[-1]})", safe='') for author in paper.authors.all()]) + ")"
            query_parts.append(authors_query)

        if paper.pub_year:
            date_part = urllib.parse.quote(f"date({paper.pub_year})", safe='')
            query_parts.append(date_part)

        search_query = " AND ".join(query_parts)

        # TODO: Use POST request instead of GET request.
        # Currently the whole query is to be directly appended to the URL according to documentation. For reference:
        # https://dev.elsevier.com/tecdoc_sdsearch_migration.html deals with this exact topic.
        # -> Use POST with params instead of GET in the future to optimize this. 
        return {'useDirectPath': search_query}

    @staticmethod
    def process_search_results(json_data, paper: Paper):
        """
        Processes the search results from the Elsevier API to find matches based on a Paper instance.

        Parameters:
            data (dict): The JSON data returned from the Elsevier API search query.
            paper (Paper): The Paper instance used as the search criteria.

        Returns:
            dict or None: A dictionary with the matched paper details or None if no match is found.
        """
        entries = json_data.get('search-results', {}).get('entry', [])
        for result in entries:
            if ElsevierApi.is_match(result, paper):
                return ElsevierApi.format_match_result(result)
        return None

    @staticmethod
    def is_match(result, paper: Paper):
        """
        Checks if a single result from the search results matches the given Paper instance based on title.
        Other checks based on the return fields with the source paper fields can be added.

        Parameters:
            result (dict): A single search result.
            paper (Paper): The Paper instance to match against.

        Returns:
            bool: True if the result matches the Paper instance, False otherwise.
        """
        title_match = paper.title.lower().strip() == result.get('dc:title', '').lower().strip()
        return title_match

    @staticmethod
    def format_match_result(result):
        """
        Formats a matching search result into a structured dictionary for easier access and use.

        Parameters:
            result (dict): A dictionary representing a matching search result.

        Returns:
            dict: A dictionary containing the formatted details of the matching result, including
                  source, title, access status, links, and DOI information.
        """
        title = result.get('dc:title')
        oa_status = result.get('openaccess', False)
        doi = result.get('prism:doi')
        pii = result.get('pii')
        doi_link = f"http://dx.doi.org/{doi}" if doi else None
        full_text_link = result.get('link', [{}])[0].get('@href')

        returning = {
            'source': 'Elsevier',
            'title': title,
            'open_access': oa_status,
            'full_text_link': full_text_link,
            'doi_link': doi_link,
        }
        if oa_status and doi:
            returning['full_text_link'] = f"https://www.sciencedirect.com/science/article/pii/{pii}/pdf"
            returning['download_link'] = f"https://api.elsevier.com/content/article/doi/{doi}?APIKey={ElsevierApi.API_KEY}&view=FULL&httpAccept=application/pdf"
            returning['file_format'] = FileFormat.PDF
        if doi:
            returning['DOI'] = doi
            returning['doi_link'] = doi_link

        return returning
