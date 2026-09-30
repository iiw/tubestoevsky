"""Chain prompts. Every LLM step of the application is defined here."""

from langchain_core.prompts import ChatPromptTemplate

# Step 1: raw transcript -> literary prose with paragraphs.
PROSE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "user",
            """Below is an automatic transcript of spoken speech (video subtitles, language: {lang}). \
Rewrite it as connected literary prose:
- fix and correct punctuation, split the text into meaningful paragraphs;
- remove artifacts of spoken speech: repetitions, filler words, broken phrases;
- fix obvious speech-recognition errors;
- do NOT change the content: add no facts, invent nothing, cut no meaning, \
keep every mentioned detail, number, and name;
- preserve the author's conversational, emotional style;
- output only the finished prose, no headings or explanations.

Transcript:
{transcript}""",
        )
    ]
)

# Step 2: prose -> short document title.
TITLE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "user",
            """Based on the text below, come up with a short document title (up to 60 characters, \
in the language of the text) that accurately reflects its topic. Output only the title itself, \
without quotes or a trailing period.

Text:
{prose}""",
        )
    ]
)

# Step 3: prose -> Markdown layout with subheadings (no rewording).
MARKDOWN_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "user",
            """Format the text below as Markdown for comfortable reading:
- add "##" subheadings for the meaningful parts (3-6 subheadings, short, in the language of the text);
- do NOT change the wording, shorten, or extend the text - structure and paragraph breaks only;
- do not use a level-1 "#" heading (it is added separately);
- output only the finished Markdown.

Text:
{prose}""",
        )
    ]
)
