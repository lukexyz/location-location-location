"""A local progress feed: one JSON document the viewer polls while a run works.

The feed is honest by construction. It only ever records what a command has
actually done (a stage name, a message, real counts, which provider answered,
whether the cache did), and it lives beside the private runs so it is never
committed or published. A `ProgressLog` with no path is a silent no-op, which
is what library callers and tests get unless they ask for a feed.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping

PROGRESS_FILE = "progress.json"
STAGES = ("boundary", "discovery", "measure", "score", "write", "import")
LEVELS = ("info", "warning", "error")
Clock = Callable[[], datetime]


def default_progress_path(root: Path) -> Path:
    return root / "research-runs" / PROGRESS_FILE


def result_url(output: Path, root: Path) -> str | None:
    """The serve command's URL for a finished bundle, or None if it is not under research-runs."""
    try:
        relative = output.resolve().relative_to((root / "research-runs").resolve())
    except ValueError:
        return None
    if len(relative.parts) != 1:
        return None
    return f"runs/{relative.parts[0]}/results.json"


class ProgressLog:
    """Append stage events to a small JSON document, atomically, or do nothing."""

    def __init__(self, path: Path | None, *, clock: Clock | None = None) -> None:
        self._path = path
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.document: dict[str, Any] | None = None

    @property
    def enabled(self) -> bool:
        return self._path is not None

    def start(self, run_id: str, *, command: str) -> None:
        now = self._now()
        self.document = {
            "schema_version": "1",
            "run_id": run_id,
            "command": command,
            "status": "running",
            "started_at": now,
            "updated_at": now,
            "events": [],
            "result_url": None,
        }
        self._write()

    def event(
        self,
        stage: str,
        message: str,
        *,
        counts: Mapping[str, int] | None = None,
        provider: str | None = None,
        cache: str | None = None,
        level: str = "info",
    ) -> None:
        if stage not in STAGES:
            raise ValueError(f"unknown progress stage: {stage}")
        if level not in LEVELS:
            raise ValueError(f"unknown progress level: {level}")
        if cache is not None and cache not in ("hit", "miss"):
            raise ValueError("cache must be hit or miss")
        if self.document is None:
            return
        entry: dict[str, Any] = {
            "at": self._now(), "stage": stage, "message": message, "level": level,
        }
        if counts:
            entry["counts"] = {key: int(value) for key, value in counts.items()}
        if provider:
            entry["provider"] = provider
        if cache:
            entry["cache"] = cache
        self.document["events"].append(entry)
        self._write()

    def done(self, result: str | None) -> None:
        if self.document is None:
            return
        self.document["status"] = "done"
        self.document["result_url"] = result
        self._write()

    def fail(self, message: str) -> None:
        if self.document is None:
            return
        self.document["status"] = "failed"
        self.document["error"] = message
        self._write()

    def _now(self) -> str:
        return self._clock().isoformat()

    def _write(self) -> None:
        if self._path is None or self.document is None:
            return
        self.document["updated_at"] = self._now()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(self.document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(temporary, self._path)
