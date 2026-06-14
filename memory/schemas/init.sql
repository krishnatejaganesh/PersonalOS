-- PersonalOS Database Schema
-- This file runs automatically on first start.
-- Safe to re-run — all tables use IF NOT EXISTS.

-- ─────────────────────────────────────────────────────────────
-- Users / Identity
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_profile (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    timezone        TEXT NOT NULL DEFAULT 'UTC',
    location        TEXT,
    language        TEXT NOT NULL DEFAULT 'English',
    persona         TEXT NOT NULL DEFAULT 'default',
    preferences     JSONB NOT NULL DEFAULT '{}',
    -- preferences example:
    -- {"communication_style": "brief", "report_format": "bullets",
    --  "urgent_threshold": "high", "businesses": ["pdf-tools", "restaurant"]}
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- Memory — what the agents remember about you
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS memories (
    id              SERIAL PRIMARY KEY,
    memory_type     TEXT NOT NULL,   -- 'fact' | 'preference' | 'relationship' | 'business' | 'context'
    key             TEXT NOT NULL,   -- short label, e.g. 'pdf_site_stack'
    value           TEXT NOT NULL,   -- the actual memory content
    source          TEXT,            -- where this came from: 'user_stated' | 'inferred' | 'observed'
    confidence      FLOAT NOT NULL DEFAULT 1.0,  -- 0.0–1.0
    last_used       TIMESTAMPTZ,
    use_count       INT NOT NULL DEFAULT 0,
    tags            TEXT[] NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_memories_key ON memories(key);

-- ─────────────────────────────────────────────────────────────
-- Conversations — full history
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS conversations (
    id              SERIAL PRIMARY KEY,
    session_id      UUID NOT NULL DEFAULT gen_random_uuid(),
    agent           TEXT NOT NULL DEFAULT 'chief-of-staff',
    source          TEXT NOT NULL DEFAULT 'telegram',   -- 'telegram' | 'desktop' | 'api' | 'cron'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    metadata        JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS messages (
    id              SERIAL PRIMARY KEY,
    conversation_id INT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,   -- 'user' | 'assistant' | 'system' | 'tool'
    content         TEXT NOT NULL,
    tool_calls      JSONB,           -- tool invocations if role='assistant'
    tool_results    JSONB,           -- results if role='tool'
    model           TEXT,            -- which model generated this message
    tokens_used     INT,
    cost_usd        NUMERIC(10, 6),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);

-- ─────────────────────────────────────────────────────────────
-- Tasks — everything the agents do
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS tasks (
    id              SERIAL PRIMARY KEY,
    task_id         UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    task_type       TEXT NOT NULL,   -- 'morning_briefing' | 'email_reply' | 'code_fix' | etc.
    agent           TEXT NOT NULL,
    source          TEXT NOT NULL,   -- 'cron' | 'user' | 'subagent'
    status          TEXT NOT NULL DEFAULT 'pending',
    -- 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
    input           JSONB NOT NULL DEFAULT '{}',
    output          TEXT,
    steps           JSONB,           -- the actual tool calls made, in order
    error           TEXT,
    model           TEXT,
    tokens_used     INT NOT NULL DEFAULT 0,
    cost_usd        NUMERIC(10, 6) NOT NULL DEFAULT 0,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(task_type);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_agent ON tasks(agent);

-- ─────────────────────────────────────────────────────────────
-- Workflow Outcomes — the self-improving loop
-- ─────────────────────────────────────────────────────────────
-- After every completed task, the evaluator scores the outcome
-- and saves it here. Future tasks of the same type load the
-- best-scoring workflow as their starting plan.

CREATE TABLE IF NOT EXISTS workflow_outcomes (
    id              SERIAL PRIMARY KEY,
    task_type       TEXT NOT NULL,
    task_input      JSONB,           -- what was requested (for similarity matching)
    steps           JSONB NOT NULL,  -- exact sequence of tool calls that worked
    outcome         TEXT,            -- what happened (natural language summary)
    score           FLOAT NOT NULL,  -- 0.0–1.0 (set by evaluator agent)
    reuse           BOOLEAN NOT NULL DEFAULT true,
    times_reused    INT NOT NULL DEFAULT 0,
    last_reused     TIMESTAMPTZ,
    notes           TEXT,            -- evaluator's reasoning
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workflow_type_score ON workflow_outcomes(task_type, score DESC);
CREATE INDEX IF NOT EXISTS idx_workflow_reuse ON workflow_outcomes(reuse, task_type);

-- ─────────────────────────────────────────────────────────────
-- Skills — reusable task templates
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS skills (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    description     TEXT NOT NULL,
    agent           TEXT,            -- which agent this skill belongs to (NULL = any)
    trigger_words   TEXT[],          -- words that activate this skill
    prompt_template TEXT NOT NULL,   -- the prompt, with {{placeholders}}
    tools_required  TEXT[],          -- tool names needed
    model_override  TEXT,            -- force a specific model for this skill
    enabled         BOOLEAN NOT NULL DEFAULT true,
    use_count       INT NOT NULL DEFAULT 0,
    avg_score       FLOAT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- Scheduled Jobs
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    description     TEXT,
    cron_expression TEXT NOT NULL,   -- standard cron format
    task_type       TEXT NOT NULL,
    agent           TEXT NOT NULL,
    payload         JSONB NOT NULL DEFAULT '{}',
    enabled         BOOLEAN NOT NULL DEFAULT true,
    last_run        TIMESTAMPTZ,
    last_status     TEXT,
    next_run        TIMESTAMPTZ,
    run_count       INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Insert default jobs (matching .env.example defaults)
INSERT INTO scheduled_jobs (name, description, cron_expression, task_type, agent, payload) VALUES
(
    'morning-briefing',
    'Daily morning summary: emails, calendar, priorities, market insights',
    '0 8 * * 1-5',
    'morning_briefing',
    'chief-of-staff',
    '{"notify": "telegram", "include": ["emails", "calendar", "priorities", "news"]}'
),
(
    'midday-check',
    'Check for urgent items since the morning briefing',
    '0 12 * * *',
    'urgent_check',
    'chief-of-staff',
    '{"notify": "telegram", "only_if_urgent": true}'
),
(
    'evening-wrap',
    'End of day summary: unanswered urgent items, day summary',
    '0 19 * * *',
    'evening_wrap',
    'chief-of-staff',
    '{"notify": "telegram"}'
),
(
    'weekly-review',
    'Weekly model benchmarks, workflow performance report, model swap suggestions',
    '0 9 * * 0',
    'weekly_review',
    'chief-of-staff',
    '{"notify": "telegram", "include": ["model_benchmarks", "workflow_performance", "cost_report"]}'
)
ON CONFLICT (name) DO NOTHING;

-- ─────────────────────────────────────────────────────────────
-- Model Performance — tracks benchmark results over time
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS model_benchmarks (
    id              SERIAL PRIMARY KEY,
    model           TEXT NOT NULL,
    benchmark_date  DATE NOT NULL DEFAULT CURRENT_DATE,
    task_category   TEXT NOT NULL,   -- 'coding' | 'writing' | 'research' | 'reasoning'
    score           FLOAT NOT NULL,  -- 0.0–1.0 normalised
    latency_ms      INT,
    cost_per_1k     NUMERIC(10, 6),
    notes           TEXT,
    source          TEXT NOT NULL DEFAULT 'internal',  -- 'internal' | 'external'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (model, benchmark_date, task_category)
);

-- ─────────────────────────────────────────────────────────────
-- Cost Tracking
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS cost_summary (
    id              SERIAL PRIMARY KEY,
    period          DATE NOT NULL,   -- first day of the period
    period_type     TEXT NOT NULL,   -- 'daily' | 'weekly' | 'monthly'
    model           TEXT NOT NULL,
    task_type       TEXT,
    total_tokens    BIGINT NOT NULL DEFAULT 0,
    total_cost_usd  NUMERIC(10, 4) NOT NULL DEFAULT 0,
    task_count      INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (period, period_type, model, task_type)
);

-- ─────────────────────────────────────────────────────────────
-- Useful views
-- ─────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW v_best_workflows AS
SELECT
    task_type,
    steps,
    score,
    outcome,
    times_reused,
    created_at
FROM workflow_outcomes
WHERE reuse = true AND score >= 0.75
ORDER BY task_type, score DESC;

CREATE OR REPLACE VIEW v_today_tasks AS
SELECT
    task_id,
    task_type,
    agent,
    status,
    cost_usd,
    created_at,
    completed_at,
    EXTRACT(EPOCH FROM (completed_at - started_at)) AS duration_seconds
FROM tasks
WHERE created_at >= CURRENT_DATE
ORDER BY created_at DESC;

CREATE OR REPLACE VIEW v_cost_this_month AS
SELECT
    model,
    SUM(total_tokens) AS tokens,
    SUM(total_cost_usd) AS cost_usd,
    SUM(task_count) AS tasks
FROM cost_summary
WHERE period_type = 'daily'
  AND period >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY model
ORDER BY cost_usd DESC;
