"""Serve the built viewer and the progress feed on localhost without installing the package."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from location3.serve_cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
