"""Agent framework API router.

Exposes the uniform agent interface over HTTP:
  GET    /agents                 — list all agents
  GET    /agents/{name}         — agent status
  POST   /agents/{name}/run     — run an agent immediately
  GET    /agents/{name}/metrics — agent metrics
  GET    /agents/{name}/health  — agent health
  GET    /agents/{name}/config  — agent config
  GET    /agents/{name}/memory  — agent memory
  GET    /agents/{name}/history — agent execution history
  POST   /tasks                 — enqueue a task
  GET    /tasks/pending         — pending task count
  POST   /messages              — send a message between agents
  GET    /health                — system-wide agent health
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agents.schemas import (
    AgentHistoryOut,
    AgentMetricsOut,
    AgentMemoryOut,
    AgentRunRequest,
    AgentStatus,
    MessageCreate,
    MessageOut,
    TaskCreate,
    TaskOut,
)
from app.db.session import get_db
from app.logging.config import get_logger

router = APIRouter(prefix="/agents", tags=["agents"])
_log = get_logger("api.agents")


def _get_manager(db: Session = Depends(get_db)):
    # The manager is built per-request from the DB session. In a production
    # deployment this would be a cached singleton keyed by the DB session.
    from app.core.container import get_agent_manager

    return get_agent_manager(db)


@router.get("", response_model=list[AgentStatus])
def list_agents(manager=Depends(_get_manager)):
    return [AgentStatus(**s) for s in manager.all_status()]


@router.get("/health")
def system_health(manager=Depends(_get_manager)):
    return manager.system_health()


@router.get("/{name}", response_model=AgentStatus)
def agent_status(name: str, manager=Depends(_get_manager)):
    try:
        return AgentStatus(**manager.get(name).status())
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"agent '{name}' not found")


@router.post("/{name}/run")
def run_agent(name: str, req: AgentRunRequest, manager=Depends(_get_manager)):
    try:
        return manager.run_agent(name, req.payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{name}/metrics", response_model=AgentMetricsOut)
def agent_metrics(name: str, manager=Depends(_get_manager)):
    try:
        return AgentMetricsOut(name=name, metrics=manager.get(name).metrics())
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"agent '{name}' not found")


@router.get("/{name}/health")
def agent_health(name: str, manager=Depends(_get_manager)):
    try:
        return manager.get(name).health()
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"agent '{name}' not found")


@router.get("/{name}/config")
def agent_config(name: str, manager=Depends(_get_manager)):
    try:
        return manager.get(name).config()
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"agent '{name}' not found")


@router.get("/{name}/memory", response_model=AgentMemoryOut)
def agent_memory(name: str, manager=Depends(_get_manager)):
    try:
        return AgentMemoryOut(name=name, memory=manager.get(name).memory())
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"agent '{name}' not found")


@router.get("/{name}/history", response_model=list[AgentHistoryOut])
def agent_history(name: str, manager=Depends(_get_manager)):
    try:
        rows = manager.get(name).history(limit=50)
        return [AgentHistoryOut.model_validate(r, from_attributes=True) for r in rows]
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"agent '{name}' not found")


@router.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(req: TaskCreate, manager=Depends(_get_manager)):
    try:
        task_id = manager.enqueue_task(
            req.agent_name,
            req.payload,
            priority=req.priority,
            max_attempts=req.max_attempts,
            scheduled_for=req.scheduled_for,
        )
        # return a minimal task out
        return {"id": task_id, "agent_id": uuid.uuid4(), "agent_name": req.agent_name, "payload": req.payload, "status": "pending", "priority": req.priority, "attempts": 0, "max_attempts": req.max_attempts, "last_error": None, "created_at": None}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/tasks/pending")
def pending_tasks(manager=Depends(_get_manager)):
    return {"pending": manager._queue.pending_count()}


@router.post("/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_message(req: MessageCreate, manager=Depends(_get_manager)):
    try:
        msg_id = manager.send_message(
            from_agent_name=req.from_agent_name,
            to_agent_name=req.to_agent_name,
            topic=req.topic,
            payload=req.payload,
        )
        return {"id": msg_id, "from_agent_name": req.from_agent_name, "to_agent_name": req.to_agent_name, "topic": req.topic, "payload": req.payload, "delivered": False, "created_at": None, "delivered_at": None}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
