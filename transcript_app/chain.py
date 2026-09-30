"""LangChain chain: sequential LLM calls through a LiteLLM router.

Pipeline (each step waits for the previous result):
1. raw transcript -> prose            (PROSE_PROMPT)
2. prose          -> title            (TITLE_PROMPT)
3. prose          -> Markdown layout  (MARKDOWN_PROMPT)

State is passed as a dict through RunnableLambda steps.
"""

from __future__ import annotations

from typing import TypedDict

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnableSequence
from langchain_litellm import ChatLiteLLM

from .config import Config
from .prompts import MARKDOWN_PROMPT, PROSE_PROMPT, TITLE_PROMPT


class PipelineState(TypedDict, total=False):
    transcript: str
    lang: str
    prose: str
    title: str
    markdown: str


def build_llm(cfg: Config) -> ChatLiteLLM:
    # the litellm client needs a provider prefix; a LiteLLM router is an
    # OpenAI-compatible endpoint: openai/<model name on the router>
    model = cfg.model if "/" in cfg.model else f"openai/{cfg.model}"
    return ChatLiteLLM(
        model=model,
        api_base=cfg.base_url,
        api_key=cfg.api_key,
        temperature=cfg.temperature,
        request_timeout=cfg.timeout,
        # the LiteLLM router works reliably through /v1/chat/completions;
        # the Responses API (/v1/responses) causes endless retries
        use_responses_api=False,
        # httpx asks for gzip by default, which makes the LiteLLM proxy hang on
        # large responses. Request an uncompressed response instead.
        extra_headers={"Accept-Encoding": "identity"},
    )


def _run_streaming(chain, inputs: dict) -> str:
    """Run an LCEL chain in streaming mode and collect the text.

    Streaming is not about progress: the LiteLLM proxy reliably returns
    uncompressed chunks, while a monolithic large response may hang.
    """
    return "".join(part for part in chain.stream(inputs) if part)


def build_pipeline(cfg: Config) -> RunnableSequence:
    llm = build_llm(cfg)

    prose_chain = PROSE_PROMPT | llm | StrOutputParser()
    title_chain = TITLE_PROMPT | llm | StrOutputParser()
    markdown_chain = MARKDOWN_PROMPT | llm | StrOutputParser()

    def step_prose(state: PipelineState) -> PipelineState:
        print(f"      [LLM 1/3] rewriting as prose ({len(state['transcript'].split())} words) ...", flush=True)
        prose = _run_streaming(
            prose_chain, {"transcript": state["transcript"], "lang": state["lang"]}
        ).strip()
        print(f"      [LLM 1/3] done: {len(prose.split())} words", flush=True)
        return {**state, "prose": prose}

    def step_title(state: PipelineState) -> PipelineState:
        print("      [LLM 2/3] document title ...", flush=True)
        title = _run_streaming(title_chain, {"prose": state["prose"]}).strip().strip('"')
        print(f"      [LLM 2/3] done: \"{title}\"", flush=True)
        return {**state, "title": title}

    def step_markdown(state: PipelineState) -> PipelineState:
        print("      [LLM 3/3] Markdown layout ...", flush=True)
        markdown = _run_streaming(markdown_chain, {"prose": state["prose"]}).strip()
        print(f"      [LLM 3/3] done: {len(markdown.split())} words", flush=True)
        return {**state, "markdown": markdown}

    return RunnableLambda(step_prose) | RunnableLambda(step_title) | RunnableLambda(step_markdown)
