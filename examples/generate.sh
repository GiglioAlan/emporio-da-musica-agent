#!/usr/bin/env bash
# Regenerates the example conversations from the scripts, running the real agent through the CLI.
# The store clock is pinned so the transcripts are reproducible (answers may still vary — it's an LLM).
set -euo pipefail
cd "$(dirname "$0")/.."

export STORE_TODAY="${STORE_TODAY:-2026-11-03T10:30}"
export TICKETS_PATH="${TICKETS_PATH:-var/example_tickets.jsonl}"

for script in examples/scripts/*.txt; do
  name="$(basename "$script" .txt)"
  out="examples/$name.md"
  rm -f "$out"
  echo "== $name"
  uv run -q emporio-agent --thread "example-$name-$(date +%s)" --script "$script" --transcript "$out"
done
