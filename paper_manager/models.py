import json

from asgiref.sync import sync_to_async
from django.core.files.storage import default_storage
from django.db import models
from django.utils.translation import gettext_lazy as label
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.conf.locale import LANG_INFO

from llm.models import getChromaCollection

# Create your models here.
"""
Takeaways from Django module docs:
- some field options are configurable in the admin page
- Fields option null=True allows NULL values in DB, blank=True allows empty/Null model/form values
- string Fields like CharField, TextField, SlugField, URLField, EmailField, CommaSeparatedIntegerField, IPAddressField, FileField, FilePathField, ImageField, and DateField, DateTimeField, TimeField, DurationField, UUIDField, all have a max_length option
- ForeignKey: is a one-to-many relationship and can be accessed from the "one" side (pointed to) too via relation_name if set or "multi" side *model_name*_set
"""

Languages = [
    (code, info['name']) for code, info in LANG_INFO.items() if 'name' in info
]


class Author(models.Model):
    # string representation of full name
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


# possibility to specify storage location if we want
#     TODO modify storing path https://docs.djangoproject.com/en/4.2/ref/models/fields/#django.db.models.FileField.upload_to
def paper_directory_path(instance, filename):
    pass  # return PurePath('papers', 'uploaded' if manually_uploaded else 'extracted', filename)
#
#
# class PaperManager(models.Manager):
#     """should filter papers by user if not superuser to restrict access on a high level"""
#     def get_queryset(self, request=None, *args, **kwargs):
#         if not request:
#             return super().get_queryset()  # TODO change in production
#         if request.user.is_superuser:
#             return super().get_queryset()
#         if request.user.is_authenticated:
#             return super().get_queryset().filter(user=self.request.user)


class FileFormat(models.TextChoices):
    """
    This class is a Django model that represents different file formats. It is used to specify the format of a file
    associated with a Paper instance. The class inherits from Django's TextChoices, which is a class to create enumerable choices.

    The class attributes represent different file formats:
    - TXT: Text file format.
    - HTML: HTML file format.
    - MD: Markdown file format.
    - PDF: PDF file format.
    - EPUB: EPUB file format.
    - DOCX: DOCX file format. This is used for both .doc and .docx files.
    - ODT: ODT file format.
    - PPTX: PPTX file format. This is used for both .ppt and .pptx files.
    - XML: XML file format.
    - LATEX: LaTeX file format.
    - UNDEFINED: This is used when the file format is not defined or unknown.

    Note:
    The URL file format is commented out as it is used for webpages that are not downloaded.
    """
    TXT = 'txt', label('TXT')
    HTML = 'html', label('HTML')
    # URL = 'url', label('URL')  # for not downloaded webpages
    MD = 'md', label('MD')
    PDF = 'pdf', label('PDF')
    EPUB = 'epub', label('EPUB')
    DOCX = 'docx', label('DOCX')  # for both .doc & .docx
    ODT = 'odt', label('ODT')
    PPTX = 'pptx', label('PPTX')  # for both .ppt & .pptx
    XML = 'xml', label('XML')
    LATEX = 'tex', label('LaTeX')
    UNDEFINED = 'un', label('undefined')


class CitationStyle(models.TextChoices):
    """
    This class is a Django model that represents different citation styles. It is used to specify the citation style
    of a Paper instance. The class inherits from Django's TextChoices, which is a class to create enumerable choices.

    The class attributes represent different citation styles:
    - APA: APA citation style.
    - IEEE: IEEE citation style.
    - UNKNOWN: This is used when the citation style is not defined or unknown.

    Note:
    The MLA, CHICAGO, HARVARD, and VANCOUVER citation styles are commented out as they don't have their own logic implementation along the process yet.
    """
    APA = 'APA', 'APA'
    # MLA = 'MLA', 'MLA'
    # CHICAGO = 'CHI', 'Chicago'
    # HARVARD = 'HAR', 'Harvard'
    IEEE = 'IEEE', 'IEEE'
    # VANCOUVER = 'VAN', 'Vancouver'
    UNKNOWN = 'UN', 'unknown'


class Paper(models.Model):
    """
    The Paper class is a Django model that represents a paper in the system. It contains various fields that store information about the paper, such as the title, authors, language, citation style, origin, type, publication year, file format, file, chroma collection, pages, start bibliography, and end bibliography.

    The class also includes several methods that provide functionality for updating the paper's attributes, duplicating the paper, getting the count of checks with a non-null score, calculating the percentage of score count, getting relevant reference attributes, matching reference bibliography, and creating a Paper instance from a JSON object.

    Attributes:
    - user (User): The user who owns the paper.
    - last_modified (DateTimeField): The date and time when the paper was last modified.
    - title (CharField): The title of the paper.
    - authors (ManyToManyField): The authors of the paper.
    - language (CharField): The language of the paper.
    - citation_style (CharField): The citation style of the paper.
    - origin (URLField): The origin of the paper.
    - type (CharField): The type of the paper.
    - pub_year (IntegerField): The publication year of the paper.
    - file_format (SlugField): The file format of the paper.
    - file (FileField): The file of the paper.
    - chroma_collection (SlugField): The chroma collection of the paper.
    - pages (IntegerField): The number of pages in the paper.
    - start_bibliography (TextField): The start bibliography of the paper.
    - end_bibliography (TextField): The end bibliography of the paper.
    """
    # objects = PaperManager()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='papers')
    last_modified = models.DateTimeField(auto_now=True)  # TODO update on any changes maybe sth django builtin?
    title = models.CharField(max_length=255, unique=True)
    authors = models.ManyToManyField(Author, related_name='papers')
    language = models.CharField(max_length=7, choices=Languages, default='en')
    citation_style = models.CharField(max_length=255, choices=CitationStyle.choices, default=CitationStyle.IEEE)
    origin = models.URLField(max_length=255, null=True, blank=True)
    # TODO adopt to possible paper type choices (paper, book, thesis, website,...), also in extraction prompts
    type = models.CharField(max_length=63, null=True, blank=True)
    pub_year = models.IntegerField(null=True, blank=True)
    file_format = models.SlugField(max_length=10, choices=FileFormat.choices, default=FileFormat.UNDEFINED)
    # open_access = models.BooleanField(default=False) ?
    # how to store files https://docs.djangoproject.com/en/4.2/ref/models/fields/#django.db.models.FileField.storage
    # TODO  secure for CGI/PHP scripts...
    file = models.FileField(upload_to='papers/', null=True, blank=True)
    chroma_collection = models.SlugField(max_length=63, null=True, blank=True, unique=True)
    pages = models.IntegerField(null=True, blank=True)
    start_bibliography = models.TextField(max_length=511, null=True, blank=True)
    end_bibliography = models.TextField(max_length=511, null=True, blank=True)

    async def update_by_json(self, json: dict, overwrite=False) -> 'Paper':
        """
        Updates paper attributes and creates new PaperAttribute objects for additional attributes.
        Updates all paper attributes except user (owner), file and chroma_collection.

        Parameters:
        - json (dict): The JSON object containing the new attributes for the paper.
        - overwrite (bool, optional): If True, overwrite existing attributes. If False, only update attributes that are currently None. Defaults to False.

        Returns:
        - Paper: The updated Paper instance.
        """
        json = {k: v for k, v in json.items() if v}
        print(json)
        # Title currently not updated, API returned title may slightly differ.
        # If also updating title, should implement logic to prevent updating with data from a wrong/different paper
        title = json.pop('title', None)
        if title and title != self.title:
            print(f"WARNING: Title \"{title}\" does not match paper title \"{self.title}\". Update with correct data?")
        if overwrite:
            # self.title = json.pop('title', self.title)
            self.language = json.pop('language', self.language)
            self.citation_style = json.pop('citation_style', self.citation_style)
            if "doi.org" in json.get('origin', ''):
                attribute, created =await sync_to_async(PaperAttribute.objects.get_or_create)(paper=self, label='doi-link', defaults={'value': json['origin']})
                attribute.value = json['origin']
                await attribute.asave()
            self.origin = json.pop('origin', self.origin)
            self.type = json.pop('type', self.type)
            self.pub_year = json.pop('pub_year', self.pub_year)
            self.file_format = json.pop('file_format', self.file_format)
            self.start_bibliography = json.pop('start_bibliography', self.start_bibliography)
            self.end_bibliography = json.pop('end_bibliography', self.end_bibliography)
        else:
            # self.title = self.title or json.pop('title', self.title)
            self.language = self.language or json.pop('language', 'en')
            self.citation_style = self.citation_style or json.pop('citation_style', 'IEEE')
            self.origin = self.origin or json.pop('origin', self.origin)
            self.type = self.type or json.pop('type', None)
            self.pub_year = self.pub_year or json.pop('pub_year', None)
            self.file_format = self.file_format or json.pop('file_format', None)
            self.start_bibliography = self.start_bibliography or json.pop('start_bibliography', None)
            self.end_bibliography = self.end_bibliography or json.pop('end_bibliography', None)
            json = {k: v for k, v in json.items() if k not in ['title', 'language', 'citation_style', 'origin', 'type', 'pub_year', 'file_format', 'start_bibliography', 'end_bibliography']}
        await self.asave()
        if json.get('authors'):
            author_create_tupel = [await sync_to_async(Author.objects.get_or_create)(name=author) for author in json.pop('authors', [])]
            # either set or fill up, make dependent on overwrite?
            # await self.authors.aset([author[0].id for author in author_create_tupel])
            await sync_to_async(self.authors.add)(*[author[0] for author in author_create_tupel])
        for key, value in json.items():
            attribute, created = await sync_to_async(PaperAttribute.objects.get_or_create)(paper=self, label=key, defaults={'label': key, 'value': value})
            if not created and overwrite:
                attribute.value = value
                await attribute.asave()
        return self

    async def copyright_safe_duplicate(self, user: User):
        """
        Creates a new paper with the same attributes except copyright relevant ones & new primary key and updates user.

        Parameters:
        - user (User): The user who will own the duplicated paper.

        Returns:
        - Paper: The duplicated Paper instance.
        """
        self.pk = None
        self.user = user
        self.file = None
        await self.asave()
        return self


    def get_checks_with_score_count(self):
        """
        Get the count of checks with a non-null score and not marked as false positive.

        Returns:
        - int: The count of checks with a non-null score and not marked as false positive.
        """
        return self.checks.filter(score__isnull=False, false_positive=False).count()

    def get_checks_with_user_score_count(self):
        """
        Get the count of checks with a non-null user score and not marked as false positives.

        Returns:
        - int: The count of checks with a non-null user score and not marked as false positives.
        """
        return self.checks.filter(user_score__isnull=False, false_positive=False).count()


    def get_checks_with_score_count_percentage(self):
        """
        Calculate the percentage of score count compared to the total checks count.
        It subtracts the user score count percentage to simulate overlapping progress bars in HTML.

        Returns:
        - float: The percentage of score count compared to the total checks count.
        """
        return self.get_checks_with_score_count() / self.checks.count() * 100 - self.get_checks_with_user_score_count_percentage()


    def get_checks_with_user_score_count_percentage(self):
        """
        Calculate the percentage of user score count compared to the total checks count.

        Returns:
        - float: The percentage of user score count compared to the total checks count.
        """
        return self.get_checks_with_user_score_count() / self.checks.count() * 100

    def relevant_reference_attributes(self):
        """
        Get the relevant reference attributes of the paper.

        Returns:
        - dict: A dictionary containing the relevant reference attributes of the paper.
        """
        attributes = {'links':{}, 'other':{}}
        attribute_list = {att.label: att.value for att in self.attributes.filter(label__in=['doi-link', 'isbn', 'url', 'publisher', 'full_text_link', 'Semantic Scholar page', 'DOI'])}
        if attribute_list.get('full_text_link'):
            attributes['links']['Link'] = attribute_list.pop('full_text_link')
        if attribute_list.get('doi-link'):
            attributes['links']['DOI link'] = attribute_list.pop('doi-link')
            attribute_list.pop('DOI', None)
        if attribute_list.get('Semantic Scholar page'):
            attributes['links']['Semantic Scholar page'] = attribute_list.pop('Semantic Scholar page')
        attributes['other'] = attribute_list
        print(json.dumps(attributes, indent=4))
        return attributes

    @property
    def file_format_display(self):
        """
        Get the display name of the file format of the paper.

        Returns:
        - str: The display name of the file format of the paper.
        """
        return dict(FileFormat.choices).get(self.file_format, '')

    def match_reference_bibliography(self):
        """
        Match the reference bibliography of the paper.

        Note:
        This method is currently not implemented.
        """
        pass

    @classmethod
    async def from_json(cls, user: User, json: dict):
        """
        Create a new Paper instance from a JSON object.

        Parameters:
        - user (User): The user who will own the new paper.
        - json (dict): The JSON object containing the attributes for the new paper.

        Returns:
        - Paper: The new Paper instance.
        """
        title = json.pop('title')
        pub_year = json.pop('pub_year', None)
        origin = json.pop('origin', None)
        language = json.pop('language', 'en')
        type = json.pop('type', None)
        paper = await Paper.objects.acreate(user=user, title=title, language=language, origin=origin, type=type, pub_year=pub_year)
        author_objects = [await sync_to_async(Author.objects.get_or_create)(name=author) for author in json.pop('authors', [])]
        await sync_to_async(paper.authors.add)(*[author[0] for author in author_objects])
        attributes = [PaperAttribute(paper=paper, label=key, value=value) for key, value in json.items() if value]
        await sync_to_async(PaperAttribute.objects.bulk_create)(attributes)
        return paper


    def __str__(self):
        return self.title

    def __repr__(self):
        return f"Paper(title={self.title}, authors={self.authors}, origin={self.origin}, file_format={self.file_format}, file={self.file}, chroma_collection={self.chroma_collection})"

    def get_full_language_name(self):
        """
        Get the full name of the language of the paper based on the language code.

        Returns:
        - str: The full name of the language of the paper.
        """
        language_dict = dict(Languages)
        return language_dict.get(self.language, 'Unknown')

@receiver(post_delete, sender=Paper)
def delete_chroma_collection(sender, instance, **kwargs):
    """
    This function is a Django signal receiver that gets triggered after a Paper instance is deleted.
    It checks if the deleted Paper instance has a Chroma collection associated with it.
    If it does, it deletes the Chroma collection.

    Parameters:
    - sender (Model): The model class. Here, it is the Paper model.
    - instance (Paper): The actual instance of the sender that is being deleted.
    - **kwargs: Arbitrary keyword arguments.

    Note:
    This function is decorated with the @receiver decorator, with the signal to listen to (post_delete) and the sender (Paper) specified.
    """
    if instance.chroma_collection:
        getChromaCollection(instance.chroma_collection).delete_collection()


@receiver(post_delete, sender=Paper)
def delete_file(sender, instance, **kwargs):
    """
    This function is a Django signal receiver that gets triggered after a Paper instance is deleted.
    It checks if the deleted Paper instance has a file associated with it.
    If it does, it deletes the file from the default storage.

    Parameters:
    - sender (Model): The model class. Here, it is the Paper model.
    - instance (Paper): The actual instance of the sender that is being deleted.
    - **kwargs: Arbitrary keyword arguments.

    Note:
    This function is decorated with the @receiver decorator, with the signal to listen to (post_delete) and the sender (Paper) specified.
    """
    if instance.file:
        default_storage.delete(instance.file.name)


class PaperAttribute(models.Model):
    """
    The PaperAttribute class is a Django model that represents additional attributes of a paper.
    It contains fields that store the paper it is associated with, the label of the attribute, and the value of the attribute.

    Attributes:
    - paper (Paper): The paper that the attribute is associated with.
    - label (CharField): The label of the attribute.
    - value (CharField): The value of the attribute.
    """
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='attributes')
    label = models.CharField(max_length=255)
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.label}: {self.value}"

    def __repr__(self):
        return f"PaperAttribute(paper={self.paper}, label={self.label}, value={self.value})"


# possible to model as many-to-many relation with properties (Django provides this with through option)
class Source(models.Model):
    """
    The Source class is a Django model that represents a source referenced in a paper. It contains fields that store the paper it is referenced in, the chunk ID of the reference, the bibliography identifier, the bibliography entry, and the paper that the source refers to.

    Attributes:
    - referenced_in (Paper): The paper that the source is referenced in.
    - chunk_id (int): The chunk ID of the reference in the paper.
    - _bibliography_identifier (str): The bibliography identifier of the source. This is a private attribute.
    - bibliography_entry (str): The bibliography entry of the source.
    - paper (Paper): The paper that the source refers to.
    """
    referenced_in = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='sources')
    chunk_id = models.IntegerField()
    _bibliography_identifier = models.CharField(max_length=255, null=True, blank=True)
    bibliography_entry = models.TextField(max_length=511)
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='source_references')

    @property
    def bibliography_identifier(self):
        """
        Get the bibliography identifier of the source. If the identifier is not set, it computes the identifier from the bibliography entry and the citation style of the paper it is referenced in.

        Returns:
        - str: The bibliography identifier of the source.
        """
        if self._bibliography_identifier:
            return self._bibliography_identifier
        else:
            # Todo: compute identifier from bibliography_entry and citation_style of referenced_in paper
            match self.referenced_in.citation_style:
                case 'IEEE':
                    entry = self.bibliography_entry

                    # get the String until the first "]" including it - that is when the IEEE identifier ends
                    identifier = str(entry.partition("]")[0]) + str(entry.partition("]")[1])

                    # remove all possible whitespaces
                    identifier = ''.join(identifier.split())

                    # put the identifier into the variable
                    self._bibliography_identifier = identifier

                    return identifier
                case 'APA':
                    entry = self.bibliography_entry

                    #get the String until the first ")" including it - that is when the parentheses of the year end
                    identifier = str(entry.partition(")")[0]) + str(entry.partition(")")[1])

                    # put the identifier into the variable
                    self._bibliography_identifier = identifier

                    return identifier
                case _:
                    return None

    @bibliography_identifier.setter
    def bibliography_identifier(self, value: str):
        """
        Set the bibliography identifier of the source.

        Parameters:
        - value (str): The new bibliography identifier of the source.
        """
        self._bibliography_identifier = value

    @property
    def chunk(self):
        """
        Get the chunk of the reference in the paper. It retrieves the chunk from the Chroma collection of the paper it is referenced in.

        Returns:
        - tuple: A tuple containing the metadata and the content of the chunk.
        """
        collection = getChromaCollection(self.referenced_in.chroma_collection)
        chroma_return = collection.get(ids=[str(self.chunk_id)])
        metadata, page_content = chroma_return['metadatas'][0], chroma_return['documents'][0]
        return metadata, page_content

    @classmethod
    async def from_json(cls, checked_paper, json: dict, chunk_id: int = None):
        '''
        Not tested yet
        json.pop() throws KeyError if no default value is set, for required fields

        :param checked_paper: The paper the source is referenced in.
        :param json: The extracted data from the checked_paper
        :param chunk_id: The chunk_id of the checked paper the source is in
        :return tuple: A tuple containing the new Source instance and the Paper instance that the source refers to.
        '''
        # load user from checked_paper
        checked_paper = await Paper.objects.select_for_update().prefetch_related('user').aget(id=checked_paper.id)
        print("Create source from json:")
        print(json)
        if not chunk_id:
            chunk_id = int(json.pop('chunk_id'))  # chunk_id required for sources
        identifier = json.pop('identifier', None)
        entry = json.pop('reference')
        json['pub_year'] = json.pop('year', None)
        json['origin'] = json.pop('url', None)
        if not json.get('title'):
            return None, None
        if await Paper.objects.filter(title=json['title']).aexists():
            paper = await Paper.objects.select_for_update().prefetch_related('user', 'authors').aget(title=json.pop('title'))
            if paper.user != checked_paper.user:
                paper = await paper.copyright_safe_duplicate(checked_paper.user)
            await paper.update_by_json(json)
        else:
            paper = await Paper.from_json(checked_paper.user, json)
        source, created = await sync_to_async(cls.objects.select_for_update().get_or_create)(referenced_in=checked_paper,
                                                                                             paper=paper,
                                                                                             defaults={'chunk_id': chunk_id,
                                                                                                       '_bibliography_identifier': identifier,
                                                                                                       'bibliography_entry': entry})
        # update if old was incomplete (shorter)
        if len(source.bibliography_entry) < len(entry):
            source.chunk_id = chunk_id
            source._bibliography_identifier = identifier
            source.bibliography_entry = entry
            await source.asave()
        return source, paper

    def __str__(self):
        return self.bibliography_entry

    def __repr__(self):
        return f"Source(referenced_in={self.referenced_in}, chunk_id={self.chunk_id}, bibliography_identifier={self._bibliography_identifier}, bibliography_entry={self.bibliography_entry}, paper={self.paper})"


class CitationType(models.TextChoices):  # TODO might be extended with description (https://medium.com/@bachelorschreibenlassen/richtig-zitieren-mit-verschiedenen-zitatarten-777c01c114d5) through dataclass (https://docs.python.org/3/howto/enum.html#dataclass-support, https://docs.djangoproject.com/en/4.2/ref/models/fields/#enumeration-types Moonlandings)
    """
    The CitationType class is a Django model that represents different types of citations. It is used to specify the type of a citation in a Check instance. The class inherits from Django's TextChoices, which is a class to create enumerable choices.

    The class attributes represent different citation types:
    - DIRECT: Direct citation.
    - INDIRECT: Indirect citation.
    - REFERENCED: Referenced citation. This may need to be removed in the future.
    - UNKNOWN: This is used when the citation type is not defined or unknown.

    The class also includes a method for getting the choice corresponding to a given label.
    """

    DIRECT = 'Direct', label('direct')
    INDIRECT = 'Indirect', label('indirect')
    REFERENCED = 'Referenced', label('referenced')  # may needs to be removed
    UNKNOWN = 'Unknown', label('unknown')

    @classmethod
    def get_choice(cls, label: str):
        """
        Get the choice corresponding to a given label. If the label does not match any choice, it returns UNKNOWN.

        Parameters:
        - label (str): The label of the choice.

        Returns:
        - str: The choice corresponding to the given label.
        """
        for choice in cls.choices:
            if choice[1] == label.lower():
                return choice[0]
        return cls.UNKNOWN


class Citation(models.Model):
    """
    The Citation class is a Django model that represents a citation in a Check instance. It contains fields that store the Check instance it is associated with, the text of the citation, the type of the citation, and whether the citation is replaced by a new user set/corrected citation or if the text is found identical in chunk.

    Attributes:
    - of_check (Check): The Check instance that the citation is associated with.
    - replaced (BooleanField): A boolean value that indicates whether the citation is replaced by a new user set/corrected citation.
    - text (TextField): The text of the citation.
    - user_text (BooleanField): A boolean value that indicates if the text is found identical in chunk (not edited by original document view with any text).
    - type (CharField): The type of the citation. It is a choice field that uses the CitationType choices.

    The class also includes methods for getting a string representation of the Citation instance and for setting the latest citation.
    """


    # for correction of citations and later reinforcement learning Multi-to-One relation with Check
    # (current citation callable there too)
    of_check = models.ForeignKey("Check", on_delete=models.CASCADE, related_name='citations')
    replaced = models.BooleanField(default=False)  # to be marked as replaced by new user set/corrected citation
    text = models.TextField(max_length=511)
    user_text = models.BooleanField(
        default=False)  # if text is found identical in chunk (not edited by original document view with any text))
    type = models.CharField(max_length=50, choices=CitationType.choices, default=CitationType.UNKNOWN)

    def __str__(self):
        return self.text

    def set_latest(self):
        """
        Set the current Citation instance as the latest citation. It marks all other citations associated with the same Check instance as replaced.
        """
        for citation in self.of_check.citations.filter(replaced=False).exclude(self):
            citation.replaced = True
            citation.save()
        self.replaced = False
        self.save()


class Reference(models.Model):
    """
    The Reference class is a Django model that represents a reference in a Check instance. It contains fields that store the Check instance it is associated with, the citation marker of the reference, the source of the reference, the chunk ID of the reference paper, the extraction of the reference, and whether the reference is primary or not.

    Attributes:
    - of_check (Check): The Check instance that the reference is associated with.
    - replaced (BooleanField): A boolean value that indicates whether the reference is replaced by a new user set/corrected reference.
    - citation_marker (CharField): The citation marker of the reference.
    - source (ForeignKey): The source of the reference. It is a foreign key that points to a Source instance.
    - reference_paper_chunk_id (IntegerField): The chunk ID of the reference paper. This is set after finding and extracting the reference.
    - extraction (TextField): The extraction of the reference.
    - is_primary (BooleanField): A boolean value that indicates whether the source paper is the origin of the statement.

    The class also includes methods for getting a string representation of the Reference instance, for setting the latest reference, and for getting a representation of the Reference instance for debugging purposes.
    """


    # for correction of references and later reinforcement learning Multi-to-One relation with Check
    # (current reference callable there too)
    of_check = models.ForeignKey("Check", on_delete=models.CASCADE, related_name='references')
    replaced = models.BooleanField(default=False)

    citation_marker = models.CharField(max_length=255)
    source = models.ForeignKey(Source, on_delete=models.SET_NULL, null=True, blank=True)

    # set after finding and extracting reference
    reference_paper_chunk_id = models.IntegerField(null=True, blank=True)  # TODO adopt to chroma DB reference
    extraction = models.TextField(null=True, blank=True)
    is_primary = models.BooleanField(default=True)  # if source paper is origin of statement

    def __str__(self):
        return self.citation_marker

    def __repr__(self):
        return f"Reference(of_check={self.of_check}, citation_marker={self.citation_marker}, source={self.source}, source_paper_chunk_id={self.reference_paper_chunk_id}, is_primary={self.is_primary}, extraction={self.extraction}, replaced={self.replaced})"

    def set_latest(self):
        """
        Set the current Reference instance as the latest reference. It marks all other references associated with the same Check instance as replaced.
        """
        for reference in self.of_check.references.filter(replaced=False).exclude(self):
            reference.replaced = True
            reference.save()
        self.replaced = False
        self.save()


class Check(models.Model):
    """
    The Check class is a Django model that represents a check in the system. It contains various fields that store information about the check, such as the paper it is associated with, the chunk ID, the short difference, the semantic difference, the score, the user score, and whether it is a false positive.

    Attributes:
    - paper (Paper): The paper that the check is associated with.
    - chunk_id (int): The chunk ID of the check.
    - difference_short (CharField): The short difference of the check. This is set by the LLM result.
    - semantic_difference (TextField): The semantic difference of the check. This is set by the LLM result.
    - score (IntegerField): The score of the check. This is set by the LLM result.
    - user_score (IntegerField): The user score of the check. If set, it is marked as checked.
    - false_positive (BooleanField): A boolean value that indicates whether the check is a false positive. It is to be marked as falsely detected Reference by LLM.
    """


    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='checks')
    # assumption: citation & reference(citation marker) are always in the same chunk (no split/new page in/between citation or reference/citation-marker)
    chunk_id = models.IntegerField()
    difference_short = models.CharField(max_length=100, null=True, blank=True)  # set by LLM result, summarization of difference
    semantic_difference = models.TextField(null=True, blank=True)  # set by LLM result
    score = models.IntegerField(null=True, blank=True)  # set by LLM result
    user_score = models.IntegerField(null=True, blank=True)  # If set -> marked as checked
    false_positive = models.BooleanField(default=False)  # to be marked as falsely detected Reference by LLM

    def remove(self):
        """
        Mark the current Check instance as a false positive.
        """
        self.false_positive = True
        self.save()

    @classmethod
    async def from_extraction(cls, paper: Paper, chunk_id: int, claim: str, citation_marker: str, citation_type: str):
        """
        Create a new Check instance from an extraction.

        Parameters:
        - paper (Paper): The paper that the check is associated with.
        - chunk_id (int): The chunk ID of the check.
        - claim (str): The claim of the check.
        - citation_marker (str): The citation marker of the check.
        - citation_type (str): The citation type of the check.

        Returns:
        - tuple: A tuple containing the new Check instance, the Citation instance, and the Reference instance.
        """

        citation_type = CitationType.get_choice(citation_type)
        if await Check.objects.filter(citations__text=claim, citations__replaced=False, paper=paper, references__citation_marker=citation_marker, references__replaced=False).aexists():
            check = await Check.objects.select_for_update().prefetch_related('citations', 'references').aget(citations__text=claim, citations__replaced=False, paper=paper, references__citation_marker=citation_marker, references__replaced=False)
            check.chunk_id = chunk_id
            citation = await sync_to_async(getattr)(check, 'citation')
            # citation = check.citation
            reference = await sync_to_async(getattr)(check, 'reference')
            # reference = check.reference
            citation.type = citation_type
            await check.asave()
            await citation.asave()
            return check, citation, reference
        else:
            check = await cls.objects.acreate(paper=paper, chunk_id=chunk_id)
            citation = await Citation.objects.acreate(of_check=check, text=claim, type=citation_type)
            reference = await Reference.objects.acreate(of_check=check, citation_marker=citation_marker)
            return check, citation, reference

    @property
    def chunk(self):
        """
        Get the chunk of the check. It retrieves the chunk from the Chroma collection of the paper it is associated with.

        Returns:
        - tuple: A tuple containing the metadata and the content of the chunk.
        """
        if not self.paper.chroma_collection:
            return {}, ''
        collection = getChromaCollection(self.paper.chroma_collection)
        chroma_return = collection.get(ids=[str(self.chunk_id)])
        metadata, page_content = chroma_return['metadatas'][0], chroma_return['documents'][0]
        return metadata, page_content

    @property
    def page(self):
        """
        Get the page of the chunk.

        Returns:
        - int: The page of the chunk.
        """
        return self.chunk[0].get('page', -1)

    @property
    def citation(self):
        """
        Get the citation of the check. If there are multiple citations, it sets the latest one.

        Returns:
        - Citation: The citation of the check.
        """
        citations = self.citations.filter(replaced=False).order_by('-id')  # ordered by newest to keep that
        if not citations:
            return None
        if len(citations) > 1:
            citations.first().set_latest()
        return citations.first()

    @property
    def reference(self):
        """
        Get the reference of the check. If there are multiple references, it sets the latest one.

        Returns:
        - Reference: The reference of the check.
        """
        references = self.references.filter(replaced=False).order_by('-id')  # ordered by newest to keep that
        if not references:
            return None
        if len(references) > 1:
            references.first().set_latest()
        return references.first()

    # TODO check if working properly/needed/handled in Citation/Reference class
    @citation.setter
    def citation(self, value: Citation):
        """
        Set the citation of the check.

        Parameters:
        - value (Citation): The new citation of the check.
        """
        value.of_check = self
        value.save()
        value.set_latest()

    @reference.setter
    def reference(self, value: Reference):
        """
        Set the reference of the check.

        Parameters:
        - value (Reference): The new reference of the check.
        """
        value.of_check = self
        value.save()
        value.set_latest()



    def __str__(self):
        return f"Check: '{self.citation}' and '{self.reference.extraction if self.reference else self.references.last()}' differ in: {self.difference_short}"
