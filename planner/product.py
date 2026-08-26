"""Product MVP orchestration for generating a complete multi-day itinerary."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple
from uuid import uuid4

import numpy as np
import pandas as pd

from .clustering import geographic_kmeans_labels
from .config import CONFIG, CITY_BBOXES, POIFilterConfig
from .data_loader import filter_pois, load_osm_pois
from .llm_recommender import load_llm_recommended_pois
from .models import DayPlan, PlanRequest, TripPlan, Visit
from .routing import build_route, haversine_km
from .storage import PlanRepository


REQUIRED_POI_COLUMNS = {"poi_id", "lat", "lon", "category", "rating", "duration_min"}


def _load_pois(request: PlanRequest) -> pd.DataFrame:
    if request.source == "osm":
        return load_osm_pois(Path(request.poi_file) if request.poi_file else None)

    city_slug = request.city.lower().replace(" ", "_")
    cache_inputs = {
        "city": request.city.lower(),
        "days": request.num_days,
        "preferences": request.preferences,
        "budget": request.budget,
        "interests": request.interests,
        "num_pois": request.max_pois or request.num_days * 6,
    }
    fingerprint = hashlib.sha256(
        json.dumps(cache_inputs, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:12]
    cache_path = CONFIG.data.llm_poi_cache / f"{city_slug}-{fingerprint}.csv"
    legacy_cache = CONFIG.data.llm_poi_cache / f"{city_slug}.csv"
    if (
        not cache_path.exists()
        and not request.preferences
        and not request.budget
        and not request.interests
        and legacy_cache.exists()
    ):
        cache_path = legacy_cache
    return load_llm_recommended_pois(
        city=request.city,
        num_days=request.num_days,
        preferences=request.preferences,
        budget=request.budget,
        interests=request.interests or None,
        num_pois=request.max_pois or request.num_days * 6,
        cache_path=cache_path,
        use_cache=True,
    )


def _prepare_pois(raw_pois: pd.DataFrame, request: PlanRequest) -> pd.DataFrame:
    missing = REQUIRED_POI_COLUMNS - set(raw_pois.columns)
    if missing:
        raise ValueError(f"POI input is missing required columns: {', '.join(sorted(missing))}")

    pois = raw_pois.copy()
    for column in ["lat", "lon", "rating", "duration_min", "popularity"]:
        if column not in pois.columns:
            pois[column] = 0.0
        pois[column] = pd.to_numeric(pois[column], errors="coerce")
    pois["popularity"] = pois["popularity"].fillna(0.0).clip(0.0, 1.0)
    pois["duration_min"] = pois["duration_min"].fillna(60.0).clip(15.0, 480.0)
    if "opening_hours" not in pois.columns:
        pois["opening_hours"] = ""
    else:
        pois["opening_hours"] = pois["opening_hours"].fillna("")
    pois["name"] = pois.get("name", pois["poi_id"]).fillna(pois["poi_id"])
    pois = pois.dropna(subset=["lat", "lon", "rating"])
    pois = pois[
        pois["lat"].between(-90, 90)
        & pois["lon"].between(-180, 180)
        & ~((pois["lat"] == 0) & (pois["lon"] == 0))
    ]
    pois = pois.drop_duplicates(subset=["poi_id"], keep="first")
    pois = pois[pois["duration_min"] <= request.max_daily_hours * 60.0]

    bbox = CITY_BBOXES.get(request.city.lower())
    if bbox is not None:
        lat_min, lat_max, lon_min, lon_max = bbox
        pois = pois[
            pois["lat"].between(lat_min, lat_max)
            & pois["lon"].between(lon_min, lon_max)
        ]

    filter_config = POIFilterConfig(
        min_rating=request.min_rating,
        max_pois=request.max_pois or request.num_days * 6,
        category_limit=None,
        preferred_categories=CONFIG.poi_filter.preferred_categories,
        max_visit_time_hours=None,
        min_visit_time_hours=0.0,
        filter_unknown_names=True,
    )
    pois = filter_pois(pois, filter_config)
    if len(pois) < request.num_days:
        raise ValueError(
            f"Only {len(pois)} valid POIs remain; at least {request.num_days} are required"
        )
    return pois.reset_index(drop=True)


def _clock(start_time: str, minutes_after_start: float) -> str:
    hour, minute = (int(part) for part in start_time.split(":"))
    base = datetime(2000, 1, 1, hour, minute)
    return (base + timedelta(minutes=minutes_after_start)).strftime("%H:%M")


def _build_day(
    day_number: int,
    candidates: pd.DataFrame,
    request: PlanRequest,
) -> DayPlan:
    candidates = candidates.reset_index(drop=True)
    route = build_route(candidates, method="nn", use_two_opt=True)
    limit_minutes = request.max_daily_hours * 60.0
    elapsed = 0.0
    total_distance = 0.0
    total_visit = 0.0
    total_travel = 0.0
    visits: List[Visit] = []
    skipped: List[str] = []
    previous_row = None

    for poi_index in route:
        row = candidates.iloc[poi_index]
        distance = 0.0
        if previous_row is not None:
            distance = haversine_km(
                previous_row["lat"], previous_row["lon"], row["lat"], row["lon"]
            )
        travel_minutes = distance / request.walking_speed_kmh * 60.0
        visit_minutes = float(row["duration_min"])
        if elapsed + travel_minutes + visit_minutes > limit_minutes:
            skipped.append(str(row["poi_id"]))
            continue

        arrival = elapsed + travel_minutes
        departure = arrival + visit_minutes
        visits.append(
            Visit(
                poi_id=str(row["poi_id"]),
                name=str(row["name"]),
                category=str(row["category"]),
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                rating=float(row["rating"]),
                opening_hours=str(row["opening_hours"]),
                arrival_time=_clock(request.start_time, arrival),
                departure_time=_clock(request.start_time, departure),
                visit_minutes=visit_minutes,
                travel_from_previous_km=round(distance, 3),
                travel_from_previous_minutes=round(travel_minutes, 1),
            )
        )
        elapsed = departure
        total_distance += distance
        total_travel += travel_minutes
        total_visit += visit_minutes
        previous_row = row

    return DayPlan(
        day=day_number,
        visits=visits,
        route_length_km=round(total_distance, 3),
        visit_minutes=round(total_visit, 1),
        travel_minutes=round(total_travel, 1),
        total_minutes=round(elapsed, 1),
        skipped_poi_ids=skipped,
    )


def _ordered_clusters(pois: pd.DataFrame, labels: np.ndarray) -> List[Tuple[int, pd.DataFrame]]:
    clustered = pois.copy()
    clustered["_cluster"] = labels
    groups = []
    for label, group in clustered.groupby("_cluster"):
        centroid = (float(group["lat"].mean()), float(group["lon"].mean()))
        groups.append((centroid, int(label), group.drop(columns=["_cluster"])))
    groups.sort(key=lambda item: (item[0][0], item[0][1]))
    return [(label, group) for _, label, group in groups]


def create_trip_plan(
    request: PlanRequest,
    pois: Optional[pd.DataFrame] = None,
    repository: Optional[PlanRepository] = None,
) -> TripPlan:
    """Generate, optionally persist, and return a product itinerary."""

    request.validate()
    prepared = _prepare_pois(pois if pois is not None else _load_pois(request), request)
    labels = geographic_kmeans_labels(prepared, request.num_days)
    days = [
        _build_day(day_number, group, request)
        for day_number, (_, group) in enumerate(_ordered_clusters(prepared, labels), start=1)
    ]
    created_at = datetime.now(timezone.utc).isoformat()
    plan = TripPlan(
        plan_id=str(uuid4()),
        city=request.city.strip(),
        num_days=request.num_days,
        source=request.source,
        algorithm={
            "day_partition": "geographic KMeans on local kilometer coordinates",
            "daily_route": "highest-rated start + nearest neighbor + 2-opt",
            "distance": "Haversine great-circle distance",
            "time_budget": "greedy inclusion of travel and visit time",
        },
        days=days,
        total_pois=sum(len(day.visits) for day in days),
        total_route_length_km=round(sum(day.route_length_km for day in days), 3),
        total_minutes=round(sum(day.total_minutes for day in days), 1),
        created_at=created_at,
    )
    if repository is not None:
        repository.save(request.to_dict(), plan.to_dict())
    return plan
