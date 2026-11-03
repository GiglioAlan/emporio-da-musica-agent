"""Terminal chat with the store assistant.

    uv run emporio-agent                       # new conversation
    uv run emporio-agent --thread ana          # resume (or start) the conversation "ana"
    uv run emporio-agent --script file.txt     # play customer messages from a file (one per line)

Every conversation is saved as Markdown (default: var/transcripts/<thread>.md), including the tools the
agent called — the example conversations in examples/ were produced this way.
"""

import argparse
import logging
from datetime import datetime
from pathlib import Path

from .chat import Turn, ask, persistent_agent
from .config import ASSISTANT_NAME, ROOT, store_now, store_status

DIM, BOLD, RESET = "\033[2m", "\033[1m", "\033[0m"
EXIT_WORDS = {"sair", "exit", "quit", "/sair"}


def format_tools(turn: Turn) -> str:
    def fmt(call) -> str:
        args = ", ".join(f"{k}={v!r}" for k, v in call.args.items())
        return f"{call.name}({args})" + (" [erro]" if call.failed else "")

    return "; ".join(fmt(c) for c in turn.tool_calls)


class Transcript:
    def __init__(self, path: Path, thread_id: str):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(
                f"# Conversa `{thread_id}`\n\n_Relógio da loja: {store_status(store_now())}_\n\n", encoding="utf-8"
            )

    def add(self, user_text: str, turn: Turn) -> None:
        lines = [f"**Cliente:** {user_text}\n"]
        if turn.tool_calls:
            lines.append(f"> 🔧 `{format_tools(turn)}`\n")
        lines.append(f"**{ASSISTANT_NAME}:** {turn.answer}\n")
        if turn.model:
            lines.append(f"<sub>modelo: {turn.model}</sub>\n")
        with self.path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=f"Chat with {ASSISTANT_NAME}, Empório da Música's assistant.")
    parser.add_argument("--thread", default=f"cli-{datetime.now():%Y%m%d-%H%M%S}", help="conversation id")
    parser.add_argument("--script", type=Path, help="file with one customer message per line (non-interactive)")
    parser.add_argument("--transcript", type=Path, help="where to save the Markdown transcript")
    parser.add_argument("--hide-tools", action="store_true", help="don't print tool calls")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    agent = persistent_agent()
    transcript = Transcript(args.transcript or ROOT / "var" / "transcripts" / f"{args.thread}.md", args.thread)

    if args.script:
        messages = [l.strip() for l in args.script.read_text(encoding="utf-8").splitlines() if l.strip()]
        messages = [m for m in messages if not m.startswith("#")]  # comments in scripts
    else:
        messages = None
        print(f"{BOLD}Empório da Música{RESET} — conversa '{args.thread}'. Digite 'sair' para encerrar.\n")

    def turns():
        if messages is not None:
            for m in messages:
                print(f"{BOLD}Você:{RESET} {m}")
                yield m
            return
        while True:
            try:
                text = input(f"{BOLD}Você:{RESET} ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if text.lower() in EXIT_WORDS:
                return
            if text:
                yield text

    for text in turns():
        try:
            turn = ask(agent, args.thread, text)
        except Exception as exc:  # noqa: BLE001 — every model in the chain failed; keep the chat alive
            logging.getLogger("emporio_agent").error("turn failed: %s: %s", type(exc).__name__, exc)
            print(f"{BOLD}{ASSISTANT_NAME}:{RESET} Tive um problema técnico agora. Pode tentar de novo em instantes?\n")
            continue
        if turn.tool_calls and not args.hide_tools:
            print(f"{DIM}  🔧 {format_tools(turn)}{RESET}")
        print(f"{BOLD}{ASSISTANT_NAME}:{RESET} {turn.answer}\n")
        transcript.add(text, turn)

    print(f"{DIM}Conversa salva em {transcript.path}{RESET}")


if __name__ == "__main__":
    main()
