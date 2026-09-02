from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from location3.walking import (
    CATCHMENT_METRES,
    FEATURE_SNAP_METRES,
    ORIGIN_SNAP_METRES,
    WalkingNetwork,
    distance_metres,
)


LAT = 51.5
LON = -0.1
METRES_PER_DEGREE_LAT = 111_320
METRES_PER_DEGREE_LON = 69_300  # at 51.5 degrees north


def offset(north_metres: float, east_metres: float) -> tuple[float, float]:
    return (
        LAT + north_metres / METRES_PER_DEGREE_LAT,
        LON + east_metres / METRES_PER_DEGREE_LON,
    )


def way(way_id: int, points: list[tuple[int, float, float]], **tags):
    return {
        "type": "way",
        "id": way_id,
        "tags": {"highway": "residential", **tags},
        "nodes": [node_id for node_id, _, _ in points],
        "geometry": [{"lat": lat, "lon": lon} for _, lat, lon in points],
    }


def u_shaped_network() -> WalkingNetwork:
    """A road that runs 800 m east, 800 m north, then 800 m back west."""
    east = offset(0, 800)
    north_east = offset(800, 800)
    north = offset(800, 0)
    return WalkingNetwork.from_elements([
        way(1, [(1, LAT, LON), (2, *east), (3, *north_east), (4, *north)]),
    ])


class WalkingNetworkTests(unittest.TestCase):
    def test_network_distance_follows_the_road_rather_than_the_crow(self):
        network = u_shaped_network()
        reach = network.reach(LAT, LON, cutoff_metres=3000)
        far_end = offset(800, 0)

        self.assertTrue(reach.usable)
        self.assertLess(distance_metres(LAT, LON, *far_end), 810)
        self.assertAlmostEqual(network.walking_metres(reach, *far_end), 2400, delta=5)

    def test_bounded_reach_leaves_features_beyond_the_cutoff_unreached(self):
        network = u_shaped_network()
        reach = network.reach(LAT, LON, cutoff_metres=CATCHMENT_METRES)

        self.assertIsNone(network.walking_metres(reach, *offset(800, 0)))
        self.assertAlmostEqual(network.walking_metres(reach, *offset(0, 600)), 600, delta=30)

    def test_long_segments_are_densified_so_mid_street_features_snap(self):
        network = u_shaped_network()
        beside_street = offset(40, 400)

        self.assertTrue(network.has_snappable_feature(*beside_street))
        self.assertGreater(network.node_count, 4)
        reach = network.reach(LAT, LON, cutoff_metres=CATCHMENT_METRES)
        self.assertAlmostEqual(network.walking_metres(reach, *beside_street), 440, delta=30)

    def test_features_and_origins_far_from_any_way_are_not_snapped(self):
        network = u_shaped_network()
        off_grid = offset(FEATURE_SNAP_METRES + 200, 400)

        self.assertFalse(network.has_snappable_feature(*off_grid))
        self.assertFalse(network.reach(*offset(ORIGIN_SNAP_METRES + 100, 400), 1200).usable)

    def test_unwalkable_and_malformed_ways_are_ignored(self):
        network = WalkingNetwork.from_elements([
            way(1, [(1, LAT, LON), (2, *offset(0, 100))], highway="motorway"),
            {"type": "way", "id": 2, "tags": {"highway": "footway"}, "nodes": [3, 4],
             "geometry": [{"lat": LAT, "lon": LON}]},
            {"type": "way", "id": 3, "tags": {"highway": "footway"}, "nodes": [5, True],
             "geometry": [{"lat": LAT, "lon": LON}, {"lat": LAT, "lon": LON + 0.001}]},
            {"type": "node", "id": 6, "lat": LAT, "lon": LON, "tags": {"highway": "footway"}},
        ])

        self.assertEqual(network.node_count, 0)
        self.assertFalse(network.reach(LAT, LON, 1200).usable)


if __name__ == "__main__":
    unittest.main()
