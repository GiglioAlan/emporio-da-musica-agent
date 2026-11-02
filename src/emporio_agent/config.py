"""Paths and runtime settings, read once from the environment (.env)."""

import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

RAW_DATA_DIR = ROOT / "data" / "raw"
POLICIES_PATH = ROOT / "data" / "processed" / "policies.md"

STORE_TZ = ZoneInfo("America/Campo_Grande")


def store_now() -> datetime:
    """Current date/time at the store. STORE_TODAY (YYYY-MM-DD or ISO datetime) pins it for demos and evals."""
    pinned = os.environ.get("STORE_TODAY", "").strip()
    if pinned:
        value = datetime.fromisoformat(pinned)
        if len(pinned) == 10:  # date only -> mid-morning, store open on weekdays
            value = value.replace(hour=10)
        return value.replace(tzinfo=STORE_TZ) if value.tzinfo is None else value.astimezone(STORE_TZ)
    return datetime.now(STORE_TZ)
