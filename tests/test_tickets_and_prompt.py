import json

import pytest

from emporio_agent.prompts import static_prompt
from emporio_agent.store import Store
from emporio_agent.tickets import create_ticket


@pytest.fixture
def tickets_file(tmp_path, monkeypatch):
    path = tmp_path / "tickets.jsonl"
    monkeypatch.setenv("TICKETS_PATH", str(path))
    return path


def test_ticket_is_persisted_with_protocol(tickets_file):
    result = create_ticket("complaint", "Pedido 8 atrasado", "anacarol.ferreira@coldmail.com", 8)
    assert result["protocol"].startswith("EM-")
    saved = json.loads(tickets_file.read_text(encoding="utf-8").strip())
    assert saved["protocol"] == result["protocol"] and saved["order_id"] == 8


def test_ticket_requires_contact_and_valid_kind(tickets_file):
    assert "error" in create_ticket("complaint", "algo", "  ")
    assert "error" in create_ticket("refund_now", "algo", "a@b.com")
    assert not tickets_file.exists()


def test_c1_categories_for_sale_exclude_empty_families():
    categories = Store().categories_for_sale()
    assert categories == ["Guitarras", "Baixos", "Baterias e Percussão", "Teclados e Pianos", "Violões", "Ukuleles"]


def test_prompt_lists_only_categories_for_sale():
    prompt = static_prompt()
    assert "for sale right now:\n  Guitarras, Baixos" in prompt
    assert "{" not in prompt.split("# STORE POLICY MANUAL")[0]  # template fully rendered
