"""Agent assembly: a LangChain v1 tool-calling (ReAct) agent running on LangGraph.

Why this shape: the task is "answer, looking things up when needed". One loop where the model decides which
tool to call covers it; a custom router graph would add moving parts without adding capability.
Reliability concerns (fallback, retries, runaway loops) are handled by LangChain's built-in middleware.
"""

import logging
import os

import openai
from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ModelFallbackMiddleware,
    ModelRequest,
    ModelRetryMiddleware,
    dynamic_prompt,
)
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from .config import FALLBACK_MODELS, GROQ_BASE_URL, PRIMARY_MODEL, store_now, store_status
from .prompts import system_prompt
from .tools import TOOLS

logger = logging.getLogger("emporio_agent")

TIMEOUT_S = 60

# Retry only transient failures. Permanent ones (404 model gone, 400 bad request) go straight to the fallback
# model instead of burning requests on the free-tier daily cap.
TRANSIENT_ERRORS = (
    openai.RateLimitError,
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.InternalServerError,
)


def chat_model(model: str) -> ChatOpenAI:
    """'groq:<model>' -> Groq; anything else -> OpenRouter (OPENAI_API_BASE / OPENAI_API_KEY).
    Both speak the OpenAI API, so one client class covers them.
    max_retries=0: a single retry layer (the middleware). Stacked retry layers multiply requests."""
    common = dict(temperature=0.2, timeout=TIMEOUT_S)
    if model.startswith("groq:"):
        # Exception to the single-retry-layer rule: Groq's free tier caps TOKENS per minute (8k), and one question
        # here needs ~8-9k. Its 429s carry a retry-after header that the OpenAI client honors (the middleware's
        # fixed backoff doesn't), so the client waits exactly as long as the server asks.
        return ChatOpenAI(
            model=model.removeprefix("groq:"),
            base_url=GROQ_BASE_URL,
            api_key=os.environ["GROQ_API_KEY"],
            max_retries=3,
            **common,
        )
    return ChatOpenAI(model=model, max_retries=0, **common)


@dynamic_prompt
def store_prompt(request: ModelRequest) -> str:
    """Rebuilt on every model call so the date/time and open/closed status are always current."""
    return system_prompt(store_status(store_now()))


def build_agent(models: list[str] | None = None, checkpointer=None):
    """models: primary first, then fallbacks. Defaults to MODEL / FALLBACK_MODELS from the environment."""
    models = models or [PRIMARY_MODEL, *FALLBACK_MODELS]
    if not os.environ.get("GROQ_API_KEY"):
        # The Groq fallback is optional: without its key the agent still runs on OpenRouter alone.
        skipped = [m for m in models if m.startswith("groq:")]
        models = [m for m in models if not m.startswith("groq:")]
        if skipped:
            logger.warning("GROQ_API_KEY not set; skipping fallback models %s", skipped)
    if not models:
        raise ValueError("No usable model configured (set MODEL in .env).")
    middleware = [store_prompt]
    if len(models) > 1:
        middleware.append(ModelFallbackMiddleware(*[chat_model(m) for m in models[1:]]))
    middleware += [
        ModelRetryMiddleware(max_retries=2, retry_on=TRANSIENT_ERRORS, on_failure="error"),
        # A confused model looping on tools would drain the request budget; 8 calls per user message is plenty.
        ModelCallLimitMiddleware(run_limit=8, exit_behavior="end"),
    ]
    return create_agent(
        model=chat_model(models[0]),
        tools=TOOLS,
        middleware=middleware,
        checkpointer=checkpointer if checkpointer is not None else InMemorySaver(),
    )
