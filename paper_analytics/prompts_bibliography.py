# Bibliography Prompts
from langchain.prompts import ChatPromptTemplate
from paper_manager.models import Languages

# TODO maybe alternative prompt for citation styles without citation marker in the bibliography
cleaning_prompt_with_identifier = ChatPromptTemplate.from_template(
        """Your role as an AI language model is to assist in organizing and formatting academic text with precision.
        I have a bibliography section from a scientific paper, containing multiple entries. Your task is to format 
        these entries by ensuring each one is separated by exactly 3 linebreaks (\"\\n\\n\\n\"). Additionally, it's crucial that each entry retains its identifier at the entries identifiers. 
        Exclude any text that isn't part of a bibliography entry, most commonly at the beginning of the chunk, 
        but pay attention to not accidentally remove parts of an bibliography entry.
        
        Here's the text chunk:
        {bib_chunk}
        \n
        Please pay close attention to formatting. 
        Ensure each bibliography entry starts with its identifier and is followed by exactly three linebreaks 
        before the next entry. Exclude non-bibliography text."""
    )

cleaning_prompt = ChatPromptTemplate.from_template(
        """Your role as an AI language model is to assist in organizing and formatting academic text with precision.
        I have a bibliography section from a scientific paper, containing multiple entries. Your task is to format 
        these entries by ensuring each one is separated by exactly three linebreaks. Additionally, it's crucial that 
        each entry retains its identifier at the start. Exclude any text that isn't part of a bibliography entry. 
        Here's the text chunk:
        {bib_chunk}
        \n
        Begin your response by stating the chunk_id in the first line. 
        Please pay close attention to formatting. 
        Ensure each bibliography entry starts with its identifier and is followed by exactly three linebreaks 
        before the next entry. Exclude non-bibliography text."""
    )


second_prompt_IEEE = ChatPromptTemplate.from_template(
    """Your role as an AI language model is to assist in formatting academic text with precision. You are tasked with analyzing the provided bibliography entries and converting each into a well-structured JSON object. The JSON object should adhere to the following format:

1. "reference": A string containing the complete passage of the bibliography entry.
2. "title": A string representing the title of the referenced work.
3. "authors": An array of strings, with each entry being one author's name. This array can be empty or contain one or more strings.
4. "publisher": A string indicating the publisher of the work. If the publisher is not specified in the bibliography entry, leave this as an empty string.
5. "year": A string representing the year of publication. If the year is not specified in the bibliography entry, leave this as an empty string.
6. "chunk_id": A string representing the chunk_id specified at the beginning of the input text chunk.
7. "link": A string representing the link of the bibliography entry, if provided. If no link is specified, leave this as an empty string.
8. "identifier": A string representing the identifier of the bibliography entry, including any brackets or formatting used in the original citation. If no identifier is specified, leave this as an empty string.

The input for processing is as follows:

{text_chunk}
"""
)

extraction_prompt_IEEE = ChatPromptTemplate.from_messages([
    ("system", f"""Your role as an AI language model is to assist in analyzing academic text with precision. You are tasked with processing a bibliography section provided by the user and extract and save all bibliography entries, each as entity together with its properties as a well-structured JSON object by calling the 'information_extraction' function.
To do so, take all the time you need to carefully think and execute the following steps:
1. First localize ALL bibliography entries (the entities), means find the start marked by the identifier and end of each specification of a referenced work (IEEE citation style is used).
2. Then for each entry retrieve/specify all it's provided properties (description follows) if available. At this point it is important that parts of an entry can be relevant for multiple properties. Don't be satisfied with just the reference property.
3. Based on the given properties, try to guess the 'type' (kind of the referenced work) and 'language' (language of the referenced work) property.
4. Finally extract and save all properties (at bare minimum 'identifier', 'reference', 'title' & 'authors' required) of each bibliography entry (the entity) by calling the 'information_extraction' function.

An bibliography entry (the extracted entity) can have varying properties, some are required, some typically (depending on the reference type) are included in a bibliography entry and are more important to extract, others are not that common and less important, so can be skipped if you are not sure about the correctness.

The required properties are:
- "identifier": A string representing the identifier of the bibliography entry, in the format "[number]" like e.g. [1], [27] or [60].
- "reference": A string containing the complete passage of the bibliography entry. Identical to the bibliography entry in the provided section including the identifier. Does NOT replace setting the other properties. Always extract 'identifier', 'title' & 'authors' too.
- "title": A string representing the title of the referenced work. Pay attention to not mix up the references title (this property) and the may given name of a journal or other format the work got published in ('publisher' property).
- "authors": An array of strings, with each entry being one author's name. This array can be empty or contain one or more strings.

Other important properties are:
- "publisher": A string indicating the publisher of the work. Could be a regular publisher, journal, organization, institution, company or other format the work got published in. If the publisher is not specified also don't use author or title as publisher.
- "year": An integer representing the year of publication.
- "url": A string representing the link of the bibliography entry, if provided.
- "pages": A string representing the specification in the bibliography entry what part of the referenced work was used. A range of pages like 56-109. This is specified only if just parts of the referenced work were used.
- "volume": A string representing the volume name and number/edition the referenced work got published in. Often introduced by "In". Not uncommonly mentioned in combination with a date. Only use this property if the work is part of a series or journal.
- "type": A string representing the type or kind of the referenced work. Something like "book", "article", "thesis", "website", etc. This is not specified in the bibliography entry directly but can be inferred from the provided informations.
- "language": A string representing the language of the referenced work. This is not specified in the bibliography entry directly but can be inferred from the title and maybe the publisher. Should be a ISO 639-1 code.

Further properties are:
- "location": A string representing the location of the publication of the work. If a location is given in the bibliography entry it's usually this property.
- "ISBN": A string representing the ISBN of the referenced work.
- "DOI": A string representing the DOI of the referenced work. If a DOI is given as doi.org url save the doi slug in this property.
Remember that not all properties are always present in a bibliography entry, so you have to check for each property if it is present in the current entry, but try to extract as many properties as possible.

Extract ALL bibliography entries and all their provided properties from the given text chunk and save them by calling the 'information_extraction' function.
NEVER only extract the reference property, allways extract all provided properties. If an entity (bibliography entry) has no identifier, title or author, the entity is not valid, so drop it and don't extract/save it.
"""),
    ("user", "{bib_chunk}")
])


#kinda working
extraction_prompt____ = ChatPromptTemplate.from_messages([
    ("system", f"""Extract all complete bibliography entries from the text section given by the user. Extract each reference/entry as entity together with ALL its properties as a well-structured JSON object by calling the 'information_extraction' function. (at least 'reference', 'title' and 'authors' parameter set)
The goal is to retrieve a complete list of all bibliography entries, each with all its individual provided properties. This list will be used in the next step to get all references, so the title and authors are particularly important and must be extracted.

A bibliography entry (to be extracted entity) can have varying properties.

'reference', 'title' and 'authors' properties are always required properties:
- "reference": A string containing the complete passage of the bibliography entry. Identical to the bibliography entry in the provided section. Does NOT replace the other properties. Others can be extracted from this property.
- "title": The title of the referenced work. Pay attention to not mix up the references title (this property) and the may given name of a journal or other format the work got published in ('publisher' property). Needs to be always extracted.
- "authors": An array of strings, with each entry being one author's name. This array can be empty or contain one or more strings. Always needs to be set, even if empty.

Other important properties that are typically (depending on the reference type) included in a bibliography entry and are valuable to be extracted are:
- "identifier": A string representing the identifier of the bibliography entry, including any brackets or formatting used in the original citation. Different referencing styles use different identifiers or no identifier at all, so this can be any sequence of chars or not specified.
- "publisher": A string indicating the publisher of the work. Could be a regular publisher, journal, organization, institution, company or other format the work got published in. If the publisher is not specified also don't use author or title as publisher.
- "year": An integer representing the year of publication.
- "url": A string representing the link to the referenced work, if provided.
- "pages": A string representing the specification in the bibliography entry what part of the referenced work was used. A range of pages like 56-109. This is specified only if just parts of the referenced work were used.
- "volume": A string representing the volume name and number/edition the referenced work got published in. Often introduced by "In". Not uncommonly mentioned in combination with a date. Only use this property if the work is part of a series or journal.
- "type": A string representing the type or kind of the referenced work. Something like "book", "article", "thesis", "website", etc. This is not specified in the bibliography entry directly but can be inferred from the provided informations.
- "language": A string representing the language of the referenced work. This is not specified in the bibliography entry directly but can be inferred from the title and maybe the publisher. Should be specified as an ISO 639-1 code.

Further properties that are not that common and less important, so can be skipped if you are not sure about the correctness are:
- "location": A string representing the location of the publication of the work. If a location is given in the bibliography entry it's usually this property.
- "ISBN": A string representing the ISBN of the referenced work.
- "DOI": A string representing the DOI of the referenced work. If a DOI is given as doi.org url save the doi slug in this property.

Specify the properties of a bibliography entry individually for each entry. Different entries can have different properties.
The 'type' (kind of the referenced work) and 'language' (language of the referenced work) properties need to be guessed based on the other properties.
Don't extract incomplete entries or other irrelevant text that may occur at the beginning or end of the provided text chunk.
Only call the 'information_extraction' function if at least the 'reference', 'title' & 'authors' (can be empty) properties are set.
"""),
    ("user", "{bib_chunk}")
])

#always working, could extract more properties, need to filter for existing title attribute/key
extraction_prompt___ = ChatPromptTemplate.from_messages([
    ("system", f"""Extract all complete bibliography entries from the text section given by the user. Extract each reference/entry as entity together with ALL its properties as a well-structured JSON object by calling the 'information_extraction' function. (at least 'reference', 'title' and 'authors' parameter set)
The goal is to retrieve a list of all complete bibliography entries, each with all its individual provided properties. This list will be used in the next step to get all references, so the title and authors are particularly important and must be extracted.

A bibliography entry (to be extracted entity) can have varying properties.

'reference', 'title' and 'authors' properties are always required properties:
- "reference": A string containing the complete passage of the bibliography entry. Identical to the bibliography entry in the provided section. Does NOT replace the other properties. Others can be extracted from this property.
- "title": The title of the referenced work. Pay attention to not mix up the references title (this property) and the may given name of a journal or other format the work got published in ('publisher' property). Needs to be always extracted.
- "authors": An array of strings, with each entry being one author's name. This array can be empty or contain one or more strings. Always needs to be set, even if empty.

Other important properties that are typically (depending on the reference type) included in a bibliography entry and are valuable to be extracted are:
- "identifier": A string representing the identifier of the bibliography entry, including any brackets or formatting used in the original citation. Different referencing styles use different identifiers or no identifier at all, so this can be any sequence of chars or not specified.
- "publisher": A string indicating the publisher of the work. Could be a regular publisher, journal, organization, institution, company or other format the work got published in. If the publisher is not specified also don't use author or title as publisher.
- "year": An integer representing the year of publication.
- "url": A string representing the link to the referenced work, if provided.
- "pages": A string representing the specification in the bibliography entry what part of the referenced work was used. A range of pages like 56-109. This is specified only if just parts of the referenced work were used.
- "volume": A string representing the volume name and number/edition the referenced work got published in. Often introduced by "In". Not uncommonly mentioned in combination with a date. Only use this property if the work is part of a series or journal.
- "type": A string representing the type or kind of the referenced work. Something like "book", "article", "thesis", "website", etc. This is not specified in the bibliography entry directly but can be inferred from the provided informations.
- "language": A string representing the language of the referenced work. This is not specified in the bibliography entry directly but can be inferred from the title and maybe the publisher. Should be specified as an ISO 639-1 code.

Further properties that are not that common and less important, so can be skipped if you are not sure about the correctness are:
- "location": A string representing the location of the publication of the work. If a location is given in the bibliography entry it's usually this property.
- "ISBN": A string representing the ISBN of the referenced work.
- "DOI": A string representing the DOI of the referenced work. If a DOI is given as doi.org url save the doi slug in this property.

Specify the properties of a bibliography entry individually for each entry. Different entries can have different properties.
Specify each property independently. Extract as many properties as possible by considering all parts of the entry.
The 'type' (kind of the referenced work) and 'language' (language of the referenced work) properties need to be derived from/guessed based on the other properties.
Don't extract incomplete entries or other irrelevant text that may occur at the beginning or end of the provided text chunk.
Only call the 'information_extraction' function if at least the 'reference', 'title' & 'authors' (can be empty) properties are set.
"""),
    ("user", "{bib_chunk}")
])

extraction_prompt__ = ChatPromptTemplate.from_messages([
    ("system", f"""Act as an research assistant proofreading a thesis. You are tasked with extracting and saving all bibliography entries from a given section for further content check. Extract each reference/entry as entity together with all its given properties by calling the 'information_extraction' function.
    The goal is to have a complete list of all bibliography entries, each with all its in the text provided properties. The title and authors are especially important to query those works in the next step.

Take all the time you need to carefully think and execute your task in the following steps:
1. First localize all bibliography entries (the entities), means find the start and end of each specification of a referenced work.
Then for each entry independently/separately:
2. Set the complete passage of the bibliography entry as the 'reference' property.
3. Extract the title and authors of the referenced work from the 'reference' property. They are always present and required to extract.
4. Retrieve/specify as much further information as possible from the 'reference' property. At this point it is important that parts of the entry/'reference' can be relevant for multiple properties. Every bibliography entry has at least the three properties that need to be extracted: 'reference', 'title' and 'authors'. Different entries can have different given properties. All properties can be extracted from the 'reference' property.
5. Based on the so far identified properties, try to guess the entry's 'type' (kind of the referenced work) and 'language' (language of the referenced work) property too.
6. Finally extract and save all provided properties of an bibliography entry (the entity) by calling the 'information_extraction' function.

An bibliography entry (the extracted entity) can have varying properties. 'reference', 'title' and 'authors' are always required, some are typically (depending on the reference type) included in a bibliography entry and are more important to extract, others are not that common and less important, so can be skipped if you are not sure about the correctness.

The required and always present properties:
- "reference": A string containing the complete passage of the bibliography entry. Identical to the bibliography entry in the provided section. Does NOT replace the other properties. Others can be extracted from this property.
- "title": The title of the referenced work. Pay attention to not mix up the references title (this property) and the may given name of a journal or other format the work got published in ('publisher' property).
- "authors": An array of strings, with each entry being one author's name. This array can be empty or contain one or more strings.

Other important properties are:
- "identifier": A string representing the identifier of the bibliography entry, including any brackets or formatting used in the original citation. Different referencing styles use different identifiers or no identifier at all, so this can be any sequence of chars or not specified.
- "publisher": A string indicating the publisher of the work. Could be a regular publisher, journal, organization, institution, company or other format the work got published in. If the publisher is not specified also don't use author or title as publisher.
- "year": An integer representing the year of publication.
- "url": A string representing the link of the bibliography entry, if provided.
- "pages": A string representing the specification in the bibliography entry what part of the referenced work was used. A range of pages like 56-109. This is specified only if just parts of the referenced work were used.
- "volume": A string representing the volume name and number/edition the referenced work got published in. Often introduced by "In". Not uncommonly mentioned in combination with a date. Only use this property if the work is part of a series or journal.
- "type": A string representing the type or kind of the referenced work. Something like "book", "article", "thesis", "website", etc. This is not specified in the bibliography entry directly but can be inferred from the provided informations.
- "language": A string representing the language of the referenced work. This is not specified in the bibliography entry directly but can be inferred from the title and maybe the publisher. Should be a ISO 639-1 code.

Further properties are:
- "location": A string representing the location of the publication of the work. If a location is given in the bibliography entry it's usually this property.
- "ISBN": A string representing the ISBN of the referenced work.
- "DOI": A string representing the DOI of the referenced work. If a DOI is given as doi.org url save the doi slug in this property.
Remember that not all properties are always present in a bibliography entry, so you have to check for each property if it is present in the current entry and extract only the present ones.

Extract ALL bibliography entries with their properties from the given text chunk and save them by calling the 'information_extraction' function.
NEVER only extract the reference property, allways extract all provided properties. If an entity (bibliography entry) has no title or author, the entity is not valid, so drop it and don't extract/save it.
"""),
    ("user", "{bib_chunk}")
])

extraction_prompt_ = ChatPromptTemplate.from_messages([
    ("system", f"""Your role as an AI language model is to assist in analyzing academic text with precision. You are tasked with processing a bibliography section provided by the user and extract and save all bibliography entries that have at least the required properties 'reference', 'title', 'authors'. Extract each Reference as entity together with all its given properties by calling the 'information_extraction' function.
To do so, take all the time you need to carefully think and execute the following steps:
1. First localize all bibliography entries (the entities), means find the start and end of each specification of a referenced work. Especially at the beginning and end of the provided text, there can be some additional text that is not part of a bibliography entry or a cut off entry and thus should be ignored.
Then for each entry independently/separately:
2. Retrieve/specify all it's provided properties (description follows). At this point it is important that parts of an entry can be relevant for multiple properties. Every bibliography entry has at least the three properties 'reference', 'title' and 'authors'. Different entries can have different given properties. All properties can be extracted from the 'reference' property.
3. Based on the given properties for an entry, try to guess its 'type' (kind of the referenced work) and 'language' (language of the referenced work) property too.
4. Finally extract and save all provided properties of an bibliography entry (the entity) by calling the 'information_extraction' function.

An bibliography entry (the extracted entity) can have varying properties. 'reference', 'title' and 'authors' are always required, some are typically (depending on the reference type) included in a bibliography entry and are more important to extract, others are not that common and less important, so can be skipped if you are not sure about the correctness.

The required properties:
- "reference": A string containing the complete passage of the bibliography entry. Identical to the bibliography entry in the provided section. Does NOT replace the other properties. Others can be extracted from this property.
- "title": A string representing the title of the referenced work. Pay attention to not mix up the references title (this property) and the may given name of a journal or other format the work got published in ('publisher' property).
- "authors": An array of strings, with each entry being one author's name. This array can be empty or contain one or more strings.

Other important properties are:
- "identifier": A string representing the identifier of the bibliography entry, including any brackets or formatting used in the original citation. Different referencing styles use different identifiers or no identifier at all, so this can be any sequence of chars or not specified.
- "publisher": A string indicating the publisher of the work. Could be a regular publisher, journal, organization, institution, company or other format the work got published in. If the publisher is not specified also don't use author or title as publisher.
- "year": An integer representing the year of publication.
- "url": A string representing the link of the bibliography entry, if provided.
- "pages": A string representing the specification in the bibliography entry what part of the referenced work was used. A range of pages like 56-109. This is specified only if just parts of the referenced work were used.
- "volume": A string representing the volume name and number/edition the referenced work got published in. Often introduced by "In". Not uncommonly mentioned in combination with a date. Only use this property if the work is part of a series or journal.
- "type": A string representing the type or kind of the referenced work. Something like "book", "article", "thesis", "website", etc. This is not specified in the bibliography entry directly but can be inferred from the provided informations.
- "language": A string representing the language of the referenced work. This is not specified in the bibliography entry directly but can be inferred from the title and maybe the publisher. Should be a ISO 639-1 code.

Further properties are:
- "location": A string representing the location of the publication of the work. If a location is given in the bibliography entry it's usually this property.
- "ISBN": A string representing the ISBN of the referenced work.
- "DOI": A string representing the DOI of the referenced work. If a DOI is given as doi.org url save the doi slug in this property.
Remember that not all properties are always present in a bibliography entry, so you have to check for each property if it is present in the current entry and extract only the present ones.

Extract ALL bibliography entries with its individually provided properties from the given text chunk and save them by calling the 'information_extraction' function.
NEVER only extract the reference property, allways extract all provided properties. If an entity (bibliography entry) has no title or author, the entity is not valid, so drop it and don't extract/save it.
"""),
    ("user", "{bib_chunk}")
])

# default prompt, can be forked to be more specific on different citation styles
# best results, but sometimes does not extract required title -> exception
extraction_prompt = ChatPromptTemplate.from_messages([
    ("system", f"""Your role as an AI language model is to assist in analyzing academic text with precision. You are tasked with processing a bibliography section provided by the user and extract and save all bibliography entries, each as entity together with its properties as a well-structured JSON object by calling the 'information_extraction' function.
To do so, take all the time you need to carefully think and execute the following steps:
1. First localize ALL bibliography entries (the entities), means find the start and end of each specification of a referenced work.
2. Then for each entry retrieve/specify all it's provided properties (description follows) if available. At this point it is important that parts of an entry can be relevant for multiple properties. Don't be satisfied with just the reference property.
3. Based on the given properties, try to guess the 'type' (kind of the referenced work) and 'language' (language of the referenced work) property.
4. Finally extract and save all properties (at bare minimum 'reference', 'title' & 'authors' required) of each bibliography entry (the entity) by calling the 'information_extraction' function.

An bibliography entry (the extracted entity) can have varying properties, some are required, some typically (depending on the reference type) are included in a bibliography entry and are more important to extract, others are not that common and less important, so can be skipped if you are not sure about the correctness.

The required properties are:
- "reference": A string containing the complete passage of the bibliography entry. Identical to the bibliography entry in the provided section. Does NOT replace the other properties. Always extract 'title' & 'authors' too.
- "title": A string representing the title of the referenced work. Pay attention to not mix up the references title (this property) and the may given name of a journal or other format the work got published in ('publisher' property).
- "authors": An array of strings, with each entry being one author's name. This array can be empty or contain one or more strings.

Other important properties are:
- "identifier": A string representing the identifier of the bibliography entry, including any brackets or formatting used in the original citation. Different referencing styles use different identifiers or no identifier at all, so this can be any sequence of chars or not specified.
- "publisher": A string indicating the publisher of the work. Could be a regular publisher, journal, organization, institution, company or other format the work got published in. If the publisher is not specified also don't use author or title as publisher.
- "year": An integer representing the year of publication.
- "url": A string representing the link of the bibliography entry, if provided.
- "pages": A string representing the specification in the bibliography entry what part of the referenced work was used. A range of pages like 56-109. This is specified only if just parts of the referenced work were used.
- "volume": A string representing the volume name and number/edition the referenced work got published in. Often introduced by "In". Not uncommonly mentioned in combination with a date. Only use this property if the work is part of a series or journal.
- "type": A string representing the type or kind of the referenced work. Something like "book", "article", "thesis", "website", etc. This is not specified in the bibliography entry directly but can be inferred from the provided informations.
- "language": A string representing the language of the referenced work. This is not specified in the bibliography entry directly but can be inferred from the title and maybe the publisher. Should be a ISO 639-1 code.

Further properties are:
- "location": A string representing the location of the publication of the work. If a location is given in the bibliography entry it's usually this property.
- "ISBN": A string representing the ISBN of the referenced work.
- "DOI": A string representing the DOI of the referenced work. If a DOI is given as doi.org url save the doi slug in this property.
Remember that not all properties are always present in a bibliography entry, so you have to check for each property if it is present in the current entry, but try to extract as many properties as possible.

Extract ALL bibliography entries and all their provided properties from the given text chunk and save them by calling the 'information_extraction' function.
NEVER only extract the reference property, allways extract all provided properties. If an entity (bibliography entry) has no title or author, the entity is not valid, so drop it and don't extract/save it.
"""),
    ("user", "{bib_chunk}")
])
