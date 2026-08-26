"""Product-facing request and response models for itinerary planning."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class PlanRequest:
    city: str
    num_days: int
    source: str = "llm"
    preferences: Optional[str] = None
    budget: Optional[str] = None
    interests: List[str] = field(default_factory=list)
    max_pois: Optional[int] = None
    min_rating: float = 3.5
    max_daily_hours: float = 8.0
    start_time: str = "09:00"
    walking_speed_kmh: float = 4.0
    poi_file: Optional[str] = None

    def validate(self) -> None:
        if not self.city.strip():
            raise ValueError("city cannot be empty")
        if not 1 <= self.num_days <= 14:
            raise ValueError("num_days must be between 1 and 14")
        if self.source not in {"llm", "osm"}:
            raise ValueError("source must be either 'llm' or 'osm'")
        if self.max_pois is not None and self.max_pois < self.num_days:
            raise ValueError("max_pois must be at least num_days")
        if not 2.0 <= self.max_daily_hours <= 16.0:
            raise ValueError("max_daily_hours must be between 2 and 16")
        if self.walking_speed_kmh <= 0:
            raise ValueError("walking_speed_kmh must be positive")
        try:
            hour, minute = (int(part) for part in self.start_time.split(":"))
        except (TypeError, ValueError):
            raise ValueError("start_time must use HH:MM format") from None
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("start_time must use HH:MM format")

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass(frozen=True)
class Visit:
    poi_id: str
    name: str
    category: str
    lat: float
    lon: float
    rating: float
    opening_hours: str
    arrival_time: str
    departure_time: str
    visit_minutes: float
    travel_from_previous_km: float
    travel_from_previous_minutes: float


@dataclass(frozen=True)
class DayPlan:
    day: int
    visits: List[Visit]
    route_length_km: float
    visit_minutes: float
    travel_minutes: float
    total_minutes: float
    skipped_poi_ids: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class TripPlan:
    plan_id: str
    city: str
    num_days: int
    source: str
    algorithm: Dict[str, str]
    days: List[DayPlan]
    total_pois: int
    total_route_length_km: float
    total_minutes: float
    created_at: str

    def to_dict(self) -> Dict:
        return asdict(self)
