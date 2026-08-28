"""Conversational, AI-native orchestration for the travel planner.

The language model owns intent understanding and dialogue. The existing
planner remains a deterministic tool for geography, routing, and scheduling.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

import pandas as pd
from dotenv import load_dotenv

from .models import PlanRequest, TripPlan
from .product import create_trip_plan
from .storage import PlanRepository


load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@dataclass(frozen=True)
class TravelIntent:
    """The durable user constraints carried between conversation turns."""

    city: Optional[str] = None
    num_days: Optional[int] = None
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

    def missing_fields(self) -> List[str]:
        missing = []
        if not self.city:
            missing.append("city")
        if self.num_days is None:
            missing.append("num_days")
        return missing

    def to_plan_request(self) -> PlanRequest:
        if self.missing_fields():
            raise ValueError("city and num_days are required before planning")
        return PlanRequest(
            city=self.city or "",
            num_days=int(self.num_days or 0),
            source=self.source,
            preferences=self.preferences,
            budget=self.budget,
            interests=list(self.interests),
            max_pois=max(self.max_pois, int(self.num_days)) if self.max_pois else None,
            min_rating=self.min_rating,
            max_daily_hours=self.max_daily_hours,
            start_time=self.start_time,
            walking_speed_kmh=self.walking_speed_kmh,
            poi_file=self.poi_file,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IntentInterpretation:
    intent: TravelIntent
    summary: str
    question: Optional[str] = None


class IntentInterpreter(Protocol):
    def interpret(
        self, message: str, current_intent: Optional[TravelIntent]
    ) -> IntentInterpretation:
        """Merge a user message into the current durable travel intent."""


INTENT_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "city": {"type": ["string", "null"]},
        "num_days": {"type": ["integer", "null"], "minimum": 1, "maximum": 14},
        "source": {"type": "string", "enum": ["llm", "osm"]},
        "preferences": {"type": ["string", "null"]},
        "budget": {"type": ["string", "null"]},
        "interests": {"type": "array", "items": {"type": "string"}},
        "max_pois": {"type": ["integer", "null"], "minimum": 1},
        "min_rating": {"type": "number", "minimum": 0, "maximum": 5},
        "max_daily_hours": {"type": "number", "minimum": 2, "maximum": 16},
        "start_time": {"type": "string", "pattern": "^(?:[01]\\d|2[0-3]):[0-5]\\d$"},
        "walking_speed_kmh": {"type": "number", "exclusiveMinimum": 0},
        "poi_file": {"type": ["string", "null"]},
        "summary": {"type": "string"},
        "question": {"type": ["string", "null"]},
    },
    "required": [
        "city",
        "num_days",
        "source",
        "preferences",
        "budget",
        "interests",
        "max_pois",
        "min_rating",
        "max_daily_hours",
        "start_time",
        "walking_speed_kmh",
        "poi_file",
        "summary",
        "question",
    ],
}


AGENT_INSTRUCTIONS = """You are PlanC, a warm and practical travel planning assistant.

Your job is to merge the latest user message into the durable travel constraints.
Return the complete updated state, not a patch.

Rules:
- Preserve existing values unless the user changes or removes them.
- Extract explicit constraints faithfully. Put nuanced requests that do not have a
  dedicated field into preferences as a concise cumulative description.
- Infer ordinary defaults only from the supplied current state. Never invent a city,
  trip length, budget, or POI file.
- A slower desired pace may reduce max_daily_hours or walking_speed_kmh only when the
  user clearly asks for it; otherwise capture it in preferences.
- city and num_days are the only mandatory fields. If either is missing, ask one short
  question for the missing information. Otherwise question must be null.
- summary briefly states what you understood or changed, in the user's language.
- Use HH:MM for start_time.
"""


class OpenAIIntentInterpreter:
    """Use the Responses API with Structured Outputs to understand each turn."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        try:
            from openai import OpenAI
        except (ImportError, AttributeError) as error:
            raise RuntimeError(
                "The AI-native CLI requires openai>=1.68.0. "
                "Run: pip install -r requirements.txt"
            ) from error

        provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
        if provider == "aihubmix":
            resolved_key = api_key or os.getenv("AIHUBMIX_API_KEY") or os.getenv("OPENAI_API_KEY")
        else:
            resolved_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("AIHUBMIX_API_KEY")
        if not resolved_key:
            raise ValueError("OPENAI_API_KEY or AIHUBMIX_API_KEY is required")
        resolved_base_url = base_url or os.getenv("OPENAI_BASE_URL")
        if provider == "aihubmix" and not resolved_base_url:
            raise ValueError("OPENAI_BASE_URL is required when LLM_PROVIDER=aihubmix")
        client_kwargs: Dict[str, Any] = {"api_key": resolved_key}
        if resolved_base_url:
            client_kwargs["base_url"] = resolved_base_url
        self.client = OpenAI(**client_kwargs)
        self.model = model or os.getenv("AGENT_MODEL") or os.getenv("LLM_MODEL", "gpt-4o-mini")

    def interpret(
        self, message: str, current_intent: Optional[TravelIntent]
    ) -> IntentInterpretation:
        current = current_intent or TravelIntent()
        response = self.client.responses.create(
            model=self.model,
            instructions=AGENT_INSTRUCTIONS,
            input=(
                "Current durable constraints:\n"
                f"{json.dumps(current.to_dict(), ensure_ascii=False)}\n\n"
                f"Latest user message:\n{message}"
            ),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "travel_intent",
                    "strict": True,
                    "schema": INTENT_JSON_SCHEMA,
                }
            },
        )
        payload = json.loads(response.output_text)
        summary = str(payload.pop("summary"))
        question = payload.pop("question")
        intent = TravelIntent(**payload)

        missing = intent.missing_fields()
        if missing and not question:
            labels = {"city": "目的地", "num_days": "旅行天数"}
            question = f"请告诉我{ '和'.join(labels[item] for item in missing) }。"
        return IntentInterpretation(intent=intent, summary=summary, question=question)


@dataclass(frozen=True)
class AgentTurn:
    status: str
    message: str
    intent: TravelIntent
    plan: Optional[TripPlan] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "intent": self.intent.to_dict(),
            "plan": self.plan.to_dict() if self.plan else None,
        }


class TravelAgent:
    """Maintain dialogue state and call the deterministic planner as a tool."""

    def __init__(
        self,
        interpreter: IntentInterpreter,
        repository: Optional[PlanRepository] = None,
        pois: Optional[pd.DataFrame] = None,
    ):
        self.interpreter = interpreter
        self.repository = repository
        self.pois = pois
        self.intent: Optional[TravelIntent] = None
        self.plan: Optional[TripPlan] = None

    def reset(self) -> None:
        self.intent = None
        self.plan = None

    def respond(self, message: str) -> AgentTurn:
        if not message.strip():
            raise ValueError("message cannot be empty")

        previous = self.intent
        interpretation = self.interpreter.interpret(message, previous)
        self.intent = interpretation.intent
        missing = self.intent.missing_fields()
        if missing:
            return AgentTurn(
                status="needs_input",
                message=interpretation.question or interpretation.summary,
                intent=self.intent,
            )

        request = self.intent.to_plan_request()
        request.validate()
        plan = create_trip_plan(request, pois=self.pois, repository=self.repository)
        self.plan = plan
        action = "已重新规划" if previous is not None else "已生成行程"
        message_text = (
            f"{interpretation.summary}\n{action}：{plan.city} {plan.num_days} 天，"
            f"共安排 {plan.total_pois} 个地点，预计路线 {plan.total_route_length_km:.1f} 公里，"
            f"总计 {plan.total_minutes / 60:.1f} 小时。"
        )
        return AgentTurn(status="planned", message=message_text, intent=self.intent, plan=plan)
