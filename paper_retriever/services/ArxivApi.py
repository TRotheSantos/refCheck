import xml.etree.ElementTree as ET

from aiolimiter import AsyncLimiter

from paper_manager.models import Paper, FileFormat
from paper_retriever.services.BasicApi import BasicApi


class ArxivApi(BasicApi):
    """
    ArxivApi provides an interface to query and process responses from the arXiv API.
    It extends BasicApi, utilizing its structure for making HTTP requests and handling responses,
    tailored specifically for the arXiv's API endpoints, response formats, and rate limiting.

    Attributes:
        BASE_URL (str): Base URL for the arXiv API.
        SEARCH_ENDPOINT (str): Endpoint for querying the arXiv API.
        RESPONSE_FORMAT (str): The expected response format from the arXiv API, set to 'atom'.
                               This format indicates that responses will be XML-based and require
                               appropriate parsing.
        RATE_LIMIT (int): The maximum number of requests allowed per time unit, set to enforce
                          compliance with arXiv's rate limiting policy. arXiv specifies a spacing
                          of 3 seconds between requests but no upper cap per day.
        limiter (AsyncLimiter): An instance of AsyncLimiter to enforce rate limits.
        NAMESPACE (dict): Namespace mapping used for parsing the atom XML response, facilitating
                          accurate data extraction.
    """
    BASE_URL = "http://export.arxiv.org/api"
    SEARCH_ENDPOINT = "/query"
    RESPONSE_FORMAT = "atom"

    RATE_LIMIT = 1
    limiter = AsyncLimiter(RATE_LIMIT, 3)

    NAMESPACE = {'arxiv': 'http://www.w3.org/2005/Atom'}

    @staticmethod
    def build_query(paper: Paper):
        """
        Constructs a search query for the arXiv API based on the paper's title and authors.

        Parameters:
            paper (Paper): An instance of the Paper model containing title and authors.

        Returns:
            dict: A dictionary with the search query to be used in the API request.
            This query incorporates the paper's title and authors, an exact year parameter
            doesn't exist. But it can be filtered for results of different years.

        """
        query_parts = []
        if paper.title:
            title_query = f"ti:{paper.title}"
            query_parts.append(title_query)
        if paper.authors.exists():
            authors_query = " OR ".join([f'au:"{author.name.split()[-1]}"' for author in paper.authors.all()])
            query_parts.append(f"({authors_query})")
        # No explicit year param. Could filter for year or better just match date in response during processing.

        search_query = " AND ".join(query_parts)
        return {'search_query': search_query}

    @staticmethod
    def process_search_results(atom_data, paper: Paper):
        """
        Processes the XML response from the arXiv API, extracting relevant paper information
        by calling the format_match_result method for every response entry.

        Parameters:
            xml_data (str): The XML response data from the arXiv API.
            paper (Paper): An instance of the Paper model to match the response against.

        Returns:
            dict or None: A dictionary with matched paper details as formatted by format_match_result,
                          or None if no match is found. The dictionary contains keys for 'source', 'title',
                          'open_access', 'full_text_link', and 'doi_link', among possible others.
        """
        root = ET.fromstring(atom_data)

        for result in root.findall('arxiv:entry', ArxivApi.NAMESPACE):
            if ArxivApi.is_match(result, paper):
                return ArxivApi.format_match_result(result)
        return None

    @staticmethod
    def is_match(result, paper: Paper):
        """
        Checks if a result from the arXiv API response matches the search criteria.

        Parameters:
            entry (xml.etree.ElementTree.Element): An entry element from the XML response.
            paper (Paper): An instance of the Paper model to compare the entry against.

        Returns:
            bool: True if the entry matches the paper's title, False otherwise.
        """
        search_title = paper.title.lower().strip()
        result_title = result.find('arxiv:title', {'arxiv': 'http://www.w3.org/2005/Atom'}).text.lower().strip()

        '''
        Logic if title and year should be matched. Need to check if this is accurate first.

        title_match = search_title == result_title
        year_match = True  # Assume match by default
        if reference.publication_date:
            published_date = item.find('arxiv:published', {'arxiv': 'http://www.w3.org/2005/Atom'}).text
            published_year = datetime.strptime(published_date, "%Y-%m-%dT%H:%M:%SZ").year
            year_match = str(published_year) == reference.publication_date
        return title_match and year_match
        '''
        return search_title == result_title

    @staticmethod
    def format_match_result(result):
        """
        Formats a matching result into a structured dictionary.

        Parameters:
            result (xml.etree.ElementTree.Element): A matching entry from the XML response.

        Returns:
             dict: A dictionary containing the source, title, access link, and other details of the paper,
                   specifically keys for 'source', 'title', 'open_access', 'full_text_link', and 'doi_link'.
                   This dictionary is intended to be used as the return value of process_response when a match
                   is found.
        """
        title = result.find('arxiv:title', ArxivApi.NAMESPACE).text
        pdf_link = result.find("arxiv:link[@title='pdf']", ArxivApi.NAMESPACE).attrib['href'] # correct link

        doi_link_element = result.find("arxiv:link[@title='doi']", ArxivApi.NAMESPACE)
        doi_link = doi_link_element.attrib['href'] if doi_link_element is not None else None

        download_link = pdf_link
        returning = {
            'source': 'arXiv',
            'title': title,

            # TODO: Implement checks for unclear licensing issues.
            # Generally open access but no explict open access field returend. License type also not part of response 
            # field but publishing on arXiv requires granting certain reuse rights by publishing under an open license.
            # -> Licenses should be considered in more detail for the future of the project. 
            'open_access': True, 
            'full_text_link': pdf_link,
            'doi_link': doi_link
        }
        if download_link:
            returning['download_link'] = download_link
            returning['file_format'] = FileFormat.PDF
        return returning
