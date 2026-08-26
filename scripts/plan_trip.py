"""Command-line entry point for the product MVP itinerary planner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from planner.models import PlanRequest
from planner.product import create_trip_plan
from planner.storage import PlanRepository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a multi-day travel itinerary")
    parser.add_argument("--city", required=True)
    parser.add_argument("--days", required=True, type=int)
    parser.add_argument("--source", choices=["llm", "osm"], default="llm")
    parser.add_argument("--poi-file", help="OSM-compatible POI CSV path")
    parser.add_argument("--preferences")
    parser.add_argument("--budget")
    parser.add_argument("--interests", nargs="*", default=[])
    parser.add_argument("--max-pois", type=int)
    parser.add_argument("--min-rating", type=float, default=3.5)
    parser.add_argument("--max-daily-hours", type=float, default=8.0)
    parser.add_argument("--start-time", default="09:00")
    parser.add_argument("--walking-speed-kmh", type=float, default=4.0)
    parser.add_argument("--database", type=Path, default=Path("data/planner.db"))
    parser.add_argument("--output", type=Path, help="Also save the result as JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    request = PlanRequest(
        city=args.city,
        num_days=args.days,
        source=args.source,
        preferences=args.preferences,
        budget=args.budget,
        interests=args.interests,
        max_pois=args.max_pois,
        min_rating=args.min_rating,
        max_daily_hours=args.max_daily_hours,
        start_time=args.start_time,
        walking_speed_kmh=args.walking_speed_kmh,
        poi_file=args.poi_file,
    )
    try:
        plan = create_trip_plan(request, repository=PlanRepository(args.database))
    except Exception as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1

    result = plan.to_dict()
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
