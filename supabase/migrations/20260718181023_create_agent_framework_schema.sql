/*
# Create Multi-Agent Framework Schema (single-tenant, no auth)

1. Purpose
   Persistence layer for the QuantGPT multi-agent framework. Stores agent
   registrations, the task queue, inter-agent messages, per-agent memory,
   execution history, metrics, and health snapshots. Single-tenant: the app
   has no sign-in screen, so all policies allow anon + authenticated CRUD
   (the data is intentionally shared within the single QuantGPT instance).

2. New Tables
   - `agents`            — registered agents (id, name, type, status, config)
   - `tasks`             — task queue (id, agent_id, payload, status, attempts)
   - `messages`          — inter-agent message bus (from, to, topic, payload)
   - `agent_memory`      — per-agent key/value memory (agent_id, key, value)
   - `agent_history`     — execution history per agent run (agent_id, run_id, result)
   - `agent_metrics`     — rolling metrics per agent (agent_id, metric, value)
   - `agent_health`      — health snapshots per agent (agent_id, status, detail)

3. Security
   - RLS enabled on every table.
   - All tables allow anon + authenticated CRUD (single-tenant, shared data).

4. Important Notes
   - All tables use `gen_random_uuid()` for ids.
   - Timestamps are `timestamptz DEFAULT now()`.
   - `tasks.status` constrained to pending|running|completed|failed|cancelled.
   - `agent_health.status` constrained to healthy|degraded|unhealthy.
   - Indexes on agent_id and status columns for query performance.
   - Idempotent: uses IF NOT EXISTS and DROP POLICY IF EXISTS.
*/

-- ── agents ──
CREATE TABLE IF NOT EXISTS agents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL UNIQUE,
  type text NOT NULL,
  status text NOT NULL DEFAULT 'idle',
  config jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_select_agents" ON agents;
CREATE POLICY "anon_select_agents" ON agents FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS "anon_insert_agents" ON agents;
CREATE POLICY "anon_insert_agents" ON agents FOR INSERT TO anon, authenticated WITH CHECK (true);
DROP POLICY IF EXISTS "anon_update_agents" ON agents;
CREATE POLICY "anon_update_agents" ON agents FOR UPDATE TO anon, authenticated USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS "anon_delete_agents" ON agents;
CREATE POLICY "anon_delete_agents" ON agents FOR DELETE TO anon, authenticated USING (true);
CREATE INDEX IF NOT EXISTS ix_agents_type ON agents(type);
CREATE INDEX IF NOT EXISTS ix_agents_status ON agents(status);

-- ── tasks ──
CREATE TABLE IF NOT EXISTS tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id uuid NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'pending',
  priority int NOT NULL DEFAULT 0,
  attempts int NOT NULL DEFAULT 0,
  max_attempts int NOT NULL DEFAULT 3,
  last_error text,
  scheduled_for timestamptz NOT NULL DEFAULT now(),
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT tasks_status_chk CHECK (status IN ('pending','running','completed','failed','cancelled'))
);
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_select_tasks" ON tasks;
CREATE POLICY "anon_select_tasks" ON tasks FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS "anon_insert_tasks" ON tasks;
CREATE POLICY "anon_insert_tasks" ON tasks FOR INSERT TO anon, authenticated WITH CHECK (true);
DROP POLICY IF EXISTS "anon_update_tasks" ON tasks;
CREATE POLICY "anon_update_tasks" ON tasks FOR UPDATE TO anon, authenticated USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS "anon_delete_tasks" ON tasks;
CREATE POLICY "anon_delete_tasks" ON tasks FOR DELETE TO anon, authenticated USING (true);
CREATE INDEX IF NOT EXISTS ix_tasks_agent_id ON tasks(agent_id);
CREATE INDEX IF NOT EXISTS ix_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS ix_tasks_scheduled_for ON tasks(scheduled_for);

-- ── messages ──
CREATE TABLE IF NOT EXISTS messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  from_agent_id uuid REFERENCES agents(id) ON DELETE SET NULL,
  to_agent_id uuid REFERENCES agents(id) ON DELETE SET NULL,
  topic text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  delivered boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  delivered_at timestamptz
);
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_select_messages" ON messages;
CREATE POLICY "anon_select_messages" ON messages FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS "anon_insert_messages" ON messages;
CREATE POLICY "anon_insert_messages" ON messages FOR INSERT TO anon, authenticated WITH CHECK (true);
DROP POLICY IF EXISTS "anon_update_messages" ON messages;
CREATE POLICY "anon_update_messages" ON messages FOR UPDATE TO anon, authenticated USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS "anon_delete_messages" ON messages;
CREATE POLICY "anon_delete_messages" ON messages FOR DELETE TO anon, authenticated USING (true);
CREATE INDEX IF NOT EXISTS ix_messages_to_agent ON messages(to_agent_id);
CREATE INDEX IF NOT EXISTS ix_messages_topic ON messages(topic);
CREATE INDEX IF NOT EXISTS ix_messages_delivered ON messages(delivered);

-- ── agent_memory ──
CREATE TABLE IF NOT EXISTS agent_memory (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id uuid NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  key text NOT NULL,
  value jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (agent_id, key)
);
ALTER TABLE agent_memory ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_select_agent_memory" ON agent_memory;
CREATE POLICY "anon_select_agent_memory" ON agent_memory FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS "anon_insert_agent_memory" ON agent_memory;
CREATE POLICY "anon_insert_agent_memory" ON agent_memory FOR INSERT TO anon, authenticated WITH CHECK (true);
DROP POLICY IF EXISTS "anon_update_agent_memory" ON agent_memory;
CREATE POLICY "anon_update_agent_memory" ON agent_memory FOR UPDATE TO anon, authenticated USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS "anon_delete_agent_memory" ON agent_memory;
CREATE POLICY "anon_delete_agent_memory" ON agent_memory FOR DELETE TO anon, authenticated USING (true);
CREATE INDEX IF NOT EXISTS ix_agent_memory_agent_id ON agent_memory(agent_id);

-- ── agent_history ──
CREATE TABLE IF NOT EXISTS agent_history (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id uuid NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  run_id uuid NOT NULL DEFAULT gen_random_uuid(),
  status text NOT NULL,
  result jsonb NOT NULL DEFAULT '{}'::jsonb,
  duration_ms int,
  error text,
  started_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);
ALTER TABLE agent_history ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_select_agent_history" ON agent_history;
CREATE POLICY "anon_select_agent_history" ON agent_history FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS "anon_insert_agent_history" ON agent_history;
CREATE POLICY "anon_insert_agent_history" ON agent_history FOR INSERT TO anon, authenticated WITH CHECK (true);
DROP POLICY IF EXISTS "anon_update_agent_history" ON agent_history;
CREATE POLICY "anon_update_agent_history" ON agent_history FOR UPDATE TO anon, authenticated USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS "anon_delete_agent_history" ON agent_history;
CREATE POLICY "anon_delete_agent_history" ON agent_history FOR DELETE TO anon, authenticated USING (true);
CREATE INDEX IF NOT EXISTS ix_agent_history_agent_id ON agent_history(agent_id);
CREATE INDEX IF NOT EXISTS ix_agent_history_run_id ON agent_history(run_id);
CREATE INDEX IF NOT EXISTS ix_agent_history_started_at ON agent_history(started_at);

-- ── agent_metrics ──
CREATE TABLE IF NOT EXISTS agent_metrics (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id uuid NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  metric text NOT NULL,
  value numeric NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE agent_metrics ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_select_agent_metrics" ON agent_metrics;
CREATE POLICY "anon_select_agent_metrics" ON agent_metrics FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS "anon_insert_agent_metrics" ON agent_metrics;
CREATE POLICY "anon_insert_agent_metrics" ON agent_metrics FOR INSERT TO anon, authenticated WITH CHECK (true);
DROP POLICY IF EXISTS "anon_update_agent_metrics" ON agent_metrics;
CREATE POLICY "anon_update_agent_metrics" ON agent_metrics FOR UPDATE TO anon, authenticated USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS "anon_delete_agent_metrics" ON agent_metrics;
CREATE POLICY "anon_delete_agent_metrics" ON agent_metrics FOR DELETE TO anon, authenticated USING (true);
CREATE INDEX IF NOT EXISTS ix_agent_metrics_agent_id ON agent_metrics(agent_id);
CREATE INDEX IF NOT EXISTS ix_agent_metrics_metric ON agent_metrics(metric);
CREATE INDEX IF NOT EXISTS ix_agent_metrics_recorded_at ON agent_metrics(recorded_at);

-- ── agent_health ──
CREATE TABLE IF NOT EXISTS agent_health (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id uuid NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  status text NOT NULL DEFAULT 'healthy',
  detail text,
  checked_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT agent_health_status_chk CHECK (status IN ('healthy','degraded','unhealthy'))
);
ALTER TABLE agent_health ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_select_agent_health" ON agent_health;
CREATE POLICY "anon_select_agent_health" ON agent_health FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS "anon_insert_agent_health" ON agent_health;
CREATE POLICY "anon_insert_agent_health" ON agent_health FOR INSERT TO anon, authenticated WITH CHECK (true);
DROP POLICY IF EXISTS "anon_update_agent_health" ON agent_health;
CREATE POLICY "anon_update_agent_health" ON agent_health FOR UPDATE TO anon, authenticated USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS "anon_delete_agent_health" ON agent_health;
CREATE POLICY "anon_delete_agent_health" ON agent_health FOR DELETE TO anon, authenticated USING (true);
CREATE INDEX IF NOT EXISTS ix_agent_health_agent_id ON agent_health(agent_id);
CREATE INDEX IF NOT EXISTS ix_agent_health_checked_at ON agent_health(checked_at);
