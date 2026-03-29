"""Shared logging utility for extractor modules."""
from __future__ import annotations

import datetime
from pathlib import Path

# Resolve log directory relative to the project root (three levels up from this file).
# agent/utils/logger.py -> agent/utils -> agent -> project root
_LOG_DIR: Path = Path(__file__).resolve().parent.parent.parent / "logs"
_LOG_FILE: Path = _LOG_DIR / "extractor_failures.log"


def log_failure(name: str, model: str, prompt_messages, output: str) -> None:
    """Append a failure entry to the extractor failures log."""
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        with _LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(f"\n---\n{datetime.datetime.utcnow().isoformat()}Z | {name} | model={model}\n")
            fh.write("MESSAGES:\n")
            fh.write(str(prompt_messages))
            fh.write("\nOUTPUT:\n")
            fh.write(output)
            fh.write("\n---\n")
    except Exception:
        pass
