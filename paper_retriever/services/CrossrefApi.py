from aiolimiter import AsyncLimiter

from paper_retriever.services.BasicApi import BasicApi
from paper_manager.models import Paper, FileFormat


class CrossrefApi(BasicApi):
    """
    CrossrefApi provides an interface to query the CrossRef API for academic papers.
    It extends BasicApi, leveraging its foundational structure for making HTTP requests and handling responses,
    specifically tailored to the CrossRef API's requirements. This includes custom endpoint configurations,
    expected response formats, and rate limiting adaptations.

    Attributes:
        BASE_URL (str): The base URL for the CrossRef API.
        SEARCH_ENDPOINT (str): The endpoint for searching academic works in the CrossRef database.
        RESPONSE_FORMAT (str): The expected response format (JSON).
        PARAMS (dict): Default parameters to include in every search request, aimed at refining and controlling the search output.
        RATE_LIMIT (int): The maximum number of requests per second allowed by the API to prevent overloading the service: 50 requests/second.
        limiter (AsyncLimiter): An instance of AsyncLimiter to enforce rate limits according to the API's guidelines.

    The class provides methods to construct queries based on various criteria (e.g., paper title, author names, publication year),
    process search results to find matches, and format these matches for further use. It takes into account the API specificities,
    such as its bibliographic query capabilities and the handling of rate limits to ensure compliance with the API's usage policies.
    """
    BASE_URL = "https://api.crossref.org"
    SEARCH_ENDPOINT = "/works"
    RESPONSE_FORMAT = "json"
    PARAMS =  {"rows": 2}
    RATE_LIMIT = 50
    limiter = AsyncLimiter(RATE_LIMIT, 1)

    @staticmethod
    def build_query(paper: Paper):
        """
        Processes search results from the CrossRef API to find matches based on a paper object.

        Parameters:
            data (dict): The JSON response data from the CrossRef API.
            paper (Paper): The paper object used to find matches in the search results.

        Returns:
            dict or None: A dictionary with formatted match results if a match is found; otherwise, None.
        """
        if paper.title:
            bibliographic_query = {"query.bibliographic": paper.title}
        if paper.authors.exists():
            authors = ", ".join([author.name.split()[-1] for author in paper.authors.all()])
            bibliographic_query["query.bibliographic"] += f", {authors}"
        if paper.pub_year:
            bibliographic_query["query.bibliographic"] += f" {paper.pub_year}"

        return bibliographic_query

    @staticmethod
    def process_search_results(json_data, paper: Paper):
        """
        Processes the search results returned by the Crossref API.

        Parameters:
            data (dict): The JSON response data from the CrossRef API.
            paper (Paper): The paper object used to find matches in the search results.

        Returns:
            dict or None: A dictionary with formatted match results if a match is found; otherwise, None.

        Note:
            This method iterates over search results and returns the first match based on the paper's title.
        """
        for result in json_data.get('message', {}).get('items', []):
            if CrossrefApi.is_match(result, paper):
                return CrossrefApi.format_match_result(result)
        return None

    @staticmethod
    def is_match(result, paper: Paper):
        """
        Determines if a search result matches the search criteria.

        Parameters:
            result (dict): A single result from the search results.
            paper (Paper): The paper object to match against.

        Returns:
            bool: True if the result title matches the paper's title; otherwise, False.

        Note:
            Currently, this method only checks for an exact match of the paper's title.
            Future implementations could consider additional attributes for matching.
        """
        search_title = paper.title.lower().strip()
        result_title = (result.get('title', [''])[0]).lower().strip()
        title_match = search_title == result_title
        # ToDo: Add year attribute check here.
        # Year attributes exists. A check could theoretically be added but many kinds of different dates are 
        # returned (publication, first upload, etc.). This requires further inspection to avoid matching issues.
        # -> Common issue amongst multiple APIs. Publication d ate issues require careful testing as they have proven
        #    to be one of the biggest inconsistencies e.g. in Springer API as well.

        return title_match

    @staticmethod
    def format_match_result(result):
        """
        Formats a search result into a structured dictionary for further processing.

        Parameters:
            result (dict): A single result from the search results that matches a paper.

        Returns:
            dict: A dictionary containing key details about the match, such as DOI, title, and links.

        Note:
            This method formats the match result, including DOI, title, open access status, and links.
            Open access status is currently hard-coded as False; future versions may dynamically determine this.
        """
        doi = result.get('DOI')
        doi_link = f"http://dx.doi.org/{doi}" if doi else None
        full_text_link = CrossrefApi.get_best_full_text_link(result.get('link', []))
        download_link = full_text_link
        title = result.get('title', [None])[0]
        returning = {
            'source': 'CrossRef',
            'title': title,

            # TODO: Extract copyright status from license field.
            # No Open Access Field but licenses are sometimes returned. They can be missing as Crossref as
            # an indexing service often has no uniform responses but rather creates the return fields based 
            # on how much information it can retrieve about a ressource. RefCheck already provideds some 
            # basic functionality to store copyright levels in the CopyrightLevels.py. 
            # -> Hard but possible future feature if license links are stored with respective rights.
            'open_access': False,  
            'full_text_link': full_text_link,
        }
        if doi:
            returning['DOI'] = doi
            returning['doi_link'] = doi_link
        if download_link:
            returning['download_link'] = download_link
            returning['file_format'] = FileFormat.PDF

        return returning
    
    @staticmethod
    def get_best_full_text_link(links):
        # First, try to find a link with content-type as application/pdf.
        pdf_link = next((link['URL'] for link in links if link.get('content-type') == 'application/pdf'), None)

        # If no link with content-type application/pdf was found, search for a link ending in .pdf (case insensitive).
        # A missing application/pdf tag happens quite often as Crossref aggregates from many different providers and
        # this sometimes causes the internal logic to miss the tag even tough a (unmarked) link was found.
        if not pdf_link:
            # Chooses the first available, untagged pdf link.
            pdf_link = next((link['URL'] for link in links if 'URL' in link and link['URL'].lower().endswith('.pdf')), None)
        return pdf_link