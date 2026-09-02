# Recorded Overpass response

`welwyn-garden-city-sample.json` is a real Overpass API response recorded on
2026-09-02 (OSM base timestamp 2026-09-02T22:52:05Z) for the query that
`OverpassAmenityCollector(walk_radius_metres=600).build_query()` produces for a
small polygon around the Welwyn Garden City place node. It exists so the tests
exercise the exact element shapes the live query returns: node points of
interest with `lat`/`lon`, ways with `center` or `bounds`, and highway ways with
`geometry`. The file was trimmed to drop `nodes` arrays from non-highway ways
and `bounds` from highway ways; no coordinate or tag was edited.

Data © OpenStreetMap contributors, licensed under the
[Open Database License](https://www.openstreetmap.org/copyright).
