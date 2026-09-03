"""The local progress feed and the loopback serve command."""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from location3.progress import PROGRESS_FILE, ProgressLog, result_url
from location3.research_cli import execute_research
from location3.serve_cli import make_server
from test_research_pipeline import ProviderTransport


class ProgressLogTests(unittest.TestCase):
    def test_without_a_path_the_log_is_a_silent_no_op(self):
        log = ProgressLog(None)
        log.start("quiet", command="research")
        log.event("boundary", "nothing written")
        log.done(None)
        self.assertFalse(log.enabled)

    def test_events_accumulate_atomically_and_status_follows_the_run(self):
        now = [datetime(2026, 9, 3, 8, tzinfo=timezone.utc)]

        def clock():
            now[0] += timedelta(seconds=1)
            return now[0]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "feed" / PROGRESS_FILE
            log = ProgressLog(path, clock=clock)
            log.start("my-search", command="research")
            log.event(
                "discovery", "Overpass returned 3 places",
                counts={"candidates": 3, "observations": 12.0}, provider="overpass", cache="miss",
            )
            document = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(document["status"], "running")
            self.assertEqual(document["run_id"], "my-search")
            self.assertEqual(document["events"][0]["counts"], {"candidates": 3, "observations": 12})
            self.assertEqual(document["events"][0]["cache"], "miss")
            self.assertGreater(document["updated_at"], document["started_at"])
            self.assertFalse(path.with_suffix(".json.tmp").exists(), "the write is atomic")

            log.done("runs/my-search/results.json")
            document = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(document["status"], "done")
            self.assertEqual(document["result_url"], "runs/my-search/results.json")

            log.start("again", command="import-rail")
            log.fail("provider call cap of 2 would be exceeded")
            document = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(document["status"], "failed")
            self.assertEqual(document["error"], "provider call cap of 2 would be exceeded")
            self.assertEqual(document["events"], [])

    def test_events_are_validated_so_the_viewer_can_trust_them(self):
        log = ProgressLog(None)
        log.start("x", command="research")
        with self.assertRaisesRegex(ValueError, "stage"):
            log.event("teleport", "no")
        with self.assertRaisesRegex(ValueError, "level"):
            log.event("score", "no", level="loud")
        with self.assertRaisesRegex(ValueError, "cache"):
            log.event("score", "no", cache="stale")

    def test_result_url_only_names_direct_children_of_research_runs(self):
        self.assertEqual(
            result_url(ROOT / "research-runs" / "my-search", ROOT), "runs/my-search/results.json"
        )
        self.assertIsNone(result_url(ROOT / "research-runs" / "a" / "b", ROOT))
        self.assertIsNone(result_url(ROOT / "elsewhere" / "my-search", ROOT))

    def test_the_research_command_reports_every_stage_and_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            feed = temporary / PROGRESS_FILE
            execute_research(
                root=ROOT,
                output=temporary / "run",
                cache_directory=temporary / "cache",
                run_id="progress-test",
                latitude=51.5,
                longitude=-0.1,
                duration_minutes=30,
                route_profile="driving-car",
                api_key="",
                include_local_preferences=False,
                transport=ProviderTransport(),
                generated_at="2026-09-03T09:00:00+00:00",
                progress=ProgressLog(feed),
            )
            document = json.loads(feed.read_text(encoding="utf-8"))
            self.assertEqual(document["status"], "done")
            self.assertEqual(
                [event["stage"] for event in document["events"]],
                ["boundary", "discovery", "measure", "score", "write"],
            )
            boundary, discovery, measure, score, write = document["events"]
            self.assertEqual(boundary["provider"], "distance-proxy")
            self.assertEqual(boundary["counts"], {"vertices": 64})
            self.assertEqual(discovery["counts"]["candidates"], 1)
            self.assertEqual(discovery["cache"], "miss")
            self.assertIn("cafes", measure["counts"])
            self.assertEqual(score["counts"]["ranked"], 1)
            self.assertEqual(score["counts"]["pass"], 1)
            self.assertIn("run", write["message"])
            self.assertIsNone(document["result_url"], "a run outside research-runs has no serve URL")

            class Broken:
                def request(self, *args, **kwargs):
                    raise RuntimeError("provider unreachable")

            with self.assertRaisesRegex(RuntimeError, "unreachable"):
                execute_research(
                    root=ROOT,
                    output=temporary / "broken",
                    cache_directory=temporary / "cache-broken",
                    run_id="progress-fail",
                    latitude=51.5,
                    longitude=-0.1,
                    duration_minutes=30,
                    route_profile="driving-car",
                    api_key="",
                    include_local_preferences=False,
                    transport=Broken(),
                    generated_at="2026-09-03T09:00:00+00:00",
                    progress=ProgressLog(feed),
                )
            document = json.loads(feed.read_text(encoding="utf-8"))
            self.assertEqual(document["status"], "failed")
            self.assertIn("provider unreachable", document["error"])
            self.assertEqual([event["stage"] for event in document["events"]], ["boundary"])


class ServeTests(unittest.TestCase):
    def test_serves_only_the_viewer_the_feed_and_finished_results_on_loopback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "app" / "dist").mkdir(parents=True)
            (root / "app" / "dist" / "index.html").write_text("<title>viewer</title>", encoding="utf-8")
            runs = root / "research-runs"
            (runs / "run-a").mkdir(parents=True)
            (runs / PROGRESS_FILE).write_text('{"status": "running"}', encoding="utf-8")
            (runs / "run-a" / "results.json").write_text('{"run_id": "run-a"}', encoding="utf-8")
            (runs / "run-a" / "profile.json").write_text('{"secret": true}', encoding="utf-8")
            (runs / "run-a" / "photos").mkdir()
            (runs / "run-a" / "photos" / "run-a.jpg").write_bytes(b"JPEG-BYTES")
            (runs / "run-a" / "photos" / "notes.txt").write_text("private", encoding="utf-8")
            (runs / "secret.txt").write_text("origin", encoding="utf-8")

            server = make_server(root, 0)
            host, port = server.server_address[:2]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                self.assertEqual(host, "127.0.0.1")
                base = f"http://127.0.0.1:{port}"
                with urlopen(f"{base}/") as response:
                    self.assertIn(b"viewer", response.read())
                with urlopen(f"{base}/{PROGRESS_FILE}") as response:
                    self.assertEqual(response.headers["Content-Type"], "application/json; charset=utf-8")
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                    self.assertEqual(json.loads(response.read()), {"status": "running"})
                with urlopen(f"{base}/runs/run-a/results.json") as response:
                    self.assertEqual(json.loads(response.read()), {"run_id": "run-a"})
                with urlopen(f"{base}/runs/run-a/photos/run-a.jpg") as response:
                    self.assertEqual(response.headers["Content-Type"], "image/jpeg")
                    self.assertEqual(response.read(), b"JPEG-BYTES")
                for forbidden in (
                    "/runs/run-a/profile.json", "/runs/../secret.txt", "/research-runs/secret.txt",
                    "/runs/%2e%2e/secret.txt", "/runs/missing/results.json", "/research-runs/run-a/results.json",
                    "/runs/run-a/photos/notes.txt", "/runs/run-a/photos/../profile.json", "/runs/run-a/photos/missing.jpg",
                ):
                    with self.subTest(path=forbidden):
                        with self.assertRaises(HTTPError) as caught:
                            urlopen(f"{base}{forbidden}")
                        self.assertEqual(caught.exception.code, 404)
                        caught.exception.close()
            finally:
                server.shutdown()
                server.server_close()
