"""Serve the built viewer, the progress feed, and finished private bundles on localhost.

Nothing here leaves the machine. The server binds to a loopback address only,
reads `app/dist` for the viewer, `research-runs/progress.json` for the feed,
`research-runs/<name>/results.json` for a finished run and that run's
`photos/` images, and refuses every other path. The viewer polls the feed only when it is served this way.
"""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import threading
from typing import Sequence
import webbrowser

from .progress import PROGRESS_FILE

DEFAULT_PORT = 43118
RUN_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
LOOPBACK = "127.0.0.1"
PHOTO_FILE = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}\.(jpg|png)$")
IMAGE_TYPES = {"jpg": "image/jpeg", "png": "image/png"}


class ViewerHandler(SimpleHTTPRequestHandler):
    """Static viewer plus private, read-only routes for the feed, results, and photos."""

    def __init__(self, *args, root: Path, **kwargs) -> None:
        self._root = root
        super().__init__(*args, directory=str(root / "app" / "dist"), **kwargs)

    def do_GET(self) -> None:  # noqa: N802 - http.server naming
        path = self.path.split("?", 1)[0]
        if path == f"/{PROGRESS_FILE}":
            self._send_private_json(self._root / "research-runs" / PROGRESS_FILE)
            return
        match = re.fullmatch(r"/runs/([^/]+)/results\.json", path)
        if match:
            name = match.group(1)
            if not RUN_NAME.fullmatch(name) or name in (".", ".."):
                self.send_error(404)
                return
            self._send_private_json(self._root / "research-runs" / name / "results.json")
            return
        match = re.fullmatch(r"/runs/([^/]+)/photos/([^/]+)", path)
        if match:
            name, file = match.group(1), match.group(2)
            if not RUN_NAME.fullmatch(name) or name in (".", "..") or not PHOTO_FILE.fullmatch(file):
                self.send_error(404)
                return
            self._send_private_file(
                self._root / "research-runs" / name / "photos" / file, IMAGE_TYPES[file.rsplit(".", 1)[1]]
            )
            return
        if path.startswith("/runs/") or path.startswith("/research-runs"):
            self.send_error(404)
            return
        super().do_GET()

    def _send_private_json(self, path: Path) -> None:
        self._send_private_file(path, "application/json; charset=utf-8", cache="no-store")

    def _send_private_file(self, path: Path, content_type: str, *, cache: str = "private, max-age=3600") -> None:
        if not path.is_file():
            self.send_error(404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self) -> None:
        # The viewer never needs to be framed or scripted from elsewhere.
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - http.server naming
        # Quiet by default; the progress feed is the user-facing log.
        return


def make_server(root: Path, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((LOOPBACK, port), partial(ViewerHandler, root=root))


def main(argv: Sequence[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Serve the built viewer and the local progress feed on 127.0.0.1"
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--open", action="store_true", help="open the viewer in a browser")
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")

    dist = root / "app" / "dist" / "index.html"
    if not dist.is_file():
        parser.error("app/dist/index.html is missing; run `npm run build` first")

    server = make_server(root, args.port)
    url = f"http://{LOOPBACK}:{args.port}/"
    print(f"Serving the viewer at {url} (loopback only; Ctrl+C to stop)")
    print(f"Progress feed: {url}{PROGRESS_FILE} from research-runs/{PROGRESS_FILE}")
    print("Finished runs: /runs/<name>/results.json and /runs/<name>/photos/* from research-runs/<name>/")
    if args.open:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped")
    finally:
        server.server_close()
    return 0
