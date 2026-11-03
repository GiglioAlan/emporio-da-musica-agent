"""Support tickets: complaints and hand-offs to the human team (policy 7.3: "registrar a reclamação e
encaminhar para o responsável"). Stored as JSON lines — enough for a prototype and easy to inspect;
in production this would call the store's helpdesk/CRM API instead.
"""

import json
import os
import secrets
from pathlib import Path

from .config import ROOT, store_now

TICKET_KINDS = ("complaint", "exchange_or_return", "warranty", "human_handoff", "other")


def tickets_path() -> Path:
    return Path(os.environ.get("TICKETS_PATH", ROOT / "var" / "tickets.jsonl"))


def create_ticket(kind: str, summary: str, customer_contact: str, order_id: int | None = None) -> dict:
    if kind not in TICKET_KINDS:
        return {"error": f"Tipo inválido. Use um destes: {list(TICKET_KINDS)}"}
    if not summary.strip() or not customer_contact.strip():
        return {"error": "Preciso de um resumo do caso e de um e-mail ou telefone para a equipe retornar."}

    now = store_now()
    ticket = {
        "protocol": f"EM-{now:%Y%m%d}-{secrets.token_hex(2).upper()}",
        "created_at": now.isoformat(timespec="seconds"),
        "kind": kind,
        "summary": summary.strip(),
        "customer_contact": customer_contact.strip(),
        "order_id": order_id,
    }
    path = tickets_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ticket, ensure_ascii=False) + "\n")
    return {
        "protocol": ticket["protocol"],
        "next_step": "A equipe responde em até 24 horas úteis pelo contato informado.",
    }
