"""SQLite persistence for product itinerary requests and results."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, Optional


class PlanRepository:
    """Persist complete request/result snapshots in a small SQLite database."""

    def __init__(self, database_path: Path | str = Path("data/planner.db")):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS trip_plans (
                    plan_id TEXT PRIMARY KEY,
                    city TEXT NOT NULL,
                    num_days INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_trip_plans_city_created "
                "ON trip_plans(city, created_at DESC)"
            )

    def save(self, request: Dict, result: Dict) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO trip_plans (
                    plan_id, city, num_days, source,
                    request_json, result_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result["plan_id"],
                    result["city"],
                    result["num_days"],
                    result["source"],
                    json.dumps(request, ensure_ascii=False),
                    json.dumps(result, ensure_ascii=False),
                    result["created_at"],
                ),
            )

    def get(self, plan_id: str) -> Optional[Dict]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT result_json FROM trip_plans WHERE plan_id = ?", (plan_id,)
            ).fetchone()
        return json.loads(row["result_json"]) if row else None
