"""Bounded adapter for ORR passenger rail performance tables.

The Office of Rail and Road publishes operator-level punctuality (Table 3138) and
cancellations (Table 3124) as HTML tables. This adapter fetches each table once,
parses the rows for the operators the person asked about, and records the latest
period with citations. Nothing about the run leaves the machine: the request is
the public table URL and nothing else.
"""

from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser
import re
from typing import Any, Iterable, Sequence

from .net import HttpTransport, UrllibTransport


ORR_BASE = "https://dataportal.orr.gov.uk"
ORR_LICENCE = "OGL-3.0"
ORR_SOURCE = "Office of Rail and Road passenger rail performance statistics"
TABLES: dict[str, dict[str, str]] = {
    "punctuality": {
        "id": "3138",
        "path": (
            "/statistics/performance/passenger-rail-performance/"
            "table-3138-train-punctuality-at-recorded-station-stops-by-operator-periodic/"
        ),
        "title": "Table 3138: train punctuality at recorded station stops by operator (periodic)",
        "period": "Time Period",
        "operator": "Operator",
        "periodic": "Time to 3",
        "annual": "Time to 3 maa",
    },
    "cancellations": {
        "id": "3124",
        "path": (
            "/statistics/performance/passenger-rail-performance/"
            "table-3124-trains-planned-and-cancellations-by-operator-periodic/"
        ),
        "title": "Table 3124: trains planned and cancellations by operator (periodic)",
        "period": "time period",
        "operator": "national or operator",
        "periodic": "periodic cancellations percentage",
        "annual": "moving annual average cancellations percentage",
    },
}
PERIOD = re.compile(r"^[A-Za-z]{3} (\d{4}) to [A-Za-z]{3} \d{4} \(Period (\d{2})\)$")
MAX_OPERATORS = 6
MAX_PAGE_BYTES = 16 * 1024 * 1024


class _ReportTableParser(HTMLParser):
    """Collect the rows of the page's `#reportTable` element only."""

    def __init__(self) -> None:
        super().__init__()
        self.headers: list[str] = []
        self.rows: list[list[str]] = []
        self._in_table = False
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table" and dict(attrs).get("id") == "reportTable":
            self._in_table = True
        if not self._in_table:
            return
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if not self._in_table:
            return
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                if self.headers:
                    self.rows.append(self._row)
                else:
                    self.headers = self._row
            self._row = None
        elif tag == "table":
            self._in_table = False

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


def parse_report_table(html: str) -> tuple[list[str], list[list[str]]]:
    parser = _ReportTableParser()
    parser.feed(html)
    if not parser.headers or not parser.rows:
        raise ValueError("ORR page did not contain a report table with rows")
    return parser.headers, parser.rows


def period_key(label: str) -> tuple[int, int]:
    match = PERIOD.fullmatch(label.strip())
    if not match:
        raise ValueError(f"unrecognised ORR period label: {label!r}")
    return int(match.group(1)), int(match.group(2))


def latest_rows(
    headers: list[str], rows: list[list[str]], table: dict[str, str]
) -> dict[str, dict[str, str]]:
    """Return the most recent row per operator, keyed by casefolded operator name."""
    try:
        period_index = headers.index(table["period"])
        headers.index(table["operator"])
    except ValueError as error:
        raise ValueError(
            f"ORR {table['title']} columns changed; expected {table['period']!r} "
            f"and {table['operator']!r}"
        ) from error
    latest: dict[str, tuple[tuple[int, int], dict[str, str]]] = {}
    for row in rows:
        if len(row) != len(headers):
            continue
        key = period_key(row[period_index])
        record = dict(zip(headers, row))
        operator = record[table["operator"]].casefold()
        if operator not in latest or key > latest[operator][0]:
            latest[operator] = (key, record)
    return {operator: record for operator, (_, record) in latest.items()}


class OrrPerformanceAdapter:
    def __init__(
        self,
        *,
        transport: HttpTransport | None = None,
        base_url: str = ORR_BASE,
        timeout: float = 60.0,
    ) -> None:
        self._transport = transport or UrllibTransport()
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def table_urls(self) -> dict[str, str]:
        return {name: f"{self._base_url}{table['path']}" for name, table in TABLES.items()}

    def fetch(
        self, operators: Sequence[str], *, retrieved_at: str | None = None
    ) -> dict[str, Any]:
        wanted = _clean_operators(operators)
        retrieved_at = retrieved_at or datetime.now(timezone.utc).isoformat()
        tables: dict[str, dict[str, dict[str, str]]] = {}
        stamped_at: str | None = None
        for name, table in TABLES.items():
            response = self._transport.request(
                "GET",
                f"{self._base_url}{table['path']}",
                headers={"Accept": "text/html", "User-Agent": "location3/0.1"},
                body=b"",
                timeout=self._timeout,
            )
            if not 200 <= response.status < 300:
                raise RuntimeError(f"ORR returned HTTP {response.status} for {table['title']}")
            if len(response.body) > MAX_PAGE_BYTES:
                raise ValueError(f"ORR {table['title']} page is larger than expected")
            stamped_at = stamped_at or response.headers.get("X-Location3-Retrieved-At")
            headers, rows = parse_report_table(response.body.decode("utf-8", "replace"))
            tables[name] = latest_rows(headers, rows, table)
        retrieved_at = stamped_at or retrieved_at

        available = sorted(
            {record[TABLES["punctuality"]["operator"]] for record in tables["punctuality"].values()}
        )
        results: list[dict[str, Any]] = []
        for operator in wanted:
            key = operator.casefold()
            punctuality = tables["punctuality"].get(key)
            cancellations = tables["cancellations"].get(key)
            if punctuality is None or cancellations is None:
                raise ValueError(
                    f"ORR does not list an operator named {operator!r}; available: "
                    + ", ".join(available)
                )
            period = punctuality[TABLES["punctuality"]["period"]]
            if cancellations[TABLES["cancellations"]["period"]] != period:
                raise ValueError(
                    f"ORR punctuality and cancellation periods differ for {operator!r}"
                )
            results.append({
                "operator": punctuality[TABLES["punctuality"]["operator"]],
                "period": period,
                "punctuality_time_to_3_percent": _percent(
                    punctuality[TABLES["punctuality"]["periodic"]]
                ),
                "punctuality_time_to_3_annual_percent": _percent(
                    punctuality[TABLES["punctuality"]["annual"]]
                ),
                "cancellations_percent": _percent(
                    cancellations[TABLES["cancellations"]["periodic"]]
                ),
                "cancellations_annual_percent": _percent(
                    cancellations[TABLES["cancellations"]["annual"]]
                ),
            })
        return {
            "schema_version": "1",
            "provider": "orr",
            "retrieved_at": retrieved_at,
            "source_date": retrieved_at[:10],
            "licence": ORR_LICENCE,
            "sources": [
                {
                    "kind": name,
                    "label": f"ORR {table['title']}",
                    "url": f"{self._base_url}{table['path']}",
                }
                for name, table in TABLES.items()
            ],
            "basis": "measured",
            "operators": results,
        }


def _clean_operators(operators: Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    for operator in operators:
        name = " ".join(str(operator).split())
        if not name or len(name) > 80:
            raise ValueError("operator names must be 1-80 characters")
        if name.casefold() not in {item.casefold() for item in cleaned}:
            cleaned.append(name)
    if not cleaned:
        raise ValueError("at least one operator is required")
    if len(cleaned) > MAX_OPERATORS:
        raise ValueError(f"at most {MAX_OPERATORS} operators per fetch")
    return cleaned


def _percent(value: str) -> float:
    try:
        number = float(value)
    except ValueError as error:
        raise ValueError(f"ORR percentage is not numeric: {value!r}") from error
    if not 0 <= number <= 100:
        raise ValueError(f"ORR percentage is out of range: {value!r}")
    return number


def validate_performance(performance: dict[str, Any]) -> None:
    """Runtime check for a performance file before it is trusted by an importer."""
    if performance.get("schema_version") != "1" or performance.get("provider") != "orr":
        raise ValueError("unsupported ORR performance file")
    if performance.get("basis") != "measured":
        raise ValueError("ORR performance must be measured evidence")
    operators = performance.get("operators")
    if not isinstance(operators, list) or not operators:
        raise ValueError("ORR performance must list at least one operator")
    sources = {source.get("kind"): source for source in performance.get("sources", [])}
    if set(sources) != set(TABLES):
        raise ValueError("ORR performance must cite both tables")
    for record in operators:
        period_key(record["period"])
        for field in (
            "punctuality_time_to_3_percent", "punctuality_time_to_3_annual_percent",
            "cancellations_percent", "cancellations_annual_percent",
        ):
            value = record.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"ORR {field} must be numeric")
            if not 0 <= value <= 100:
                raise ValueError(f"ORR {field} is out of range")


def performance_for(performance: dict[str, Any], operator: str) -> dict[str, Any]:
    for record in performance["operators"]:
        if record["operator"].casefold() == operator.casefold():
            return record
    raise ValueError(f"ORR performance file has no entry for operator {operator!r}")
