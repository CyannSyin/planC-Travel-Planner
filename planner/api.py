"""HTTP API for the PlanC web application.

The API deliberately keeps OpenAI credentials and planner execution on the
server. Conversation state is held per browser session; complete generated
plans are still persisted through ``PlanRepository``.
"""

from __future__ import annotations

import os
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Callable, Dict, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent import OpenAIIntentInterpreter, TravelAgent
from .storage import PlanRepository


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: Optional[str] = Field(default=None, max_length=100)


class ResetRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)


@dataclass
class AgentSession:
    agent: TravelAgent
    lock: RLock = field(default_factory=RLock)


class SessionStore:
    """Small bounded in-memory store for conversational planner instances."""

    def __init__(
        self,
        agent_factory: Callable[[], TravelAgent],
        max_sessions: int = 100,
    ) -> None:
        self.agent_factory = agent_factory
        self.max_sessions = max_sessions
        self._sessions: "OrderedDict[str, AgentSession]" = OrderedDict()
        self._lock = RLock()

    def get_or_create(self, session_id: Optional[str]) -> tuple[str, AgentSession]:
        with self._lock:
            if session_id and session_id in self._sessions:
                session = self._sessions.pop(session_id)
                self._sessions[session_id] = session
                return session_id, session

            resolved_id = str(uuid4())
            session = AgentSession(agent=self.agent_factory())
            self._sessions[resolved_id] = session
            while len(self._sessions) > self.max_sessions:
                self._sessions.popitem(last=False)
            return resolved_id, session

    def remove(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None


def _allowed_origins() -> list[str]:
    configured = os.getenv("FRONTEND_ORIGINS", "")
    origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
    return origins or [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def create_app(
    agent_factory: Optional[Callable[[], TravelAgent]] = None,
) -> FastAPI:
    repository = PlanRepository(Path(os.getenv("PLANC_DATABASE", "data/planner.db")))

    def default_agent_factory() -> TravelAgent:
        return TravelAgent(
            interpreter=OpenAIIntentInterpreter(),
            repository=repository,
        )

    sessions = SessionStore(agent_factory or default_agent_factory)
    app = FastAPI(title="PlanC API", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health")
    def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/chat")
    def chat(request: ChatRequest) -> Dict:
        message = request.message.strip()
        if not message:
            raise HTTPException(status_code=422, detail="message cannot be empty")

        try:
            session_id, session = sessions.get_or_create(request.session_id)
            with session.lock:
                turn = session.agent.respond(message)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(
                status_code=503,
                detail=f"旅行规划服务暂时不可用：{error}",
            ) from error

        return {"session_id": session_id, "turn": turn.to_dict()}

    @app.post("/api/reset")
    def reset(request: ResetRequest) -> Dict[str, bool]:
        return {"reset": sessions.remove(request.session_id)}

    return app


app = create_app()
