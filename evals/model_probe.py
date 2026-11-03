"""Probe candidate free models with the REAL agent (same tools and prompt) before choosing one.

Each model runs alone (no fallback) on a few questions; we record tools called, latency, errors and the answer,
then read the answers before deciding. Cost: ~2 requests per question per model.

    uv run python evals/model_probe.py nvidia/nemotron-3-ultra-550b-a55b:free dots-studio/dots-3-note-preview:free
"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from langchain_core.messages import AIMessage, ToolMessage

from emporio_agent.agent import build_agent

QUESTIONS = [
    # (question, tool expected to be called, substrings the answer must contain — any of them)
    ("Quanto custa o Takamine GD20?", "get_product_details", ["2.199", "2199"]),
    ("Oi! Queria saber do meu pedido 8, meu e-mail é anacarol.ferreira@coldmail.com", "get_order_status", ["BRJL5544332BR"]),
    ("Vocês vendem cordas de guitarra?", None, ["instrumento"]),
]
CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯]")
RESULTS_DIR = Path(__file__).parent / "results"


def run(model: str) -> list[dict]:
    agent = build_agent([model])
    rows = []
    for i, (question, expected_tool, must_contain) in enumerate(QUESTIONS):
        start = time.perf_counter()
        row = {"model": model, "question": question}
        try:
            out = agent.invoke({"messages": [("user", question)]}, {"configurable": {"thread_id": f"probe-{i}"}})
            messages = out["messages"]
            answer = messages[-1].content if isinstance(messages[-1], AIMessage) else ""
            tools = [tc["name"] for m in messages if isinstance(m, AIMessage) for tc in m.tool_calls]
            row.update(
                answer=answer,
                tools=tools,
                tool_ok=(expected_tool in tools) if expected_tool else True,
                content_ok=any(s.lower() in answer.lower() for s in must_contain),
                cjk=bool(CJK.search(answer)),
                tool_errors=sum(1 for m in messages if isinstance(m, ToolMessage) and m.status == "error"),
            )
        except Exception as exc:  # noqa: BLE001 — a probe must survive any provider failure
            row.update(error=f"{type(exc).__name__}: {str(exc)[:300]}")
        row["seconds"] = round(time.perf_counter() - start, 1)
        rows.append(row)
        status = row.get("error") or f"tools={row['tools']} tool_ok={row['tool_ok']} content_ok={row['content_ok']}"
        print(f"[{model}] {row['seconds']:>5}s  {question[:40]!r}  {status}", flush=True)
    return rows


def main(models: list[str]) -> None:
    rows = [row for model in models for row in run(model)]
    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"model_probe_{datetime.now():%Y%m%d_%H%M}.json"
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nsaved {path}")


if __name__ == "__main__":
    main(sys.argv[1:])
