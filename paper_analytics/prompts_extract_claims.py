from langchain.prompts import ChatPromptTemplate

IEEE_based_on_markers = ChatPromptTemplate.from_template(
    "This is the text: {text_chunk}    \n \
    This is the markers list: {markers}     \n   \
    Return from the text: \n    \
    - 'marker': marker    \n \
    - 'claim': the sentence containing the marker  \n  \
    Return for each number a JSON object"
)

IEEE_based_on_markers2_tilli = ChatPromptTemplate.from_template(
    "A matching task. For every entry in the marker list find the sentence in the text.        \n   \
    Text: {text_chunk}    \n \
    Marker list: {marker}     \n      \
    Important you response like this because I will use it to convert in JSON after.       \n      \
    If Marker list is empty dont response only '0'"
)

IEEE_based_on_markers3_tilli = ChatPromptTemplate.from_template(
    "Look for the statements marked with a reference in the text.  \n"
    "The list of markers to look for: {marker} \n"
    "The text: \n {text_chunk} \n"

)

IEEE_based_on_markers_linus = ChatPromptTemplate.from_template(
    "Your task is to extract all citations from the given text.\n"
    "Therefore, first identify each provided marker from the list in the text."
    "Then for each marker figure out which neighboring passage makes the statement/claim that is proven by the referenced work. This is the 'citation' property and core of your task, to set the correct scope of the citations claim."
    "Finally extract and save all properties of each reference (the entity) by calling the 'information_extraction' function.\n\n"
    "The citation marker are: {marker}\n"
    "The Text is:\n{text_chunk}"
)

IEEE_based_on_markers2 = ChatPromptTemplate.from_template(
    "For every provided IEEE citation marker extract the corresponding citation.\n"
    "The citation is the statement or claim of the author next to the citation marker.\n"
   # "Extract the citation/claim exactly as it stands in the text."
   # "and citation type ('direct', 'indirect', 'referenced' & 'undefined') from the text.\n"
    "The citation markers are: {marker}\n"
    "Text:\n{text_chunk}"
)

# If the markers list is empty return: 'no citations'

#     From the text return all sentences which include the IEEE markers, like this: - marker, sentence \n \
#     It is important that you return it like this because I need it to format to JSON after \n \
#     Also, if the markers list is empty just return number 0"

APA = ChatPromptTemplate.from_template(
    """"
    This is the text:
    
    {text_chunk}
    \n
    Extract references from Text. References are marked with (name of author, publishing year) and only like this. \
    Put the tuple together with the reference. Multiple references like (name, year; name2, year2), return separately \
    Return the following for every reference:
        - (name of author, publishing year) \
        - the sentence without the tupel \
    I need to convert your response into a json file so it is extremely important that you return it exactly this way.
    """
)

IEEE = ChatPromptTemplate.from_template(
    " This is the Text: {text_chunk} \n \
    From the text: Find the citations marked with [number] (IEEE) as 'citation_marker'. If multiple numbers, return separately"
)

# default prompt, can be forked to be more specific on different citation styles
extraction_prompt_ = ChatPromptTemplate.from_messages([
    ("system", f"""Your role as an AI language model is to assist in analyzing academic text with precision. You task is to extract and save all references from a scientific paper section, provided by the user, by calling the 'information_extraction' function. Extract each reference as entity together with its properties as a well-structured JSON object.
To do so, take all the time you need to carefully think and execute the following steps:
1. First localize all citations, direct and indirect ones, by searching for citation markers in the text, there is no citation/reference without a citation marker. Depending on the citation style, the citation marker can be a number, combination of name(s) and year or another combination of characters establishing a relation to a bibliography entry. The citation marker is the part of the text that is used to reference a work. It is extracted as the 'citation_marker' property. Don't mix up citation marker and abbreviations used in the text.
2. Then for each marker figure out which neighboring passage makes the statement/claim that is proven by the referenced work. This is the 'claim' property and core of your task, to set the correct scope of the claim. But still, without citation marker, there can't be reference.
3. After you got the claim, classify the reference in the 'types' property. There are 4 possible types: 'direct', if the claim is a direct quote from the referenced work (quotation marks required), 'indirect', if the claim is a paraphrase or summary of the referenced work (most common), 'referenced', if the referenced work only provides further background or in depth information, and 'unknown', if the type is not clear. But if the type is not clear, reconsider if there is really a reference present.
4. Finally extract and save all properties of each reference (the entity) by calling the 'information_extraction' function.

There are no odds for or against the presence of a reference in the given text, so don't be surprised if there are none.

In short, extract the references/citations from the text, if there are some, together with its properties that are:
- "claim": A string containing the complete passage of the citation, excluding the citation marker. Identical to the corresponding part in the provided section. If the citation is a direct one, the claim is the part of the text that is cited, exactly the citation including the quotation marks. If the citation is a indirect one, the claim is the passage that makes the statement that is proven by the referenced work. At this point you have to carefully evaluate semantics.
- "citation_marker": The string that specifies the referenced work validating the claim. Varies depending on the citation style, but consistent within the provided text. REQUIRED for every reference. examples are [12], (Smith, 2010), or [21, 22].
- "type": Enum of "direct", "indirect", "referenced", "unknown". - 'direct' for direct citation, 'indirect' for paraphrased or summarized referenced work, 'indirect' for background or in-depth references, and 'unknown' as fallback if the type is not clear. unknown should be avoided.

Remember there can be multiple, one or no reference at all!!! Your indicator are citation markers that are obligatory for a reference. If there is no citation marker, there is no reference.
Extract all citations and all their properties from the given text chunk and save them by calling the 'information_extraction' function.
"""),
    ("user", "{text_chunk}")
])

extraction_prompt_I = ChatPromptTemplate.from_messages([
    ("system", f"""The user input is a text chunk from a scientific paper. Scan the text and extract all literature references (the entity) with the 'information_extraction' function if there are any and only if you are 100% sure that its a reference in the users sense.
    A reference is a referral to another literature work or source of information specified in the bibliography.
    
    A reference has two parts, the citation marker (link to the bibliography entry) and the claim.
    The citation marker is the part of the text that is used to refer to a bibliography entry like an identifier or key. It is always one or more numbers in square brackets like [3], [33] or [13, 14, 15] and stands right after the claim. Extract this property exactly as it stands in the text.
    The claim is the part of the text that makes a statement or claim which is proven by the referenced work (linked by the citation marker). Claims made in the text that are not validated by a trailing citation marker are no references, but common statements.
    A citaton can't be without a following citation marker, so if there is no citation marker, there is also not a reference to extract.
    
    Look out for citation markers not statements or claims, cause in a scientific text there are statements everywhere, but you're looking only for references. Extract an reference entity only if you're completely sure that there is a reference present.
    
    Additionally to the citation marker and the claim, you should also extract the type of the reference. There are 4 possible types: 'direct', if the claim is a direct quote from the referenced work (quotation marks required), 'indirect', if the claim is a paraphrase or summary of the referenced work (most common), 'referenced', if the referenced work only provides further background or in depth information, and 'unknown', if the type is not clear. But if the type is not clear, reconsider if there is really a reference present.
    
    Its not rare that there are no references at all in the given text.
    """),
    ("user", "{text_chunk}")
])

extraction_prompt_IEEEE = ChatPromptTemplate.from_messages([
    ("system", f"""The user input is a text chunk from a scientific paper. Extract and save the entity (a literature reference) with the 'information_extraction' function if you find one.
    A reference has two parts, the citation marker and the claim.
    The citation marker is the part of the text that is used to link a bibliography entry like an identifier. It is always one or more numbers in square brackets like [3], [33] or [13, 14, 15] and stands after the claim.
    The claim is the part of the text that makes a statement or claim which is proven by the referenced work (linked by the citation marker). Statements made in the text that are not proven by/tagged with a referenced work/accompained with a citation marker are no references.
    A citaton/reference can't be without a citation marker, so if there is no citation marker, there is also no reference to extract.
    Look out for citation markers not statements or claims.
    Additionally to the citation marker and the claim, you should also extract the type of the reference. There are 4 possible types: 'direct', if the claim is a direct quote from the referenced work (quotation marks required), 'indirect', if the claim is a paraphrase or summary of the referenced work (most common), 'referenced', if the referenced work only provides further background or in depth information, and 'unknown', if the type is not clear. But if the type is not clear, reconsider if there is really a reference present.

    Its not rare that there are no references at all in the given text.
    """),
    ("user", "{text_chunk}")
])

extraction_prompt_IEE = ChatPromptTemplate.from_messages([
    ("system", f"""The user inputs a text chunk from a scientific paper. Extract and save the entity (an IEEE literature reference) with the 'information_extraction' function if you find one.
    A reference has two parts, the citation marker and the claim.
    The citation marker is the part of the text that is used to link a bibliography entry like an identifier. It is in IEEE format, so always one or more numbers in square brackets like [3], [33] or [13, 14, 15] and stands after the claim, sometimes with the mention of the author(s). Extract this property exactly as it stands in the text.
    The claim is the part of the text that makes a statement or claim which is proven by the referenced work (linked by the citation marker in IEEE citation format). Statements made in the text that are not tagged with a citation marker are no references.
    A citaton/reference can't be without a citation marker, so if there is no citation marker, there is also no reference to extract.
    
    Your task is to only briefly scan the priveded text and extract citations in the IEEE standard format.
    To do so simply look out for citation markers not statements or claims and if you fond one extract the corresponding reference (claim & marker) with its citation type using the 'information_extraction' function and the reference as entity.
    Additionally to the citation marker and the claim, you should also extract the type of the reference. There are 4 possible types: 'direct', if the claim is a direct quote from the referenced work (quotation marks required), 'indirect', if the claim is a paraphrase or summary of the referenced work (most common), 'referenced', if the referenced work only provides further background or in depth information, and 'unknown', if the type is not clear. But if the type is not clear, reconsider if there is really a reference present.

    Its common that there are no references at all in the given text.
    """),
    ("user", "{text_chunk}")
])

extraction_prompt_IEEE_ = ChatPromptTemplate.from_messages([
    ("system", f"""From the user input (a scientific paper) extract and save the entities (citation in IEEE reference format) with the 'information_extraction' for each given citation_marker.
    The claim is a part of the text that makes a statement or claim which is proven by the referenced work (linked by the given citation marker in IEEE citation format).
    
    To do so simply look out for citation markers not statements or claims and if you fond one extract the corresponding reference (claim & marker) with its citation type using the 'information_extraction' function and the reference as entity.
    Additionally to the citation marker and the claim, you should also extract the type of the reference. There are 4 possible types: 'direct', if the claim is a direct quote from the referenced work (quotation marks required), 'indirect', if the claim is a paraphrase or summary of the referenced work (most common), 'referenced', if the referenced work only provides further background or in depth information, and 'unknown', if the type is not clear. But if the type is not clear, reconsider if there is really a reference present.

    Its common that there are no references at all in the given text.
    """),
    ("user", "{text_chunk}")
])

extraction_prompt_IEEEX = ChatPromptTemplate.from_messages([
    ("system", "Look out for given citation marker [{marker}] in the text provided by the user.\n"
               "If you find one, extract the corresponding citation (claim) with its citation type using the 'information_extraction' seperately for each marker.\n"
               "The citation/claim is small section or at least the sentence next (typically infront) to the citation marker that makes an assertion or claim which is underpinned/proven by the referenced work (linked by the given citation marker in IEEE citation format). The citation and its marker are coherent and there is only one claim per marker.\n"
               "The citation should extract the whole (coherent) passage that is needed to understand the statement/essence. The context needs to be exactly the scope around the marker to fully get the claim and evaluate if the refrence wittnesses the claim.\n"
               "Additionally to the citation marker and the claim, you should also extract the type of the reference. There are 4 possible types: 'direct', if the claim is a direct quote from the referenced work (quotation marks required), 'indirect', if the claim is a paraphrase or summary of the referenced work (most common), 'referenced', if the referenced work only provides further background or in depth information, and 'unknown', if the type is not clear."
    ),
    ("user", "{text_chunk}")
])

extraction_prompt_IEEX = ChatPromptTemplate.from_messages([
    ("system", "Your Task is to extract the citation/claim for each citation marker from the text.\n"
               "The used citation style is IEEE. For each of the markers {marker} seperately extract the corresponding citation ('claim' property) with its citation type using the 'information_extraction' function.\n"
               "The citation/claim is the small section or at least the sentence next, typically infront of the citation marker that makes an assertion/claim which is underpinned/proven by the referenced work or that mentions something that is explained/talked about in the referenced work. The citation and its marker are adjoint. Extract the citation/claim exactly once for each citation marker.\n"
               "The citation should extract the whole (coherent) passage that is needed to understand the statement/essence. The context needs to be exactly the scope around the marker to fully get the claim and evaluate if the refrence wittnesses the claim.\n"
               "This part is crucial and the core of the task, because it is further used to look up if the information/claim/assertion is indeed found in the referenced work. So its crucial to extract the citation correctly to not blame someone for plagiarism falsely.\n"
               "Additionally to the citation marker and the claim, you should also extract the type of the reference. There are 4 possible types: 'direct', if the claim is a direct quote from the referenced work (quotation marks required), 'indirect', if the claim is a paraphrase or summary of the referenced work (most common), 'referenced', if the referenced work only provides further background or in depth information, and 'unknown', if the type is not clear."
    ),
    ("user", "{text_chunk}")
])

# default prompt, can be forked to be more specific on different citation styles
test_ = ChatPromptTemplate.from_messages([
    ("system", """Your role as an AI language model is to assist in analyzing academic text with precision. Your task is to extract and save all references from a scientific paper section, provided by the user, by calling the 'information_extraction' function.
These references, especially the claims are needed to further check if the information/claim/assertion is indeed found in the referenced work. So its crucial to extract the claim correctly to not blame someone for plagiarism.
Take all the time you need to carefully think and execute the following steps to extract the references:
1. First localize all citations, by searching for the citation markers {marker} in the text. The citation marker is used to reference a work with the IEEE reference style format. It is extracted as the 'citation_marker' property.
2. Then for each marker associate the corresponding claim with the 'claim' property. Therefor you need to figure out the scope of the passage, starting from the citation marker, that makes the statement/claim/mentions sth that is proven/addressed by the referenced work. This is the 'claim' property and core of your task, to extract the claim of the marker. It is allways directly next/adjacent to its marker.
3. After you got the claim, classify the references 'type' property. There are 4 possible types: 'direct', if the claim is a direct quote from the referenced work (quotation marks required), 'indirect', if the claim is a paraphrase or summary of the referenced work (most common), 'referenced', if the referenced work only provides further background or in depth information, and 'unknown', if the type is not clear.
4. Finally extract and save all properties for each reference (the entity)/given marker by calling the 'information_extraction' function.

In short, for each marker, extract the reference/citation together with its properties from the text. The properties are:
- "claim": A string containing the complete passage of the citation. If the citation is a direct one, the claim is the identical part of the text that is cited, including the quotation marks. If the citation is an indirect one, the claim is the passage that makes the statement that is proven by the referenced work or mentions sth from it. It also includes the context if needed for understanding and validation in the referenced work. At this point you have to carefully evaluate semantics.
- "citation_marker": The string that specifies the referenced work validating the claim. The provided marker.
- "type": Enum of "direct", "indirect", "referenced", "unknown". - 'direct' for direct citation, 'indirect' for paraphrased or summarized referenced work, 'referenced' for background or in-depth references, and 'unknown' as fallback if the type is not clear. unknown should be avoided.

Remember that there is exactly one claim/citation per marker. So don't extract multiple claims for one marker.
Extract the claim and its type for each citation, indicated by the provided markers, from the given text chunk and save them by calling the 'information_extraction' function.
"""),
    ("user", "{text_chunk}")
])

# default prompt, can be forked to be more specific on different citation styles
extraction_prompt = ChatPromptTemplate.from_messages([  # works so far for correctly loaded text and statements, not that good for additional information
    ("system", """Your role as an AI language model is to assist in analyzing academic text with precision. Your task is to extract and save all references from a scientific paper section, provided by the user, by calling the 'information_extraction' function.
To do so, take all the time you need to carefully think and execute the following steps:
1. First localize all citations, by searching for the citation markers [{marker}] in the text. The citation marker is used to reference a work. It is extracted as the 'citation_marker' property.
2. Then for each marker figure out the scope of the neighboring passage that makes the statement/claim that is proven by the referenced work. This is the 'claim' property and core of your task, to set the correct scope of the claim. It is allways directly next to the marker.
3. After you got the claim, classify the 'type' property of each reference. There are 4 possible types: 'direct', if the claim is a direct quote from the referenced work (quotation marks required), 'indirect', if the claim is a paraphrase or summary of the referenced work (most common), 'referenced', if the referenced work only provides further background or in depth information, and 'unknown', if the type is not clear.
4. Finally extract and save all properties of each reference (the entity) by calling the 'information_extraction' function.

In short, extract the references/citations from the text, exactly one per marker, together with its properties that are:
- "claim": A string containing the complete passage of the citation. Identical to the corresponding part in the provided section. If the citation is a direct one, the claim is the part of the text that is cited, exactly the citation including the quotation marks. If the citation is a indirect one, the claim is the passage that makes the statement that is proven by the referenced work. At this point you have to carefully evaluate semantics.
- "citation_marker": The string that specifies the referenced work validating the claim. The provided marker.
- "type": Enum of "direct", "indirect", "referenced", "unknown". - 'direct' for direct citation, 'indirect' for paraphrased or summarized referenced work, 'indirect' for background or in-depth references, and 'unknown' as fallback if the type is not clear. unknown should be avoided.

Remember that there is exactly one claim/citation per marker. So don't extract multiple claims for one marker.
Extract all citations and all their properties from the given text chunk and save them by calling the 'information_extraction' function.
"""),
    ("user", "{text_chunk}")
])

# default prompt, can be forked to be more specific on different citation styles
test = ChatPromptTemplate.from_messages([  # works so far for correctly loaded text and statements, not that good for additional information
    ("system", """Your role as an AI language model is to assist in analyzing academic text with precision. Your task is to extract and save all references from a scientific paper section, provided by the user, by calling the 'information_extraction' function.
To do so, take all the time you need to carefully think and execute the following steps:
1. First localize all citations, by searching for the citation markers {marker} in the text. The citation marker is used to reference a work. It is extracted as the 'citation_marker' property.
2. Then for each marker figure out the scope of the neighboring passage that makes the statement/claim or mentions something which is underpinned/proven by the referenced work. This is the 'claim' property and core of your task, to set the correct scope of the claim. It is allways directly next to the marker.
3. After you got the claim, classify the 'type' property of each reference. There are 4 possible types: 'direct', if the claim is a direct quote from the referenced work (quotation marks required), 'indirect', if the claim is a paraphrase or summary of the referenced work (most common), 'referenced', if the referenced work only provides further background or in depth information, and 'unknown', if the type is not clear.
4. Finally extract and save all properties of each reference (the entity) by calling the 'information_extraction' function.

In short, extract the references/citations from the text, exactly one per marker, together with its properties that are:
- "claim": A string containing the complete passage of the citation. Identical to the corresponding part in the provided section. If the citation is a direct one, the claim is the part of the text that is cited, exactly the citation including the quotation marks. If the citation is a indirect one, the claim is the passage that makes the statement that is proven by the referenced work. At this point you have to carefully evaluate semantics.
- "citation_marker": The string that specifies the referenced work validating the claim. The provided marker.
- "type": Enum of "direct", "indirect", "referenced", "unknown". - 'direct' for direct citation, 'indirect' for paraphrased or summarized referenced work, 'indirect' for background or in-depth references, and 'unknown' as fallback if the type is not clear. unknown should be avoided.

Remember that there is exactly one claim/citation per marker. So don't extract multiple claims for one marker.
Extract all citations and all their properties from the given text chunk and save them by calling the 'information_extraction' function.
"""),
    ("user", "{text_chunk}")
])

extraction_prompt_IEEEY = ChatPromptTemplate.from_messages([
    ("system", "Look out for the given citation marker [{marker}] in the text provided by the user.\n"
               "For each marker extract the corresponding citation (claim) with its citation type using the 'information_extraction' seperately for each marker. Repeat it for each marker only once.\n"
               "The citation/claim is small section or at least the sentence next (typically infront) to the citation marker that makes an assertion or claim or mentions something which is underpinned/proven by the referenced work (linked by the given citation marker in IEEE citation format). The citation and its marker are coherent. Extract the claim for a marker only once.\n"
               "The citation should extract the whole (coherent) passage that is needed to understand the statement/essence. The context needs to be exactly the scope around the marker to fully get the claim and evaluate if the refrence wittnesses the claim.\n"
               "Additionally to the citation marker and the claim, you should also extract the type of the reference. There are 4 possible types: 'direct', if the claim is a direct quote from the referenced work (quotation marks required), 'indirect', if the claim is a paraphrase or summary of the referenced work (most common), 'referenced', if the referenced work only provides further background or in depth information, and 'unknown', if the type is not clear."
    ),
    ("user", "{text_chunk}")
])

# TODO maybe read more about Citation classification to improve prompt (just one source: https://oro.open.ac.uk/91832/1/snk_cikm_2023.pdf)

extraction_prompt_IEEE = ChatPromptTemplate.from_messages([  # really good, some exceptions
    ("system", "Look out for the citation marker [{marker}] in the text provided by the user.\n"
               "For each marker evaluate if the reference/marker should only provide additional infos related to something mentioned or if it should underpin/prove a statement/claim in the text.\n"
               "Based on that, extract the corresponding citation (claim) scope with the citation type using the 'information_extraction' function. Repeat this seperately for each marker once.\n"
               "The citation/claim is a small section or sentence making an assertion or claim or mentions something which is underpinned/proven by the referenced work (linked by the given citation marker in IEEE citation format). The citation and its marker are adjacent and the citation is allways next to the citation marker (typically infront of it) without any text inbetween. Extract the claim for a marker only once.\n"
               "Extract the whole passage that is needed to understand the statement/essence as citation. The context needs to be exactly the scope around the marker word by word to fully get the claim and evaluate if the reference wittnesses the claim.\n"
               "Additionally to the citation marker and the claim, you should also extract the type of the reference. There are 4 possible types: 'direct', if the claim is a direct quote from the referenced work (quotation marks required), 'indirect', if the claim is a paraphrase or summary of the referenced work (most common), 'referenced', if the referenced work only provides further background or in depth information, and 'unknown', if the type is not clear."
    ),
    ("user", "The Text:\n{text_chunk}")
])

extraction_prompt_IEEE___ = ChatPromptTemplate.from_messages([
    ("system", "Look out for given citation marker [{marker}] in the text provided by the user.\n"
               "If you find one, evaluate if the reference/marker should only provide additional infos related to something mentioned or if it should underpin/prove a statement/claim.\n"
               "Based on that extract the corresponding citation (claim) scope with the citation type using the 'information_extraction' function. Repeat this seperately for each marker.\n"
               "The citation/claim is a small section or sentence making an assertion or claim or mentions something which is underpinned/proven by the referenced work (linked by the given citation marker in IEEE citation format). The citation and its marker are coherent and the citation is allways next to the citation marker (typically infront of it). There is also only one claim per marker.\n"
               "Extract the whole passage that is needed to understand the statement/essence as citation. The context needs to be exactly the scope around the marker to fully get the claim and evaluate if the refrence wittnesses the claim.\n"
               "Additionally to the citation marker and the claim, you should also extract the type of the reference. There are 4 possible types: 'direct', if the claim is a direct quote from the referenced work (quotation marks required), 'indirect', if the claim is a paraphrase or summary of the referenced work (most common), 'referenced', if the referenced work only provides further background or in depth information, and 'unknown', if the type is not clear."
    ),
    ("user", "{text_chunk}")
])

extraction_prompt_IEEE__ = ChatPromptTemplate.from_messages([  # pretty good
    ("system", "Look out for given citation marker [{marker}] in the text provided by the user.\n"
               "If you find one, extract the corresponding citation (claim) with its citation type using the 'information_extraction'.\n"
               "The citation/claim is small section or at least a sentence next (typically infront) to the citation marker that makes a (questionable) assertion or claim which is underpinned/proven by the referenced work (linked by the given citation marker in IEEE citation format).\n"
               "The citation should extract the whole passage that is needed to understand the statement/essence . The context needs to be exactly the scope to fully get the claim and evaluate if the refrence wittness the claim.\n"
               "Additionally to the citation marker and the claim, you should also extract the type of the reference. There are 4 possible types: 'direct', if the claim is a direct quote from the referenced work (quotation marks required), 'indirect', if the claim is a paraphrase or summary of the referenced work (most common), 'referenced', if the referenced work only provides further background or in depth information, and 'unknown', if the type is not clear."
    ),
    ("user", "{text_chunk}")
])

#####################################################

#historical promts to lean on for a multi step claim extraction


# Usual paper chunks prompts
extract_usual_chunks_first_prompt = ChatPromptTemplate.from_template(
    """""Your role as an AI language model is to assist in organizing and formatting academic text with precision. 
    Analyze the provided text chunk from a scientific paper. Your task is to identify each reference to a 
    bibliography within the text and extract the sentence or sentences that contain the reference along with the 
    assertion supported by the reference. Organize the data as follows:

- Identify each reference including any brackets or formatting from the original citation. 
This should be followed by the sentence or sentences that form the context of the reference and include the 
assertion that is to be supported by the reference.

- If multiple references, like ([23], [24]) support a single assertion, create a separate entry for each reference, 
repeating the context sentence for each one. This means you will have multiple entries with the same context 
sentence but different inline references.

- Separate different reference-contextOfAssertion pairs with three linebreaks.

- Begin your response by stating the chunk_id in the first line.

Note: This task may involve different citation styles. Please adapt accordingly to accurately extract and 
format the references regardless of the citation style used.
The input for processing is as follows: {text_chunk}
"""
)

extract_usual_chunks_second_prompt = ChatPromptTemplate.from_template(
    """""Your role as an AI language model is to assist in formatting academic text with precision. 
    You are tasked with analyzing the provided reference-contextOfAssertion pairs and converting each into a 
    well-structured JSON object. Ensure the JSON syntax is correct and valid. The JSON object should adhere to 
    the following format:

{
  "reference": "A string representing the reference including any brackets or formatting used in the original citation.",
  "raw_sentence": "A string representing the context of the pair",
  "claim": "A paraphrased description of the assertion supported by the reference",
  "chunk_id": "The chunk_id specified at the beginning of the input text chunk"
}

Ensure all fields are enclosed in double quotes, and the overall structure adheres to proper JSON formatting. 
Handle each reference-contextOfAssertion pair individually and maintain accuracy in representing the data.
The input for processing is as follows: {text_chunk} """
)
