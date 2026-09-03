"""Preview, then fetch, one freely licensed photo per place into a private run.

The command reads a validated run, prints exactly what it will ask Wikipedia
and Commons for (place names and rounded coordinates, nothing else), and only
after `--execute` fetches through the caching transport, writes the images
beside a sibling bundle, and rescores so every candidate carries its photo
record. Photos are opt-in and separate from the research command's call cap.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from shutil import copy2
from typing import Sequence

from .cache import CachingTransport, RequestLedger
from .importer import SIDECARS, read_json
from .net import UrllibTransport
from .photos import (
    CALLS_PER_PLACE, DEFAULT_WIDTH, PHOTO_PROVIDER, describe_photo_plan, fetch_photos,
    merge_photo_research,
)
from .progress import PROGRESS_FILE, ProgressLog, result_url
from .reporting import write_bundle
from .scoring import score_research
from .validation import validate_provenance

CACHE_PROVIDER = "wikimedia"
CACHE_TTL = timedelta(days=30)


def main(argv: Sequence[str] | None = None, *, transport=None, clock=None) -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Preview or fetch one freely licensed photo per place for a private run"
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cache", type=Path, default=root / "cache")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help="image width in pixels")
    parser.add_argument(
        "--prefer",
        action="append",
        default=[],
        metavar="CANDIDATE_ID=PAGE_TITLE",
        help="use this Wikipedia page for a place instead of the lookup by its name (repeatable)",
    )
    parser.add_argument("--execute", action="store_true", help="make the previewed calls and write the bundle")
    args = parser.parse_args(argv)
    if not 320 <= args.width <= 2560:
        parser.error("width must be between 320 and 2560 pixels")

    profile = read_json(args.run_dir / "profile.json")
    evidence = read_json(args.run_dir / "evidence.json")
    manifest = read_json(args.run_dir / "provenance.json")
    artifacts = {
        name: (args.run_dir / name).read_bytes()
        for name in ("profile.json", "evidence.json", "results.json")
    }
    validate_provenance(evidence, manifest, artifacts)
    candidates = list(evidence["candidates"])
    output = args.output or args.run_dir.with_name(f"{args.run_dir.name}-photos")
    preferred = _preferred_pages(parser, args.prefer, {candidate["id"] for candidate in candidates})

    for line in describe_photo_plan(candidates, width=args.width, preferred=preferred):
        print(line)
    print(f"Private output: {output} (images under {output / 'photos'})")
    if not args.execute:
        print("Preview only. Re-run with --execute after reviewing the calls above.")
        return 0
    now = clock or (lambda: datetime.now(timezone.utc))
    ledger = RequestLedger(max_network_requests=CALLS_PER_PLACE * len(candidates))
    caching = CachingTransport(
        CACHE_PROVIDER, transport or UrllibTransport(), args.cache, ledger, ttl=CACHE_TTL, clock=now
    )
    progress = ProgressLog(args.run_dir.parent / PROGRESS_FILE)
    progress.start(str(profile["run_id"]), command="photos")
    try:
        research, files, notes = fetch_photos(
            candidates, caching, retrieved_at=now().isoformat(), width=args.width, preferred=preferred
        )
        progress.event(
            "discovery",
            f"{len(research['photos'])} of {len(candidates)} places have a freely licensed photo",
            counts={"photos": len(research["photos"]), "places": len(candidates)},
            provider=PHOTO_PROVIDER,
            cache="hit" if ledger.cache_used else "miss",
        )
        merged = merge_photo_research(evidence, research)
        profile["search"]["providers"]["photos"] = PHOTO_PROVIDER
        results = score_research(profile, merged, now().isoformat())
        write_bundle(
            output, profile, merged, results,
            request_ledger=list(manifest["request_ledger"]) + list(ledger.entries),
        )
        for relative, content in files.items():
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        for name in SIDECARS:
            source = args.run_dir / name
            if source.exists():
                copy2(source, output / name)
        progress.event("write", f"Bundle and {len(files)} images written to {output}")
        progress.done(result_url(output, root))
    except Exception as error:
        progress.fail(f"{type(error).__name__}: {error}")
        raise
    for note in notes:
        print(f"Note: {note}")
    hits = sum(entry["cache"] == "hit" for entry in ledger.entries)
    print(
        f"Wrote photo-enriched bundle to {output}: {len(files)} images, "
        f"{ledger.network_requests} live calls, {hits} cache hits"
    )
    return 0


def _preferred_pages(
    parser: argparse.ArgumentParser, specs: Sequence[str], candidate_ids: set[str]
) -> dict[str, str]:
    """Parse CANDIDATE_ID=PAGE_TITLE overrides; each must name a place in the run."""
    preferred: dict[str, str] = {}
    for spec in specs:
        candidate_id, separator, title = spec.partition("=")
        candidate_id, title = candidate_id.strip(), title.strip()
        if not separator or not candidate_id or not title:
            parser.error("prefer must look like CANDIDATE_ID=Wikipedia page title")
        if candidate_id not in candidate_ids:
            parser.error(f"prefer names a place that is not in the run: {candidate_id}")
        preferred[candidate_id] = title
    return preferred
