"""Write private research bundles and a tiny standalone proof-of-contract report."""

from __future__ import annotations

from hashlib import sha256
from html import escape
import json
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .schema_validation import validate_schema_document
from .validation import validate_provenance


def write_bundle(
    output: Path,
    profile: dict[str, Any],
    evidence: dict[str, Any],
    results: dict[str, Any],
    *,
    request_ledger: list[dict[str, object]] | None = None,
    warnings: Sequence[str] = (),
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    profile_bytes = _json_bytes(profile)
    evidence_bytes = _json_bytes(evidence)
    result_bytes = _json_bytes(results)
    manifest = {
        "schema_version": "1",
        "run_id": profile["run_id"],
        "generated_at": results["generated_at"],
        "scoring_version": results["scoring_version"],
        "tool_versions": {"location3": __version__},
        "geographic_coverage": profile["search"]["route_boundary"],
        "request_ledger": request_ledger or [],
        "cache_used": any(
            entry.get("cache") == "hit" for entry in (request_ledger or [])
        ),
        "sources": _evidence_values(evidence, "source_url", "url"),
        "licences": _evidence_values(evidence, "licence", "licence"),
        "warnings": sorted(
            {warning for candidate in results["candidates"] for warning in candidate["warnings"]}
            | set(warnings)
        ),
        "checksums": {
            "profile.json": _checksum(profile_bytes),
            "evidence.json": _checksum(evidence_bytes),
            "results.json": _checksum(result_bytes),
        },
    }
    artifacts = {
        "profile.json": profile_bytes,
        "evidence.json": evidence_bytes,
        "results.json": result_bytes,
    }
    validate_schema_document(profile, "research-profile.schema.json")
    validate_schema_document(evidence, "evidence.schema.json")
    validate_schema_document(results, "research-result.schema.json")
    validate_schema_document(manifest, "research-manifest.schema.json")
    validate_provenance(evidence, manifest, artifacts)
    (output / "profile.json").write_bytes(profile_bytes)
    (output / "evidence.json").write_bytes(evidence_bytes)
    (output / "results.json").write_bytes(result_bytes)
    (output / "provenance.json").write_bytes(_json_bytes(manifest))
    (output / "report.html").write_text(_render_html(results), encoding="utf-8")
    return manifest


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _checksum(content: bytes) -> str:
    return f"sha256:{sha256(content).hexdigest()}"


def _evidence_values(
    evidence: dict[str, Any], observation_key: str, rail_source_key: str
) -> list[str]:
    values = {item[observation_key] for item in evidence["observations"]}
    for journey in evidence.get("rail_journeys", []):
        values.update(source[rail_source_key] for source in journey["sources"])
    housing_research = evidence.get("housing_research")
    if housing_research:
        values.update(
            source[rail_source_key]
            for market in housing_research["markets"]
            for source in market["sources"]
        )
    street_research = evidence.get("street_care_research")
    if street_research:
        for place in street_research["places"]:
            values.add(place["fly_tipping"]["source"][rail_source_key])
            if place["local_reports"]:
                values.add(place["local_reports"]["source"][rail_source_key])
    return sorted(values)


def _render_html(results: dict[str, Any]) -> str:
    cards = []
    for candidate in results["candidates"]:
        categories = []
        for category in candidate["categories"]:
            rows = "".join(
                "<tr>"
                f"<td>{escape(metric['metric'].replace('_', ' ').title())}</td>"
                f"<td>{metric['raw_value']} {escape(metric['unit'])}</td>"
                f"<td>{metric['normalized_score']:.1f}</td>"
                f"<td>{metric['weight']:g}</td>"
                f'<td><a href="{escape(metric["source_url"])}">'
                f"{escape(metric['source'])}</a> ({escape(metric['source_date'])})</td>"
                "</tr>"
                for metric in category["metrics"]
            )
            categories.append(
                f"<details><summary>{escape(category['category'].title())}: "
                f"{category['score']:.1f}</summary><table><thead><tr>"
                "<th>Metric</th><th>Raw</th><th>Score</th><th>Weight</th><th>Evidence</th>"
                f"</tr></thead><tbody>{rows}</tbody></table></details>"
            )
        informational = "".join(
            f"<li>{escape(metric['metric'].replace('_', ' ').title())}: "
            f"{metric['raw_value']} {escape(metric['unit'])} (informational)</li>"
            for metric in candidate["informational_metrics"]
        )
        status = "PASS" if candidate["hard_constraints"]["passed"] else "OUTSIDE LIMIT"
        warnings = "".join(f"<li>{escape(item)}</li>" for item in candidate["warnings"])
        warning_details = (
            f"<details><summary>Warnings</summary><ul>{warnings}</ul></details>"
            if warnings else ""
        )
        cards.append(
            f"""
            <article>
              <div class="rank">#{candidate['rank']}</div>
              <h2>{escape(candidate['name'])}</h2>
              <div class="score">{candidate['overall_score']:.1f}</div>
              <p>{status} · confidence {candidate['confidence']:.0f}%</p>
              {''.join(categories)}
              {f'<ul>{informational}</ul>' if informational else ''}
              {warning_details}
            </article>"""
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LOCATION³ — {escape(results['run_id'])}</title>
  <style>
    :root {{ color-scheme: dark; font-family: ui-monospace, monospace; background: #0b1010; color: #d9ffdf; }}
    body {{ max-width: 80rem; margin: 0 auto; padding: 3rem 1rem; }}
    header {{ border-bottom: 1px solid #48604d; margin-bottom: 2rem; }}
    main {{ display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr)); }}
    article {{ position: relative; padding: 1rem; border: 1px solid #48604d; background: #111918; overflow: auto; }}
    h1, h2 {{ letter-spacing: .08em; }} .rank {{ color: #8aa88f; }}
    .score {{ font-size: 3rem; color: #b6ff73; }} li {{ margin: .4rem 0; }}
    details {{ margin: .75rem 0; }} table {{ width: 100%; border-collapse: collapse; font-size: .75rem; }}
    th, td {{ padding: .35rem; text-align: left; border-bottom: 1px solid #293b2d; }}
  </style>
</head>
<body>
  <header><h1>LOCATION³</h1><p>{escape(results['run_id'])} · fixture research bundle</p></header>
  <main>{''.join(cards)}</main>
</body>
</html>
"""
