from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from planner.models import PlanRequest
from planner.product import create_trip_plan
from planner.routing import nearest_neighbor_route, route_length_km, two_opt
from planner.storage import PlanRepository


def sample_pois() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["a", "Museum A", 23.100, 113.240, "tourism=museum", 4.9, 90, 0.9, "09:00-17:00"],
            ["b", "Park B", 23.105, 113.245, "leisure=park", 4.7, 60, 0.8, "06:00-22:00"],
            ["c", "Gallery C", 23.110, 113.250, "tourism=gallery", 4.6, 60, 0.7, "09:00-18:00"],
            ["d", "Tower D", 23.300, 113.500, "tourism=attraction", 4.8, 90, 0.9, "09:00-22:00"],
            ["e", "Garden E", 23.305, 113.505, "leisure=garden", 4.5, 60, 0.6, "07:00-20:00"],
            ["f", "Market F", 23.310, 113.510, "shop=marketplace", 4.4, 60, 0.7, "08:00-21:00"],
        ],
        columns=[
            "poi_id", "name", "lat", "lon", "category", "rating",
            "duration_min", "popularity", "opening_hours",
        ],
    )


class ProductPlannerTest(unittest.TestCase):
    def test_generates_two_days_with_time_budget(self):
        request = PlanRequest(
            city="Test City",
            num_days=2,
            source="osm",
            max_pois=6,
            max_daily_hours=4,
        )
        plan = create_trip_plan(request, pois=sample_pois())

        self.assertEqual(2, len(plan.days))
        self.assertEqual(6, plan.total_pois)
        self.assertTrue(all(day.total_minutes <= 240 for day in plan.days))
        self.assertTrue(all(day.visits for day in plan.days))

    def test_persists_and_reads_plan(self):
        request = PlanRequest(city="Test City", num_days=2, source="osm", max_pois=6)
        with tempfile.TemporaryDirectory() as directory:
            repository = PlanRepository(Path(directory) / "plans.db")
            plan = create_trip_plan(request, pois=sample_pois(), repository=repository)
            stored = repository.get(plan.plan_id)

        self.assertIsNotNone(stored)
        self.assertEqual(plan.plan_id, stored["plan_id"])
        self.assertEqual("Test City", stored["city"])

    def test_rejects_invalid_request(self):
        with self.assertRaises(ValueError):
            PlanRequest(city="", num_days=0).validate()

    def test_two_opt_never_makes_route_longer(self):
        pois = sample_pois().iloc[:4].reset_index(drop=True)
        initial = nearest_neighbor_route(pois)
        optimized = two_opt(initial, pois)
        self.assertLessEqual(route_length_km(pois, optimized), route_length_km(pois, initial))


if __name__ == "__main__":
    unittest.main()
