import os

from aiolimiter import AsyncLimiter

from paper_retriever.services.BasicApi import BasicApi
from paper_manager.models import Paper


class UnpaywallApi(BasicApi):
    """
    A class for querying the Unpaywall API to retrieve open access versions of academic papers.
    Currently this class is used for DOI results without a fulltext or download link in the
    Query Engine. It can search for an open access version for a given doi. Querying for titles
    and attributes like the other APIs is possible but the query logic is not very accurate
    and requires lots of filtering. Therefore, the DOI-lookup is preferred.

    This class is designed to interact with the Unpaywall API, providing methods to construct
    queries based on a paper's DOI, process the search results, and format them into a
    standardized structure.

    Attributes:
        BASE_URL (str): Base URL for the Unpaywall API.
        SEARCH_ENDPOINT (str): Endpoint for search queries, left empty as DOIs are appended directly.
        RESPONSE_FORMAT (str): Expected format of the response from the API, defaulted to 'json'.
        EMAIL (str): Email address used for querying the Unpaywall API, necessary for compliance.
                     Should be an actual email but no registration for it is required.
        RATE_LIMIT (int): The rate limit for API requests to avoid exceeding API usage terms: 50 requests/second and
                          maximum of 100k requests per day.
        RATE_LIMITER (AsyncLimiter): An asynchronous rate limiter to manage request rates.
    """
    BASE_URL = "https://api.unpaywall.org/v2"
    SEARCH_ENDPOINT = '' # DOI is directly appended, no specificy endpoint. Keep empty currently to avoid "None" issue in BasicApi.
    RESPONSE_FORMAT = 'json'
    EMAIL = os.environ.get('UNPAYWALL_EMAIL')
    RATE_LIMIT = 50
    limiter = AsyncLimiter(RATE_LIMIT, 1)


    @staticmethod
    def build_query(paper: Paper):
        """
        Constructs a query for the Unpaywall API based on the DOI found in a paper's origin field.
        The DOI will be inside a DOI-link so it will be extracted first.

        Args:
            paper (Paper): The paper object containing the origin field, potentially with a DOI.

        Returns:
            dict: A dictionary with 'useDirectPath' key containing the query path, or None if no DOI.
        """

        origin = paper.origin if paper.origin else ""
        doi = ""

        # Attempt to extract the DOI only if the 'origin' contains "doi.org/".
        if "doi.org/" in origin:
            try:
                doi = origin.split("doi.org/")[-1]
            except Exception:
                # Safely catches formatting errors and resets DOI to an empty string to indicate an extraction failure.
                doi = ""  

        if doi:
            query = f"/{doi}?email={UnpaywallApi.EMAIL}"
            return {'useDirectPath': query}
        else:
            return None # No query is performed if no valid DOI is provided.

    @staticmethod
    def process_search_results(data, paper: Paper):
        """
        Processes the search results from the Unpaywall API and formats them into a standardized structure,
        ensuring the data matches the DOI of the provided paper object.

        Args:
            data (dict): The JSON data returned from the Unpaywall API query.
            paper (Paper): The paper object used for the query.

        Returns:
            dict: A dictionary containing formatted search results if a match is found; otherwise, None.
        """
        if UnpaywallApi.is_match(data, paper):
            formatted_result = UnpaywallApi.format_match_result(data)
            return formatted_result
        else:
            return None

    @staticmethod
    def is_match(data, paper: Paper):
        """
        Determines if the returned data from Unpaywall matches the DOI of the paper.

        Args:
            data (dict): Data returned from the Unpaywall API.
            paper (Paper): The paper object used for the query, containing the DOI information.

        Returns:
            bool: True if there's a match between the paper's DOI and the DOI in the data; False otherwise.
        """

        # Ommits safety check as only well-formatted DOIs are queried for.
        origin_doi = paper.origin.split("doi.org/")[-1]

        return origin_doi and data.get('doi') == origin_doi

    @staticmethod
    def format_match_result(data):
        """
        Formats the raw data returned from Unpaywall into a standardized dictionary format.

        Args:
            data (dict): The raw data returned from the Unpaywall API.

        Returns:
            dict: A dictionary containing key information extracted from the raw data.
        """
        result = {
            'title': data.get('title'),
            'doi': data.get('doi'),
            'is_open_access': data.get('is_oa'),
            'oa_status': data.get('oa_status'),
            'publisher': data.get('publisher'),
            'genre': data.get('genre'),
            'has_repository_copy': data.get('has_repository_copy', False),
            'license': None,
            'version': None,
            'host_type': None,
            'url_for_pdf': None
        }

        best_oa_location = data.get('best_oa_location')
        if best_oa_location:
            result['license'] = best_oa_location.get('license')
            result['version'] = best_oa_location.get('version')
            result['host_type'] = best_oa_location.get('host_type')
            result['url_for_pdf'] = best_oa_location.get('url_for_pdf')

        # If no PDF URL in best OA location, search for other OA locations.
        if not result['url_for_pdf']:
            for location in data.get('oa_locations', []):
                if location.get('url_for_pdf'):
                    result['url_for_pdf'] = location['url_for_pdf']
                    break

        return result
