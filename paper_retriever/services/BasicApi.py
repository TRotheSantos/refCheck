from abc import ABC, abstractmethod

from aiohttp import ClientSession
from aiolimiter import AsyncLimiter

from paper_manager.models import Paper


class BasicApi(ABC):
    """
    Abstract base class for API interfaces.

    This class provides a template for API classes that retrieve paper information from various sources. 
    It enforces a consistent structure across different APIs by defining abstract methods that each subclass 
    must implement. The class handles rate limiting and the basic flow of making an API request.

    Attributes:
        BASE_URL (str): Base URL for the API. Must always be defined in subclasses.
        SEARCH_ENDPOINT (str): The endpoint added to the BASE_URL to allow for querying. Not all APIs use it.
        RESPONSE_FORMAT (str): Expected response format from the API (Currently supported: "json", "xml", "atom").
        API_KEY (str): Optional API key for authentication. Consider secure storage for sensitive keys.
        PARAMS (dict): Fixed parameters amongst all API request, like the number of returned rows. Defined in subclasses if needed.
        HEADERS (dict): Headers for the API request, often used for authentication. Defined in subclasses if needed.
        RATE_LIMIT (int): Maximum number of requests per time unit to comply with API rate limits (if limit exists).
        limiter (AsyncLimiter): A class-level rate limiter object to ensure compliance with RATE_LIMIT.

    Methods:
        query_api(reference, session): Asynchronously sends a query to the API and processes the response. The query searches
        by using an instance of Paper and 'session' is an instance of aiohttp.ClientSession for making HTTP requests.

        build_query(reference): Constructs the query string based on the corresponding API documentation. This method should
        always be overriden in the subclass to comply with the required query format. The query is based on Paper attributes,
        currently title, authors and year are possible to be queried for.

        process_search_results(data, reference): Processes the API response and extracts a standardized dictionary including
        the name of the source API, required doi, display and fulltext links and the open access status. Optional attributes
        can be added to the dictionary based on the format of the API response. Should be overriden in every API class.

        is_match(result, reference): Determines if a given result from the search results matches the paper atttributes.
        Mainly the titles is matched and other checks such as authors and year are possible. Should be overriden in every API
        class.

        format_match_result(result): Formats and returns the information of a match from the search results. This creates the
        returned dictionary with all required and optional attributes. Should be overriden in every API class.
    """
    BASE_URL: str = None
    SEARCH_ENDPOINT: str = None
    RESPONSE_FORMAT: str = None
    API_KEY: str = None
    PARAMS: dict = None
    HEADERS: dict = None
    RATE_LIMIT: int = None
    limiter: AsyncLimiter = None

    @classmethod
    def ensure_required_attributes_are_set(cls):
        """
        Validates that all required class attributes are defined in subclasses.
        Lists all necessarilly required attributes inside the provided array based on their class 
        variable name. The array has to atleast include a base url to send the request to as well as 
        define the API response format. 

        Raises:
            AttributeError: If any required attribute is not properly defined.
        """
        required_attributes = ['BASE_URL', 'RESPONSE_FORMAT']  
        missing_attributes = [attr for attr in required_attributes if getattr(cls, attr) is None]

        if missing_attributes:
            raise AttributeError(f"{cls.__name__} is missing definitions for: {', '.join(missing_attributes)}")

    @classmethod
    async def query_api(cls, paper: Paper, session: ClientSession):
        """
        Asynchronously queries the API for paper information.

        This method sends a GET request to the API using the query built by the build_query method. 
        A query can be added to the params of the request which is the best practice when it comes 
        to HTTP requests. If this is not possible due to the API requiring a URL appended query, 
        use a dictionary the same way if the query would be added to params but in this case use 
        the "useDirectPath" field mentioned inside the method to indicate direct appendation.
        The method then processes the API response using the process_search_results method.
        
        Args:
            paper (Paper): An instance of the Paper class containing information about the paper to be queried.
            session (ClientSession): An aiohttp client session used to send the GET request, allowing for asynchronous 
            HTTP requests.

        Returns:
            The processed search result if a match is found; otherwise, None.
        """
         # Validate required attributes. These include a base url and a specified return format.
        cls.ensure_required_attributes_are_set()

        await cls.limiter.acquire()

        # Get headers from subclass. If 'None' then safely ignored in GET request.
        headers = cls.HEADERS

        # Merge constant class params with the dynamically constructed query.
        params = dict(cls.PARAMS or {}, **cls.build_query(paper))

        # Special cases where the query needs to be appended directly instead of using params.
        # Set the Indicator tag "useDirectPath" inside the returned dictionary. Safe empty string if not set.
        useDirectPath = params.pop("useDirectPath", "")

        # Constructs the complete search url with optional appended query.
        # Search Endpoint set to None is dangerous cause this fails if not implemented 
        # -> this is why the required attributes are validated beforehand.
        url = f"{cls.BASE_URL}{cls.SEARCH_ENDPOINT}{useDirectPath}"

        try:
            async with session.get(url, headers = headers, params = params) as response:
                if response.status == 200:
                    if cls.RESPONSE_FORMAT == 'json':
                        data = await response.json()
                    elif cls.RESPONSE_FORMAT in ['xml', 'atom']:
                        data = await response.text()
                    else:
                        # TODO: Add handling of other HTTP response types.
                        # Due to the async nature and the amount of requests there is no handling for different responses
                        # as this largely depends on the approach of the program in the future. Currently, they are simply  
                        # considered a failed request and ignored. If required to handle different response types, add 
                        # the handling here.
                        return None

                    return cls.process_search_results(data, paper)
                return None
        except Exception as e:
            # TODO: Consider Exceptions in future.
            # Currently failed request are ignored due to the amount of parallel requests and the fact that failed HTTP
            # request don't force the program to fail as they are simply classified as "not found". If necessary, 
            # exception handling could be added here.
            return None

    @staticmethod
    @abstractmethod
    def build_query(paper: Paper):
        """
        Abstract method to construct the query string for the API request.

        This method should construct a query string based on the corresponding APIs documentation which defines
        all available query fields as well as best practices to query efficiently.
        The query string is either directly appended to the combination of the URL and SEARCH_ENDPOINT in the
        query method or added to the PARAMS. Using params aligns with the requests library and makes the call
        cleaner & safer because manual encoding is more error-prone. It also allows for easier and more readable
        query manipulation.

        Args:
            paper(Paper): The Paper object containing information to construct the query.

        Returns:
            A dictionary which contains the constructed query string.
        """
        pass

    @staticmethod
    @abstractmethod
    def process_search_results(data, paper: Paper):
        """
        Abstract method to process the API response.

        This method should iterate through the search results, check if each result matches the query using
        the is_match method, and return the formatted article information using format_article_info method.

        Args:
            data: The structured data received from the API response. Currently either JSON, XML or Atom.
            paper (Paper): The Paper object used for the query.

        Returns:
            The formatted information of the matching article if found; otherwise, None.
        """
        pass

    @staticmethod
    @abstractmethod
    def is_match(result, paper: Paper):
        """
        Abstract method to determine if a search result matches the paper query.

        This method can perform a post processing matching logic as an api query with specified fields doesn't
        guarantee one of the returned results is actually the desired ressource.

        Args:
            result: A single search result.
            paper (Paper): The Paper object used for the query.

        Returns:
            True if the result matches the paper query; False otherwise.
        """
        pass

    @staticmethod
    @abstractmethod
    def format_match_result(result):
        """
        Abstract method to format the information of a single article.

        Args:
            result: A single search result.

        Returns:
            A dictionary containing the formatted article information with the following fields:
                - 'source': The name of the API or data source.
                - 'title': The title of the article.
                - 'open_access': Boolean indicating whether the article is open access (OA).
                - 'download_link': URL for downloading the article.
                - 'full_text_link': URL for accessing the full text of the article.
                - 'doi_link': URL of the Digital Object Identifier (DOI) of the article.
            Subclasses may include additional optional fields e.g. journal, publisher,... as needed.
        """
        pass
