"""One freely licensed photo per place: lookup, licence gate, cache, and the command."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from location3.net import HttpResponse
from location3.photos import (
    describe_photo_plan, fetch_photos, merge_photo_research, slug, validate_photo_research,
)
from location3.photos_cli import main as photos_main
from location3.reporting import write_bundle
from location3.scoring import score_research
from location3.validation import validate_provenance

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64


def _page(title, image=None, lat=None, lon=None, disambiguation=False, missing=False):
    page = {"title": title}
    if missing:
        page["missing"] = True
    if image:
        page["pageimage"] = image
    if lat is not None:
        page["coordinates"] = [{"lat": lat, "lon": lon}]
    if disambiguation:
        page["pageprops"] = {"disambiguation": ""}
    return page


class WikiTransport:
    """Wikipedia and Commons as a fixture: title lookups, a geosearch, metadata, and bytes."""

    def __init__(self, *, licence="CC BY-SA 4.0", by_title=None, nearby=None):
        self.calls = []
        self.licence = licence
        self.by_title = by_title if by_title is not None else {
            "Alpha": _page("Alpha", "Alpha_view.jpg", 51.5, -0.1),
            "Newport": _page("Newport", disambiguation=True),
            "Nowhere": _page("Nowhere", missing=True),
        }
        self.nearby = nearby if nearby is not None else [
            _page("Newport Castle", None, 51.6, -3.0),
            _page("Newport, Wales", "Newport_riverfront.jpg", 51.59, -2.99),
        ]

    def request(self, method, url, *, headers, body, timeout):
        self.calls.append(url)
        assert headers["User-Agent"].startswith("LOCATION3/"), "Wikimedia asks for a descriptive agent"
        parts = urlsplit(url)
        params = {key: value[0] for key, value in parse_qs(parts.query).items()}
        if parts.netloc == "upload.wikimedia.org":
            return HttpResponse(200, JPEG, {"Content-Type": "image/jpeg"})
        if parts.netloc == "en.wikipedia.org":
            if params.get("generator") == "geosearch":
                pages = self.nearby
            else:
                pages = [self.by_title.get(params["titles"], _page(params["titles"], missing=True))]
            return HttpResponse(200, json.dumps({"query": {"pages": pages}}).encode(), {})
        if parts.netloc == "commons.wikimedia.org":
            name = params["titles"].removeprefix("File:")
            info = {
                "thumburl": f"https://upload.wikimedia.org/thumb/{name}/{params['iiurlwidth']}px-{name}",
                "thumbwidth": int(params["iiurlwidth"]), "thumbheight": 720,
                "descriptionurl": f"https://commons.wikimedia.org/wiki/File:{name}",
                "extmetadata": {
                    "Artist": {"value": '<a href="https://example.org/u/jo">Jo &amp; Sam</a>'},
                    "LicenseShortName": {"value": self.licence},
                    "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0"},
                },
            }
            return HttpResponse(200, json.dumps({"query": {"pages": [{"imageinfo": [info]}]}}).encode(), {})
        raise AssertionError(f"unexpected host {parts.netloc}")


def _candidate(cid, name, lat, lon):
    return {"id": cid, "name": name, "location": {"latitude": lat, "longitude": lon}}


class PhotoLookupTests(unittest.TestCase):
    def test_the_plan_names_every_place_and_the_call_cap_without_the_origin(self):
        lines = describe_photo_plan([_candidate("alpha", "Alpha", 51.5, -0.1)])
        text = "\n".join(lines)
        self.assertIn("Alpha: Wikipedia page lookup by name", text)
        self.assertIn("Maximum live calls: 4", text)
        self.assertIn("nothing about the origin", text)

    def test_looks_up_by_name_falls_back_to_geosearch_and_skips_what_it_cannot_find(self):
        transport = WikiTransport()
        research, files, notes = fetch_photos(
            [
                _candidate("alpha", "Alpha", 51.5, -0.1),
                _candidate("newport", "Newport", 51.59, -2.99),
                _candidate("nowhere", "Nowhere", 50.0, 0.0),
            ],
            transport,
            retrieved_at="2026-09-03T10:00:00+00:00",
        )
        self.assertEqual([photo["candidate_id"] for photo in research["photos"]], ["alpha", "newport"])
        alpha, newport = research["photos"]
        self.assertEqual(alpha["file"], "photos/alpha.jpg")
        self.assertEqual(alpha["author"], "Jo & Sam", "artist HTML is reduced to text")
        self.assertEqual(alpha["licence"], "CC BY-SA 4.0")
        self.assertEqual(alpha["width"], 1280)
        self.assertEqual(newport["page_title"], "Newport, Wales", "a disambiguation page defers to geosearch")
        self.assertEqual(files["photos/alpha.jpg"], JPEG)
        self.assertEqual(notes, ["Nowhere: no freely licensed lead image found"])
        # Nowhere: title lookup and geosearch, then nothing. Newport: title, geosearch, metadata, image.
        self.assertEqual(len(transport.calls), 3 + 4 + 2)
        validate_photo_research(research, {"alpha", "newport", "nowhere"})

    def test_a_far_away_page_of_the_same_name_is_not_trusted(self):
        transport = WikiTransport(by_title={"Alpha": _page("Alpha", "Alpha_view.jpg", 40.7, -74.0)}, nearby=[])
        research, _, notes = fetch_photos(
            [_candidate("alpha", "Alpha", 51.5, -0.1)], transport, retrieved_at="2026-09-03T10:00:00+00:00"
        )
        self.assertEqual(research["photos"], [])
        self.assertEqual(len(notes), 1)

    def test_non_free_licences_mean_no_photo(self):
        for licence in ("CC BY-NC 2.0", "CC BY-ND 4.0", "All rights reserved"):
            with self.subTest(licence=licence):
                research, files, _ = fetch_photos(
                    [_candidate("alpha", "Alpha", 51.5, -0.1)],
                    WikiTransport(licence=licence),
                    retrieved_at="2026-09-03T10:00:00+00:00",
                )
                self.assertEqual(research["photos"], [])
                self.assertEqual(files, {})
        for licence in ("CC0", "CC BY 2.0", "Public domain", "CC BY-SA 3.0"):
            with self.subTest(licence=licence):
                research, _, _ = fetch_photos(
                    [_candidate("alpha", "Alpha", 51.5, -0.1)],
                    WikiTransport(licence=licence),
                    retrieved_at="2026-09-03T10:00:00+00:00",
                )
                self.assertEqual(len(research["photos"]), 1)

    def test_validation_rejects_unknown_candidates_bad_files_and_duplicates(self):
        photo = {
            "candidate_id": "alpha", "file": "photos/alpha.jpg", "width": 1280, "height": 720,
            "title": "Alpha", "author": "Jo", "licence": "CC BY 4.0",
            "licence_url": "https://creativecommons.org/licenses/by/4.0", "source_url": "https://commons.wikimedia.org/wiki/File:A.jpg",
            "page_title": "Alpha",
        }
        base = {"schema_version": "1", "provider": "wikipedia", "retrieved_at": "2026-09-03T10:00:00+00:00"}
        validate_photo_research({**base, "photos": [photo]}, {"alpha"})
        with self.assertRaisesRegex(ValueError, "unknown candidate"):
            validate_photo_research({**base, "photos": [photo]}, {"beta"})
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_photo_research({**base, "photos": [photo, photo]}, {"alpha"})
        with self.assertRaisesRegex(ValueError, "photo file"):
            validate_photo_research({**base, "photos": [{**photo, "file": "../alpha.jpg"}]}, {"alpha"})
        with self.assertRaisesRegex(ValueError, "free licence"):
            validate_photo_research({**base, "photos": [{**photo, "licence": "CC BY-NC 4.0"}]}, {"alpha"})

    def test_slugs_are_safe_file_names(self):
        self.assertEqual(slug("Welwyn Garden City"), "welwyn-garden-city")
        self.assertEqual(slug("St. Albans / Verulam"), "st-albans-verulam")
        self.assertEqual(slug("!!!"), "place")


class PhotoCommandTests(unittest.TestCase):
    def _make_run(self, directory: Path) -> Path:
        profile = json.loads((ROOT / "fixtures/demo/profile.json").read_text(encoding="utf-8"))
        evidence = json.loads((ROOT / "fixtures/demo/evidence.json").read_text(encoding="utf-8"))
        from location3.config import load_preferences

        preferences = load_preferences(ROOT, include_local=False)
        profile["weights"] = preferences["weights"]
        profile["category_weights"] = preferences["category_weights"]
        profile["unknown_data_policy"] = preferences["scoring"]["unknown_data_policy"]
        results = score_research(profile, evidence, "2026-08-01T12:00:00+00:00")
        run = directory / "research-runs" / "demo"
        write_bundle(run, profile, evidence, results)
        return run

    def test_preview_makes_no_call_and_execute_writes_photos_then_hits_the_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = self._make_run(root)
            names = {c["name"] for c in json.loads((run / "evidence.json").read_text(encoding="utf-8"))["candidates"]}
            transport = WikiTransport(by_title={
                name: _page(name, f"{name.replace(' ', '_')}.jpg", 51.7, -0.5) for name in names
            })
            clock = lambda: datetime(2026, 9, 3, 10, tzinfo=timezone.utc)  # noqa: E731

            self.assertEqual(photos_main(["--run-dir", str(run), "--cache", str(root / "cache")], transport=transport, clock=clock), 0)
            self.assertEqual(transport.calls, [], "the preview never touches the network")

            self.assertEqual(
                photos_main(["--run-dir", str(run), "--cache", str(root / "cache"), "--execute"], transport=transport, clock=clock), 0
            )
            output = run.with_name("demo-photos")
            results = json.loads((output / "results.json").read_text(encoding="utf-8"))
            evidence = json.loads((output / "evidence.json").read_text(encoding="utf-8"))
            manifest = json.loads((output / "provenance.json").read_text(encoding="utf-8"))
            self.assertEqual(len(evidence["photo_research"]["photos"]), len(names))
            for candidate in results["candidates"]:
                self.assertEqual(candidate["photo"]["candidate_id"], candidate["id"])
                self.assertTrue((output / candidate["photo"]["file"]).is_file())
            self.assertTrue(any(source.startswith("https://commons.wikimedia.org/wiki/File:") for source in manifest["sources"]))
            self.assertIn("CC BY-SA 4.0", manifest["licences"])
            artifacts = {name: (output / name).read_bytes() for name in ("profile.json", "evidence.json", "results.json")}
            validate_provenance(evidence, manifest, artifacts)
            live_calls = len(transport.calls)
            self.assertEqual(live_calls, 3 * len(names))
            feed = json.loads((root / "research-runs" / "progress.json").read_text(encoding="utf-8"))
            self.assertEqual(feed["status"], "done")
            self.assertEqual(feed["command"], "photos")

            # The same command again is served from the cache.
            self.assertEqual(
                photos_main(["--run-dir", str(run), "--cache", str(root / "cache"), "--execute"], transport=transport, clock=clock), 0
            )
            self.assertEqual(len(transport.calls), live_calls, "a repeat run makes no new calls")
            again = json.loads((output / "provenance.json").read_text(encoding="utf-8"))
            self.assertTrue(again["cache_used"])

    def test_merge_attaches_the_research_and_scoring_carries_it_through(self):
        evidence = json.loads((ROOT / "fixtures/demo/evidence.json").read_text(encoding="utf-8"))
        first = evidence["candidates"][0]["id"]
        research = {
            "schema_version": "1", "provider": "wikipedia", "retrieved_at": "2026-09-03T10:00:00+00:00",
            "photos": [{
                "candidate_id": first, "file": f"photos/{first}.jpg", "width": 1280, "height": 720,
                "title": "T", "author": "A", "licence": "CC BY 4.0", "licence_url": None,
                "source_url": "https://commons.wikimedia.org/wiki/File:T.jpg", "page_title": "T",
            }],
        }
        merged = merge_photo_research(evidence, research)
        self.assertNotIn("photo_research", evidence, "merging never mutates the input")
        profile = json.loads((ROOT / "fixtures/demo/profile.json").read_text(encoding="utf-8"))
        from location3.config import load_preferences

        preferences = load_preferences(ROOT, include_local=False)
        profile["weights"] = preferences["weights"]
        profile["category_weights"] = preferences["category_weights"]
        profile["unknown_data_policy"] = preferences["scoring"]["unknown_data_policy"]
        plain = score_research(profile, evidence, "2026-08-01T12:00:00+00:00")
        pictured = score_research(profile, merged, "2026-08-01T12:00:00+00:00")
        by_id = {c["id"]: c for c in pictured["candidates"]}
        self.assertEqual(by_id[first]["photo"]["file"], f"photos/{first}.jpg")
        for candidate in plain["candidates"]:
            self.assertEqual(candidate["overall_score"], by_id[candidate["id"]]["overall_score"], "a photo never moves a score")
        self.assertEqual(sum("photo" in c for c in pictured["candidates"]), 1)


if __name__ == "__main__":
    unittest.main()
