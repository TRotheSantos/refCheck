import asyncio
import aiohttp

from paper_manager.models import Paper
from paper_retriever.services.UnpaywallApi import UnpaywallApi
from paper_retriever.services.BasicApi import BasicApi


class QueryEngine:
    """
    A class for querying multiple APIs asynchronously to retrieve source papers.

    The Query Engine is designed to work with any registered API that inherits from the
    BasicAPI class. It simultaneously sends requests to all registered APIs and processes
    results in order to extract relevant attributes such as metadata about the source paper
    as well as required download or fulltext links. The links are either used to retrieve the
    paper automatically later or to provide the user of RefCheck a link to download or read
    the paper themselves.

    Attributes:
        apis (list): A list of API client instances to query.
    """

    # These are all original publishers with implemented API class. The name in the array is based on the 
    # API name set inside the 'source' attribute of the classes returned dictionary from its format_match_result method.
    publisher_apis = ['arXiv', 'Elsevier', 'Springer Nature']

    def __init__(self, apis: list[BasicApi]):
        """
        Initializes the QueryEngine with a list of APIs to query.

        Parameters:
            apis (list): A list of initialized API clients that conform to a common interface for querying.
        """
        self.apis = apis

    async def query_all_apis(self, paper: Paper):
        """
        Asynchronously queries all configured APIs for a given paper and returns the first open access result
        from one of the original_apis. This means the paper was found at a publisher or original content host.
        Otherwise, all existing results are passed to the proccessing logic in order to extract attributes
        and links from them.

        Parameters:
            paper (Paper): The paper object to query for.

        Returns:
            A dictionary containing the query results. There are two scenarios for return values:
            - The method immediately returns if a downloadable, open access results from an original
              publisher is found. In this case, all other ongoing query tasks are canceled.
            - If no such result is found, the method passes all gathered results to the processing logic.

        This method queries all APIs in parallel, cancels all outstanding requests once an open access result is found,
        and processes the results to return the most relevant paper information. ------ REMOVE
        """
        async with aiohttp.ClientSession() as session:
            tasks = [asyncio.create_task(api.query_api(paper, session)) for api in self.apis]
            for task in asyncio.as_completed(tasks):
                try:
                    result = await task
                    if result and result.get('open_access') and result.get('download_link') and result.get('source') in QueryEngine.publisher_apis:
                        # Cancel all other tasks as we found an open access (OA) result with a download link from an
                        # original publisher which is the best possible result, so all other requests can be dropped.
                        for t in tasks:
                            if t != task:
                                t.cancel()
                        return await self.process_results(paper, [result], session)
                except asyncio.CancelledError:  # shouldn't occurr if directly return result after cancellation of other tasks
                    # Raised when the event loop attempts to resume a cancelled task inside a HTTP request after being
                    # an optimal result was found. Ignore and continue as the task is not necessary anymore.
                    continue

        # If no OA result is found, process all results.
        return await self.process_results(paper, [t.result() for t in tasks if t.done() and not t.cancelled()], session)

    async def process_results(self, paper: Paper, results, session: aiohttp.ClientSession):
        """
        Processes all results gathered from the APIs and compiles a comprehensive result for the paper
        which consists of aggregated attributes and links based on the selection logic.
        This method filters, sorts, and consolidates results to provide a comprehensive view of the paper information,
        prioritizing open access sources and completeness of information.

        Parameters:
            paper (Paper): The paper object that was queried.
            results (list): A list of results from the APIs. These dictionaries can differ in their entries
                            as different APIs return different optional attributes. They only have to share
                            the required attributes specified in the BasicAPI class.
            session (aiohttp.ClientSession): The aiohttp client session used to send requests to the Unpaywall API.

        Returns:
            dict: A dictionary containing the compiled information from the API results.
        """
        valid_results = [result for result in results if result]

        final_result = {
            'title': None,
            'origin': None,
            'full_text_link': None,
            'doi_link': None
        }

        sorted_results = sorted(valid_results, key=lambda x: (bool(x['open_access']), x['source'] in QueryEngine.publisher_apis))

        for result in sorted_results:
            if (not final_result['origin']) and result['open_access'] and result.get('download_link'):
                final_result['source'] = result['source']
                final_result['open_access'] = result['open_access']
                final_result['origin'] = result['download_link'] # Only download open access publications.
                final_result['file_format'] = result['file_format']
                final_result['full_text_link'] = result['full_text_link'] # Also set full_text_link to keep consistency.
                break
        for result in sorted_results:
            result.pop('download_link', None)  # Remove download link from results to prevent adding not open access links
            result.pop('file_format', None)
            result.pop('source')

            # Also remove the open access status from a result as the aggregation could be a mix of open and closed
            # access and should be kept coherent to the actual origin attribute.
            result.pop('open_access')
        for result in sorted_results:
            for key, value in result.items():
                if not final_result.get(key):
                    final_result[key] = value

        # Final lookup via Unpaywall in case a DOI but no OA link was found.
        if not final_result['full_text_link'] and final_result.get('doi_link'):
            # Update the paper's origin property based on the DOI link.
            # Note: Changes the origin on the object only. Not a final update in the database!
            paper.origin = final_result.pop('doi_link', None)
            unpaywall_result = await UnpaywallApi.query_api(paper, session)
            if unpaywall_result and unpaywall_result.get('url_for_pdf'):
                final_result['full_text_link'] = unpaywall_result['url_for_pdf']
                # TODO update other details based on Unpaywall result too.
                # Additional fields could be extracted from the Unpaywall response.

        if not final_result['full_text_link']:
            final_result['full_text_link'] = final_result.pop('doi_link', None)
        if final_result.get('year'):
            final_result['pub_year'] = int(final_result.pop('year'))
        await paper.update_by_json(final_result, overwrite=True)
