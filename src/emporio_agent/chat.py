"""One conversation turn, shared by the CLI, the Streamlit UI and the evals — so what the evals measure is
exactly what the interfaces run."""

import sqlite3
from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from .agent import build_agent
from .config import ROOT

CHECKPOINTS_PATH = ROOT / "var" / "checkpoints.sqlite"


@dataclass
class ToolCall:
    name: str
    args: dict
    failed: bool = False


@dataclass
class Turn:
    answer: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str | None = None  # model that wrote the final answer (shows when a fallback kicked in)


def persistent_agent(models: list[str] | None = None):
    """Agent whose conversations survive restarts (SQLite checkpointer, one thread per conversation)."""
    CHECKPOINTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: Streamlit runs each rerun in a different thread.
    conn = sqlite3.connect(CHECKPOINTS_PATH, check_same_thread=False)
    return build_agent(models, checkpointer=SqliteSaver(conn))


def ask(agent, thread_id: str, text: str) -> Turn:
    config = {"configurable": {"thread_id": thread_id}}
    before = len(agent.get_state(config).values.get("messages", []))
    messages = agent.invoke({"messages": [("user", text)]}, config)["messages"][before:]

    failed_ids = {m.tool_call_id for m in messages if isinstance(m, ToolMessage) and m.status == "error"}
    calls = [
        ToolCall(tc["name"], tc["args"], tc["id"] in failed_ids)
        for m in messages
        if isinstance(m, AIMessage)
        for tc in m.tool_calls
    ]
    final = messages[-1]
    if isinstance(final, AIMessage) and final.content:
        answer = final.content if isinstance(final.content, str) else str(final.content)
    else:  # e.g. the per-turn call limit ended the run before a final answer
        answer = "Desculpe, não consegui concluir agora. Pode tentar de novo ou falar com a equipe pelo (67) 3341-4444?"
    model = final.response_metadata.get("model_name") if isinstance(final, AIMessage) else None
    return Turn(answer.strip(), calls, model)
