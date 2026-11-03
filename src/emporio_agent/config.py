"""Paths, runtime settings (from .env) and the store clock."""

import os
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

RAW_DATA_DIR = ROOT / "data" / "raw"
POLICIES_PATH = ROOT / "data" / "processed" / "policies.md"

ASSISTANT_NAME = os.environ.get("ASSISTANT_NAME", "Clave")

# Free models chosen with evals/model_probe.py (see README). The fallback chain ends on another provider (Groq),
# so an OpenRouter/NVIDIA outage doesn't take the agent down. "groq:" prefix = Groq's OpenAI-compatible API.
PRIMARY_MODEL = os.environ.get("MODEL", "nvidia/nemotron-3.5-super-vl:free")
FALLBACK_MODELS = [
    m.strip()
    for m in os.environ.get(
        "FALLBACK_MODELS", "nvidia/nemotron-3-ultra-550b-a55b:free,groq:openai/gpt-oss-120b"
    ).split(",")
    if m.strip()
]
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

STORE_TZ = ZoneInfo("America/Campo_Grande")

# Policy section 2: Mon-Fri 09-18, Sat 09-13, closed on Sundays and holidays.
OPENING_HOURS = {0: (9, 18), 1: (9, 18), 2: (9, 18), 3: (9, 18), 4: (9, 18), 5: (9, 13)}
WEEKDAYS_PT = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]

# Fixed-date national holidays + Campo Grande (Aug 26) and Mato Grosso do Sul (Oct 11) local ones.
FIXED_HOLIDAYS = {
    (1, 1): "Confraternização Universal",
    (4, 21): "Tiradentes",
    (5, 1): "Dia do Trabalho",
    (8, 26): "Aniversário de Campo Grande",
    (9, 7): "Independência do Brasil",
    (10, 11): "Criação do Estado de Mato Grosso do Sul",
    (10, 12): "Nossa Senhora Aparecida",
    (11, 2): "Finados",
    (11, 15): "Proclamação da República",
    (11, 20): "Dia da Consciência Negra",
    (12, 25): "Natal",
}


def store_now() -> datetime:
    """Current date/time at the store. STORE_TODAY (YYYY-MM-DD or ISO datetime) pins it for demos and evals."""
    pinned = os.environ.get("STORE_TODAY", "").strip()
    if pinned:
        value = datetime.fromisoformat(pinned)
        if len(pinned) == 10:  # date only -> mid-morning
            value = value.replace(hour=10)
        return value.replace(tzinfo=STORE_TZ) if value.tzinfo is None else value.astimezone(STORE_TZ)
    return datetime.now(STORE_TZ)


def _easter(year: int) -> date:
    """Gregorian Easter (anonymous algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def holiday_name(day: date) -> str | None:
    if day == _easter(day.year) - timedelta(days=2):
        return "Sexta-feira Santa"
    return FIXED_HOLIDAYS.get((day.month, day.day))


def store_status(now: datetime) -> str:
    """One line, in Portuguese, that the system prompt uses to answer 'are you open now?'."""
    holiday = holiday_name(now.date())
    hours = OPENING_HOURS.get(now.weekday())
    if holiday:
        state = f"FECHADA hoje (feriado: {holiday})"
    elif hours is None:
        state = "FECHADA hoje (domingo)"
    elif hours[0] <= now.hour < hours[1]:
        state = f"ABERTA agora (hoje fecha às {hours[1]:02d}:00)"
    elif now.hour < hours[0]:
        state = f"FECHADA agora (hoje abre às {hours[0]:02d}:00)"
    else:
        state = "FECHADA agora (expediente de hoje encerrado)"
    return f"{WEEKDAYS_PT[now.weekday()]}, {now:%d/%m/%Y %H:%M} (horário de Campo Grande) — loja {state}"
