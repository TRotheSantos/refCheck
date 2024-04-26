compare_tilli = ("This is the citation:\n{claim}\n\n"
"These are the possible references:\n{references}\n\n"
"I want to check if a citation made in a publication is actually referring to it s reference. \
Is the reference accurate? \
If yes, return the part showing that the citation is really referencing. If no, return in which way they do not have the same content.\n\n\
\
Your response should have the following structure:\n\
Approximate Percentage of Relatedness: __%\n\
(return an approximate percentage number on how related the citation and reference are, only based on what I gave you) \
\
... (explanation) \
\
I need to later convert your response into a json file so its important that you return it exactly this way. \
")

score_claim_prompt = ("This is the citation:\n\"\"\"{claim}\"\"\"\n\n"
"These are the relevant chunks of the reference:\n{chunks}\n\n"
"I want to check if a citation made in a publication is accurate.\n"
"The citation is accurate if the reference either way underpinns the claim, in the case the citation makes a claim or if the citation only mentions something if the reference is highly related to the citation and referred by the citation.\n"
"Is the citation accurate?\n"
"If yes, return the part showing that the citation is really referencing. If no, return in which way they do not have the same content or the references do not validate the citation.\n\n"
"Return a well-structured JSON object with the following structure:\n"
"{{\n"
"\"score\": __, The approximate percentage number (0-100)of relatedness between the citation and the reference / percentage that the citation is accurately referencing.\n"
"\"explanation\": The explanation of the score, especially whats missing for 100%.\n"
"\"explanation-short\": The explanation wrapped up as one bullet point aka up to about 3-8 words.\n"
"\"proof\": The identical passage from the relevant chunks that validates the citations claim / The section that is most likely referenced by the citation. Not the citation itself!\n"
"\"chunk_id\": The id (integer) of the chunk that validates the claim or that is referenced by the citation.\n"
"}}"
)
