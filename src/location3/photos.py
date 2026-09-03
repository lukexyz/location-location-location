"""One freely licensed photo per place, with its author and licence kept beside it.

A photo is evidence like everything else: it has a source page, an author, and
a licence, and the viewer shows all three. The lookup works for any candidate
the pipeline produces, keyed by its name and coordinates, and never assumes a
fixture. Every call goes through the caching transport, so a second run over
the same towns makes no new requests.
"""

from __future__ import annotations

from copy import deepcopy
from html import unescape
import json
from math import asin, cos, radians, sin, sqrt
import re
from typing import Any, Mapping
from urllib.parse import quote, urlencode, urlsplit

from .fields import exact_keys, http_url, iso_datetime, nonempty
from .net import HttpResponse, HttpTransport

PHOTO_PROVIDER = "wikipedia"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "LOCATION3/0.1 (https://github.com/lukexyz/location-location-location)"
DEFAULT_WIDTH = 1280
MAX_PAGE_DISTANCE_KM = 25.0
GEOSEARCH_RADIUS_M = 10_000
CALLS_PER_PLACE = 4  # title lookup, geosearch fallback, Commons metadata, the image
PHOTO_FILE = re.compile(r"^photos/[a-z0-9][a-z0-9-]{0,79}\.(jpg|png)$")
ACCEPTED_LICENCE = re.compile(
    r"^(cc0(\s[\d.]+)?|cc by(-sa)?(\s[\d.]+)?( [a-z]{2})?|public domain.*|pd.*)$", re.I
)
_TAGS = re.compile(r"<[^>]+>")


# --- Research contract -----------------------------------------------------------

def validate_photo_research(research: dict[str, Any], allowed_candidate_ids: set[str]) -> None:
    exact_keys(research, {"schema_version", "provider", "retrieved_at", "photos"}, "photo research")
    if research.get("schema_version") != "1":
        raise ValueError("unsupported photo research schema_version")
    nonempty(research, "provider")
    iso_datetime(nonempty(research, "retrieved_at"), "retrieved_at")
    photos = research.get("photos")
    if not isinstance(photos, list):
        raise ValueError("photos must be an array")
    seen: set[str] = set()
    for photo in photos:
        if not isinstance(photo, dict):
            raise ValueError("photos must be objects")
        exact_keys(
            photo,
            {
                "candidate_id", "file", "width", "height", "title", "author", "licence",
                "licence_url", "source_url", "page_title",
            },
            "photo",
        )
        candidate_id = nonempty(photo, "candidate_id")
        if candidate_id not in allowed_candidate_ids:
            raise ValueError(f"photo references an unknown candidate: {candidate_id}")
        if candidate_id in seen:
            raise ValueError(f"duplicate photo for candidate: {candidate_id}")
        seen.add(candidate_id)
        if not PHOTO_FILE.fullmatch(nonempty(photo, "file")):
            raise ValueError("photo file must be photos/<slug>.jpg or .png")
        for key in ("width", "height"):
            value = photo.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"photo {key} must be a positive integer")
        nonempty(photo, "title")
        nonempty(photo, "author")
        nonempty(photo, "page_title")
        if not ACCEPTED_LICENCE.fullmatch(nonempty(photo, "licence").strip()):
            raise ValueError(f"photo licence is not a free licence: {photo['licence']}")
        licence_url = photo.get("licence_url")
        if licence_url is not None:
            http_url(licence_url if isinstance(licence_url, str) else "", "licence_url")
        http_url(nonempty(photo, "source_url"), "source_url")


def merge_photo_research(evidence: dict[str, Any], research: dict[str, Any]) -> dict[str, Any]:
    """Attach validated photo research to a copy of the evidence bundle."""
    candidate_ids = {candidate["id"] for candidate in evidence["candidates"]}
    validate_photo_research(research, candidate_ids)
    merged = deepcopy(evidence)
    merged["photo_research"] = deepcopy(research)
    return merged


def photo_for(evidence: dict[str, Any], candidate_id: str) -> dict[str, Any] | None:
    research = evidence.get("photo_research")
    if not research:
        return None
    for photo in research["photos"]:
        if photo["candidate_id"] == candidate_id:
            return deepcopy(photo)
    return None


# --- Planning ------------------------------------------------------------------------

def describe_photo_plan(
    candidates: list[dict[str, Any]],
    *,
    width: int = DEFAULT_WIDTH,
    preferred: Mapping[str, str] | None = None,
) -> list[str]:
    """What the command will send, one line per place, before anything is fetched."""
    lines = [f"Photo plan: one freely licensed Wikipedia lead image per place, {len(candidates)} places"]
    for candidate in candidates:
        location = candidate["location"]
        title = (preferred or {}).get(candidate["id"])
        if title:
            lines.append(
                f"  {candidate['name']}: Wikipedia page \"{title}\" as asked, not checked against "
                f"coordinates ({urlsplit(WIKIPEDIA_API).netloc})"
            )
            continue
        lines.append(
            f"  {candidate['name']}: Wikipedia page lookup by name, checked against "
            f"{location['latitude']:.2f}, {location['longitude']:.2f} ({urlsplit(WIKIPEDIA_API).netloc})"
        )
    lines.append(
        "Per page found: one Commons metadata call for the author and licence, then the image "
        f"at {width}px wide from upload.wikimedia.org"
    )
    lines.append("Sent: place names and rounded coordinates only; nothing about the origin, budget, or limits")
    lines.append("Accepted licences: CC0, CC BY, CC BY-SA, public domain; anything else means no photo")
    lines.append(
        f"Maximum live calls: {CALLS_PER_PLACE * len(candidates)} "
        f"({CALLS_PER_PLACE} per place; compatible cache hits make none)"
    )
    return lines


# --- Fetching ----------------------------------------------------------------------------

def fetch_photos(
    candidates: list[dict[str, Any]],
    transport: HttpTransport,
    *,
    retrieved_at: str,
    width: int = DEFAULT_WIDTH,
    preferred: Mapping[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, bytes], list[str]]:
    """Look every candidate up and return the research record, the image bytes, and notes.

    `preferred` maps a candidate id to the Wikipedia page title to use instead of the
    lookup by name, for a place whose name finds the wrong article or none.
    """
    photos: list[dict[str, Any]] = []
    files: dict[str, bytes] = {}
    notes: list[str] = []
    for candidate in candidates:
        try:
            found = _photo_for_candidate(
                candidate, transport, width=width,
                preferred_title=(preferred or {}).get(candidate["id"]),
            )
        except RuntimeError as error:
            if "cap" in str(error):
                raise
            notes.append(f"{candidate['name']}: lookup failed ({error})")
            continue
        if found is None:
            notes.append(f"{candidate['name']}: no freely licensed lead image found")
            continue
        record, image = found
        photos.append(record)
        files[record["file"]] = image
    research = {
        "schema_version": "1",
        "provider": PHOTO_PROVIDER,
        "retrieved_at": retrieved_at,
        "photos": photos,
    }
    return research, files, notes


def _photo_for_candidate(
    candidate: dict[str, Any], transport: HttpTransport, *, width: int, preferred_title: str | None = None
) -> tuple[dict[str, Any], bytes] | None:
    page = lookup_page(transport, candidate["name"], candidate["location"], preferred_title=preferred_title)
    if page is None:
        return None
    metadata = commons_metadata(transport, page["image"], width=width)
    if metadata is None:
        return None
    image = _get(transport, metadata["thumb_url"]).body
    extension = "png" if metadata["thumb_url"].lower().endswith(".png") else "jpg"
    record = {
        "candidate_id": candidate["id"],
        "file": f"photos/{slug(candidate['id'])}.{extension}",
        "width": metadata["width"],
        "height": metadata["height"],
        "title": page["title"],
        "author": metadata["author"],
        "licence": metadata["licence"],
        "licence_url": metadata["licence_url"],
        "source_url": metadata["source_url"],
        "page_title": page["title"],
    }
    return record, image


def lookup_page(
    transport: HttpTransport, name: str, location: Mapping[str, float], *, preferred_title: str | None = None
) -> dict[str, Any] | None:
    """The Wikipedia article for a place: by name when it is unambiguous and nearby, else by geosearch.

    A preferred title is looked up as asked and not checked against the coordinates; if
    it is missing, ambiguous, or has no free lead image there is no substitute.
    """
    if preferred_title:
        asked = _query(transport, WIKIPEDIA_API, {
            "action": "query", "format": "json", "formatversion": "2", "redirects": "1",
            "titles": preferred_title, "prop": "pageimages|coordinates|pageprops",
            "piprop": "name|original", "pilicense": "free", "ppprop": "disambiguation", "colimit": "1",
        })
        return _first_usable_page(asked, location, check_distance=False)
    by_name = _query(transport, WIKIPEDIA_API, {
        "action": "query", "format": "json", "formatversion": "2", "redirects": "1",
        "titles": name, "prop": "pageimages|coordinates|pageprops",
        "piprop": "name|original", "pilicense": "free", "ppprop": "disambiguation", "colimit": "1",
    })
    page = _first_usable_page(by_name, location)
    if page is not None:
        return page
    nearby = _query(transport, WIKIPEDIA_API, {
        "action": "query", "format": "json", "formatversion": "2",
        "generator": "geosearch",
        "ggscoord": f"{location['latitude']}|{location['longitude']}",
        "ggsradius": str(GEOSEARCH_RADIUS_M), "ggslimit": "10",
        "prop": "pageimages|coordinates|pageprops",
        "piprop": "name|original", "pilicense": "free", "ppprop": "disambiguation", "colimit": "1",
    })
    return _first_usable_page(nearby, location)


def _first_usable_page(
    payload: dict[str, Any], location: Mapping[str, float], *, check_distance: bool = True
) -> dict[str, Any] | None:
    pages = payload.get("query", {}).get("pages", [])
    if isinstance(pages, dict):  # formatversion 1 shape, tolerated
        pages = list(pages.values())
    for page in pages:
        if page.get("missing") or page.get("invalid"):
            continue
        if "disambiguation" in page.get("pageprops", {}):
            continue
        image = page.get("pageimage")
        if not image:
            continue
        coordinates = page.get("coordinates") or []
        if coordinates and check_distance:
            distance = _haversine_km(
                float(location["latitude"]), float(location["longitude"]),
                float(coordinates[0]["lat"]), float(coordinates[0]["lon"]),
            )
            if distance > MAX_PAGE_DISTANCE_KM:
                continue
        return {"title": str(page.get("title", "")).strip() or image, "image": str(image)}
    return None


def commons_metadata(transport: HttpTransport, image_name: str, *, width: int) -> dict[str, Any] | None:
    payload = _query(transport, COMMONS_API, {
        "action": "query", "format": "json", "formatversion": "2",
        "titles": f"File:{image_name}", "prop": "imageinfo",
        "iiprop": "extmetadata|url|size", "iiurlwidth": str(width),
        "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl|Credit",
    })
    pages = payload.get("query", {}).get("pages", [])
    if isinstance(pages, dict):
        pages = list(pages.values())
    for page in pages:
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        extra = info.get("extmetadata", {})
        licence = _clean_text(extra.get("LicenseShortName", {}).get("value", ""))
        if not ACCEPTED_LICENCE.fullmatch(licence):
            return None
        thumb_url = info.get("thumburl") or info.get("url")
        if not thumb_url:
            return None
        author = _clean_text(extra.get("Artist", {}).get("value", "")) or _clean_text(
            extra.get("Credit", {}).get("value", "")
        ) or "Unknown author"
        licence_url = _clean_text(extra.get("LicenseUrl", {}).get("value", "")) or None
        return {
            "thumb_url": str(thumb_url),
            "width": int(info.get("thumbwidth") or info.get("width")),
            "height": int(info.get("thumbheight") or info.get("height")),
            "author": author[:120],
            "licence": licence,
            "licence_url": licence_url if licence_url and licence_url.startswith("http") else None,
            "source_url": str(info.get("descriptionurl") or f"https://commons.wikimedia.org/wiki/File:{quote(image_name)}"),
        }
    return None


# --- Helpers -----------------------------------------------------------------------------

def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (cleaned or "place")[:80]


def _query(transport: HttpTransport, endpoint: str, params: Mapping[str, str]) -> dict[str, Any]:
    url = f"{endpoint}?{urlencode(params, quote_via=quote)}"
    response = _get(transport, url)
    try:
        payload = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"{urlsplit(endpoint).netloc} returned something other than JSON") from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"{urlsplit(endpoint).netloc} returned an unexpected document")
    return payload


def _get(transport: HttpTransport, url: str) -> HttpResponse:
    response = transport.request(
        "GET", url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"}, body=b"", timeout=30.0
    )
    if not 200 <= response.status < 300:
        raise RuntimeError(f"{urlsplit(url).netloc} returned HTTP {response.status}")
    return response


def _clean_text(value: object) -> str:
    text = unescape(_TAGS.sub("", str(value)))
    return re.sub(r"\s+", " ", text).strip()


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(a))
