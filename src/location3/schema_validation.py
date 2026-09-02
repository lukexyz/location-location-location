"""Authoritative JSON Schema validation for public bundle contracts."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


SCHEMA_DIRECTORY = Path(__file__).resolve().parents[2] / "schemas"


@lru_cache(maxsize=1)
def _schema_store() -> tuple[dict[str, dict[str, Any]], Registry]:
    schemas: dict[str, dict[str, Any]] = {}
    resources = []
    for path in sorted(SCHEMA_DIRECTORY.glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        schema_id = schema.get("$id")
        if not isinstance(schema_id, str) or not schema_id:
            raise ValueError(f"schema {path.name} needs a non-empty $id")
        schemas[path.name] = schema
        resources.append((schema_id, Resource.from_contents(schema)))
    return schemas, Registry().with_resources(resources)


def validate_schema_document(document: Any, schema_name: str) -> None:
    """Raise a concise ValueError when a document violates a repository schema."""
    schemas, registry = _schema_store()
    try:
        schema = schemas[schema_name]
    except KeyError as error:
        raise ValueError(f"unknown repository schema: {schema_name}") from error
    validator = Draft202012Validator(
        schema,
        registry=registry,
        format_checker=FormatChecker(),
    )
    errors = sorted(
        validator.iter_errors(document),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if not errors:
        return
    error = errors[0]
    location = "$" + "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}"
        for part in error.absolute_path
    )
    raise ValueError(
        f"{schema_name} validation failed at {location}: {error.message}"
    )
