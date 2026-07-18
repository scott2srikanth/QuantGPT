# Multi-Agent Framework

The QuantGPT multi-agent framework is a production-quality architecture for orchestrating specialized AI agents that collaborate on trading intelligence. Every agent exposes a uniform interface, communicates via a durable message bus, and persists state (memory, history, metrics, health) to Supabase.

This document describes the architecture, components, agent interface, and how to add new agents.

## Architecture

```
┌──────────────────────────── QuantGPT ────────────────────────────┐
│                                                                 │
│   API router  ──►  AgentManager  ──►  AgentRegistry  ──►  Agents │
│                        │                                         │
│            ┌───────────┼───────────┬───────────┐                 │
│            ▼           ▼           ▼           ▼                 │
│       TaskQueue   MessageBus   Scheduler   HealthTracker          │
│            │           │                                       │
│            └─────┬─────┘                                       │
│                  ▼                                               │
│             Supabase (agents, tasks, messages, agent_memory,     │
│             agent_history, agent_metrics, agent_health)          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Design principles

1. **Uniform interface.** Every agent exposes `run()`, `status()`, `metrics()`, `health()`, `config()`, `memory()`, `history()`. Callers never need to know an agent's internals.
2. **Durable persistence.** All state (tasks, messages, memory, history, metrics, health) lives in Supabase — not in process memory — so it survives restarts and is shared across instances.
3. **Placeholder-first.** All 15 agents are placeholders with a uniform stub `execute()`. Implementation comes later without changing the framework.
4. **Retry with backoff.** `run()` retries `execute()` up to `max_attempts` with exponential backoff. Non-retryable exceptions fail fast.
5. **Observable.** Every run records history, metrics, and health. The manager surfaces system-wide status.

## Module map

```
backend/app/agents/
├── __init__.py
├── exceptions.py          # AgentError, AgentNotFoundError, TaskExecutionError, etc.
├── schemas.py             # Pydantic API schemas (AgentStatus, TaskOut, MessageOut, etc.)
├── base.py                # AgentBase — abstract base with run/status/metrics/health/config/memory/history
├── registry.py            # AgentRegistry — name -> agent instance map
├── manager.py             # AgentManager — orchestrates queue, bus, dispatch, system health
├── scheduler.py           # Scheduler — background thread that drains queue + delivers messages
├── task_queue.py          # TaskQueue — durable priority queue with retries
├── message_bus.py         # MessageBus — durable pub/sub for inter-agent communication
├── memory.py              # Memory — per-agent key/value store
├── history.py             # HistoryStore — execution history per agent run
├── metrics.py             # MetricsStore — rolling numeric metrics per agent
├── health.py              # HealthTracker — agent health snapshots
├── factory.py             # build_agent_framework() — composition root
└── agents/
    └── __init__.py        # 15 placeholder agent classes + ALL_AGENT_CLASSES
```

## Database schema

All tables live in Supabase with RLS enabled (single-tenant: `TO anon, authenticated`).

| Table | Purpose |
|---|---|
| `agents` | Registered agents (id, name, type, status, config) |
| `tasks` | Task queue (agent_id, payload, status, priority, attempts, max_attempts, scheduled_for) |
| `messages` | Inter-agent message bus (from_agent_id, to_agent_id, topic, payload, delivered) |
| `agent_memory` | Per-agent key/value memory (agent_id, key, value) — unique on (agent_id, key) |
| `agent_history` | Execution history (agent_id, run_id, status, result, duration_ms, error) |
| `agent_metrics` | Rolling metrics (agent_id, metric, value, recorded_at) |
| `agent_health` | Health snapshots (agent_id, status, detail, checked_at) |

## The uniform agent interface

Every agent extends `AgentBase` and exposes these 8 methods:

| Method | Returns | Description |
|---|---|---|
| `run(payload)` | `{run_id, status, result, duration_ms, attempts}` | Execute the agent with retry + history/metrics/health recording |
| `status()` | `{name, type, status, running}` | Current lifecycle status (idle/running/error) |
| `metrics()` | `{metric: value}` | Latest numeric metrics (latency, attempts, errors) |
| `health()` | `{name, status, detail, checked_at}` | Latest health snapshot (healthy/degraded/unhealthy) |
| `config()` | `{name, type, config}` | The agent's configuration dict |
| `memory()` | `{key: value}` | The agent's persisted key/value memory |
| `history(limit)` | `list[AgentHistory]` | Recent execution history rows |
| `execute(payload)` | `dict` | **Abstract** — concrete agents implement this |

### Retry logic

`run()` calls `execute()` up to `max_attempts` times with exponential backoff (1s, 2s, 4s, ... max 10s):
- **Retryable:** any `Exception` except `TaskMaxAttemptsExceededError`
- **Non-retryable:** `TaskMaxAttemptsExceededError` (fails immediately)
- On exhaustion: raises `TaskMaxAttemptsExceededError`, records failed history, sets status to `error`, health to `unhealthy`

### Logging

Every agent logs via `structlog` with logger `agent.{name}`. The base class logs run start/complete/attempt_failed/exhausted. The manager logs registration, task enqueue/failed, and scheduler ticks.

## Core components

### AgentRegistry (`registry.py`)
In-memory map of agent name → `AgentBase` instance. Single source of truth for which agents exist. Raises on duplicate registration or missing lookup.

### AgentManager (`manager.py`)
Operational entrypoint. Wires the registry, task queue, message bus, and health tracker. Provides:
- `register(agent)` — persist agent row + register in registry
- `enqueue_task(agent_name, payload, priority, max_attempts, scheduled_for)` — add to queue
- `run_agent(agent_name, payload)` — run immediately (bypasses queue)
- `drain(limit)` — claim + execute pending tasks
- `send_message(from, to, topic, payload)` — inter-agent messaging
- `deliver_messages(limit)` — deliver pending messages to agents (stored in receiver's memory)
- `system_health()` — aggregate health across all agents
- `all_status()`, `all_health()`, `all_metrics()` — bulk views

### TaskQueue (`task_queue.py`)
Durable priority queue. Tasks are addressed to an agent, carry a JSON payload, and have a retry budget. `dequeue()` claims the highest-priority due task and marks it running. `mark_failed()` increments attempts and either re-queues (pending) or marks failed when exhausted.

### Scheduler (`scheduler.py`)
Background daemon thread that ticks at a configurable interval. Each tick: delivers pending messages, then drains up to N tasks. Stopppable and idempotent. Exposes `tick()` for manual/testing triggers.

### MessageBus (`message_bus.py`)
Durable pub/sub. Messages are addressed to a specific agent (`to_agent_id`) or broadcast on a topic (`to_agent_id = null`). Messages persist until delivered, so agents communicate across runs and restarts.

### Memory (`memory.py`)
Per-agent key/value store. Used for state that must survive across runs (learned parameters, last-seen values, received messages). Unique on `(agent_id, key)`.

### History (`history.py`)
Records every `run()` invocation with status, result, duration, and error. Used for audit, debugging, and the self-evaluation agent.

### Metrics (`metrics.py`)
Rolling numeric metrics per agent. `record()` appends; `latest()` returns the most recent value per metric; `summary()` returns avg/min/max/count over a time window.

### Health (`health.py`)
Persists health snapshots (healthy/degraded/unhealthy). The manager aggregates these for system-wide health. Agents can override `check_health()` to report custom status.

## The 15 placeholder agents

All defined in `app/agents/agents/__init__.py`. Each is a thin subclass of `_PlaceholderAgent` with a `name`, `type`, and stub `execute()`.

| Agent | Name | Type |
|---|---|---|
| Market Scanner | `market_scanner` | scanner |
| Technical Analysis | `technical_analysis` | analysis |
| Fundamental Analysis | `fundamental_analysis` | analysis |
| News | `news` | information |
| Risk | `risk` | risk |
| Portfolio | `portfolio` | portfolio |
| Strategy | `strategy` | strategy |
| Trade Decision | `trade_decision` | decision |
| Backtesting | `backtesting` | backtesting |
| Prediction | `prediction` | prediction |
| Self Evaluation | `self_evaluation` | evaluation |
| Reporting | `reporting` | reporting |
| Trade Journal | `trade_journal` | journal |
| Monitoring | `monitoring` | monitoring |
| Alerting | `alerting` | alerting |

Each placeholder `execute()` returns:
```json
{"agent": "<name>", "type": "<type>", "status": "placeholder", "message": "<name> is a placeholder — not yet implemented", "payload": {...}}
```

## API surface

All endpoints under `/api/v1/agents`:

| Method | Path | Description |
|---|---|---|
| GET | `/agents` | List all agent statuses |
| GET | `/agents/health` | System-wide agent health |
| GET | `/agents/{name}` | Agent status |
| POST | `/agents/{name}/run` | Run an agent immediately |
| GET | `/agents/{name}/metrics` | Agent metrics |
| GET | `/agents/{name}/health` | Agent health |
| GET | `/agents/{name}/config` | Agent config |
| GET | `/agents/{name}/memory` | Agent memory |
| GET | `/agents/{name}/history` | Agent execution history |
| POST | `/agents/tasks` | Enqueue a task |
| GET | `/agents/tasks/pending` | Pending task count |
| POST | `/agents/messages` | Send a message between agents |

## Usage

### From code

```python
from app.core.container import get_container

container = get_container()
manager = container.agent_manager

# list agents
statuses = manager.all_status()

# run immediately
result = manager.run_agent("market_scanner", {"symbol": "RELIANCE", "exchange": "NSE"})
print(result["status"], result["result"])

# enqueue a task (executed by the scheduler)
manager.enqueue_task("risk", {"check": "volatility"}, priority=5)

# send a message
manager.send_message(from_agent_name="news", to_agent_name="risk", topic="alert", payload={"msg": "earnings"})

# system health
health = manager.system_health()
print(health["healthy"], health["unhealthy"], health["pending_tasks"])
```

### From the API

```bash
# list agents
curl localhost:8000/api/v1/agents

# run an agent
curl -X POST localhost:8000/api/v1/agents/market_scanner/run \
  -H "Content-Type: application/json" \
  -d '{"payload": {"symbol": "RELIANCE"}}'

# enqueue a task
curl -X POST localhost:8000/api/v1/agents/tasks \
  -H "Content-Type: application/json" \
  -d '{"agent_name": "risk", "payload": {"check": "vol"}, "priority": 5}'

# system health
curl localhost:8000/api/v1/agents/health
```

## Adding a new agent

1. **Create the class.** Subclass `AgentBase` (or `_PlaceholderAgent`), set `name` and `type`, implement `execute(payload)`:

```python
# app/agents/agents/my_agent.py
from app.agents.agents import _PlaceholderAgent

class MyAgent(_PlaceholderAgent):
    name = "my_agent"
    type = "custom"

    def execute(self, payload):
        # real implementation here
        return {"result": "done", "input": payload}
```

2. **Register it.** Add the class to `ALL_AGENT_CLASSES` in `app/agents/agents/__init__.py`. The factory will automatically persist an agent row and register it at startup.

3. **That's it.** The agent now exposes `run/status/metrics/health/config/memory/history` and is available via the manager and API. No other code changes needed.

## Configuration

Environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `AGENT_SCHEDULER_INTERVAL_SECONDS` | `5.0` | Scheduler tick interval |
| `AGENT_TASK_MAX_ATTEMPTS` | `3` | Default retry budget per task |
| `AGENT_HEALTH_CHECK_INTERVAL_SECONDS` | `60.0` | Health check interval |
| `AGENT_HISTORY_RETENTION_DAYS` | `30` | History retention window |
| `AGENT_MESSAGE_BATCH_SIZE` | `50` | Messages delivered per tick |

## Testing

```bash
cd quantgpt/backend
pytest tests/ -v
```

47 agent framework tests (109 total with the Integration Layer), all passing. Tests use an in-memory SQLite database so they never touch Supabase. Coverage:

| Test file | Covers |
|---|---|
| `test_agent_memory.py` | Memory get/set/delete/all/clear/per-agent isolation |
| `test_agent_task_queue.py` | Queue enqueue/dequeue/priority/completion/retry-until-max/cancel/pending-count |
| `test_agent_message_bus.py` | Bus publish/consume/delivered-flag/broadcast-topic/pending-count |
| `test_agent_stores.py` | Health record/latest/all-latest; Metrics record/latest/summary; History record/list/latest |
| `test_agent_base.py` | run success, status, config, memory, history, metrics, health, retry-then-succeed, retry-exhausted, unhealthy-after-failure |
| `test_agent_manager.py` | Registry register/duplicate/missing; factory registers all 15; uniform interface; run-immediate; enqueue+drain; send+deliver message; system health; scheduler tick |
| `test_placeholder_agents.py` | All 15 present; each runs; each returns status |
