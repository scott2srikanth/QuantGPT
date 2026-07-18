/*
# Create Strategy Research Engine Schema

## Overview
Creates the database tables for the QuantGPT Strategy Research Engine.
This is a single-tenant app (no sign-in), so all tables use anon+authenticated RLS.

## New Tables

1. `strategies` — Registry of all available strategies (built-in + plugins)
   - `id` (uuid PK)
   - `name` (text, unique) — slug identifier e.g. "momentum"
   - `display_name` (text) — human-readable name
   - `description` (text)
   - `type` (text) — strategy category: momentum, breakout, swing, trend_following, mean_reversion, volatility_expansion, portfolio_rotation, custom
   - `version` (text) — current semantic version e.g. "1.0.0"
   - `config_schema` (jsonb) — JSON schema describing configurable parameters
   - `default_config` (jsonb) — default parameter values
   - `is_active` (boolean, default true)
   - `is_plugin` (boolean, default false) — true for externally loaded plugins
   - `source` (text) — "builtin" or plugin module path
   - `created_at`, `updated_at` (timestamps)

2. `strategy_versions` — Versioned history of strategy code/config changes
   - `id` (uuid PK)
   - `strategy_id` (uuid FK → strategies)
   - `version` (text) — semantic version string
   - `config` (jsonb) — config snapshot at this version
   - `changelog` (text) — what changed in this version
   - `created_at` (timestamp)

3. `strategy_signals` — Signals produced by strategies (no live trading)
   - `id` (uuid PK)
   - `strategy_id` (uuid FK → strategies)
   - `symbol` (text) — stock symbol
   - `exchange` (text)
   - `signal_type` (text) — "buy", "sell", "hold"
   - `strength` (numeric, 0-100) — signal confidence
   - `price` (numeric) — price at signal time
   - `metadata` (jsonb) — extra signal data (indicators, reasons)
   - `created_at` (timestamp)

4. `backtest_results` — Backtest run results
   - `id` (uuid PK)
   - `strategy_id` (uuid FK → strategies)
   - `strategy_version` (text) — version used in backtest
   - `symbol` (text)
   - `exchange` (text)
   - `config` (jsonb) — config used
   - `start_date`, `end_date` (text) — backtest period
   - `initial_capital` (numeric)
   - `final_value` (numeric)
   - `total_return` (numeric) — percentage
   - `sharpe_ratio` (numeric)
   - `max_drawdown` (numeric) — percentage
   - `win_rate` (numeric) — percentage
   - `total_trades` (integer)
   - `winning_trades` (integer)
   - `losing_trades` (integer)
   - `avg_win` (numeric)
   - `avg_loss` (numeric)
   - `profit_factor` (numeric)
   - `benchmark_return` (numeric) — buy-and-hold return for comparison
   - `benchmark_sharpe` (numeric)
   - `outperformance` (numeric) — strategy return minus benchmark return
   - `equity_curve` (jsonb) — array of {date, value} points
   - `trade_history` (jsonb) — array of trade records
   - `created_at` (timestamp)

5. `marketplace_listings` — Strategy marketplace entries
   - `id` (uuid PK)
   - `strategy_id` (uuid FK → strategies)
   - `title` (text)
   - `description` (text)
   - `author` (text)
   - `tags` (jsonb) — array of tag strings
   - `rating` (numeric, default 0) — community rating 0-5
   - `downloads` (integer, default 0)
   - `is_featured` (boolean, default false)
   - `is_published` (boolean, default false)
   - `created_at`, `updated_at` (timestamps)

## Security
- RLS enabled on all tables.
- All tables allow anon + authenticated CRUD (single-tenant, shared data).
*/

-- ── strategies ──
CREATE TABLE IF NOT EXISTS strategies (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text UNIQUE NOT NULL,
    display_name text NOT NULL,
    description text NOT NULL DEFAULT '',
    type text NOT NULL DEFAULT 'custom',
    version text NOT NULL DEFAULT '1.0.0',
    config_schema jsonb NOT NULL DEFAULT '{}'::jsonb,
    default_config jsonb NOT NULL DEFAULT '{}'::jsonb,
    is_active boolean NOT NULL DEFAULT true,
    is_plugin boolean NOT NULL DEFAULT false,
    source text NOT NULL DEFAULT 'builtin',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE strategies ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_select_strategies" ON strategies;
CREATE POLICY "anon_select_strategies" ON strategies FOR SELECT
    TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_strategies" ON strategies;
CREATE POLICY "anon_insert_strategies" ON strategies FOR INSERT
    TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_update_strategies" ON strategies;
CREATE POLICY "anon_update_strategies" ON strategies FOR UPDATE
    TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon_delete_strategies" ON strategies;
CREATE POLICY "anon_delete_strategies" ON strategies FOR DELETE
    TO anon, authenticated USING (true);

-- ── strategy_versions ──
CREATE TABLE IF NOT EXISTS strategy_versions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id uuid NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    version text NOT NULL,
    config jsonb NOT NULL DEFAULT '{}'::jsonb,
    changelog text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(strategy_id, version)
);

ALTER TABLE strategy_versions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_select_strategy_versions" ON strategy_versions;
CREATE POLICY "anon_select_strategy_versions" ON strategy_versions FOR SELECT
    TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_strategy_versions" ON strategy_versions;
CREATE POLICY "anon_insert_strategy_versions" ON strategy_versions FOR INSERT
    TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_update_strategy_versions" ON strategy_versions;
CREATE POLICY "anon_update_strategy_versions" ON strategy_versions FOR UPDATE
    TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon_delete_strategy_versions" ON strategy_versions;
CREATE POLICY "anon_delete_strategy_versions" ON strategy_versions FOR DELETE
    TO anon, authenticated USING (true);

-- ── strategy_signals ──
CREATE TABLE IF NOT EXISTS strategy_signals (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id uuid NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    symbol text NOT NULL,
    exchange text NOT NULL DEFAULT 'NSE',
    signal_type text NOT NULL,
    strength numeric NOT NULL DEFAULT 50,
    price numeric,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE strategy_signals ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_select_strategy_signals" ON strategy_signals;
CREATE POLICY "anon_select_strategy_signals" ON strategy_signals FOR SELECT
    TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_strategy_signals" ON strategy_signals;
CREATE POLICY "anon_insert_strategy_signals" ON strategy_signals FOR INSERT
    TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_update_strategy_signals" ON strategy_signals;
CREATE POLICY "anon_update_strategy_signals" ON strategy_signals FOR UPDATE
    TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon_delete_strategy_signals" ON strategy_signals;
CREATE POLICY "anon_delete_strategy_signals" ON strategy_signals FOR DELETE
    TO anon, authenticated USING (true);

-- ── backtest_results ──
CREATE TABLE IF NOT EXISTS backtest_results (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id uuid NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    strategy_version text NOT NULL DEFAULT '1.0.0',
    symbol text NOT NULL,
    exchange text NOT NULL DEFAULT 'NSE',
    config jsonb NOT NULL DEFAULT '{}'::jsonb,
    start_date text,
    end_date text,
    initial_capital numeric NOT NULL DEFAULT 100000,
    final_value numeric,
    total_return numeric,
    sharpe_ratio numeric,
    max_drawdown numeric,
    win_rate numeric,
    total_trades integer NOT NULL DEFAULT 0,
    winning_trades integer NOT NULL DEFAULT 0,
    losing_trades integer NOT NULL DEFAULT 0,
    avg_win numeric,
    avg_loss numeric,
    profit_factor numeric,
    benchmark_return numeric,
    benchmark_sharpe numeric,
    outperformance numeric,
    equity_curve jsonb NOT NULL DEFAULT '[]'::jsonb,
    trade_history jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE backtest_results ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_select_backtest_results" ON backtest_results;
CREATE POLICY "anon_select_backtest_results" ON backtest_results FOR SELECT
    TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_backtest_results" ON backtest_results;
CREATE POLICY "anon_insert_backtest_results" ON backtest_results FOR INSERT
    TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_update_backtest_results" ON backtest_results;
CREATE POLICY "anon_update_backtest_results" ON backtest_results FOR UPDATE
    TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon_delete_backtest_results" ON backtest_results;
CREATE POLICY "anon_delete_backtest_results" ON backtest_results FOR DELETE
    TO anon, authenticated USING (true);

-- ── marketplace_listings ──
CREATE TABLE IF NOT EXISTS marketplace_listings (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id uuid NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    title text NOT NULL,
    description text NOT NULL DEFAULT '',
    author text NOT NULL DEFAULT '',
    tags jsonb NOT NULL DEFAULT '[]'::jsonb,
    rating numeric NOT NULL DEFAULT 0,
    downloads integer NOT NULL DEFAULT 0,
    is_featured boolean NOT NULL DEFAULT false,
    is_published boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE marketplace_listings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_select_marketplace_listings" ON marketplace_listings;
CREATE POLICY "anon_select_marketplace_listings" ON marketplace_listings FOR SELECT
    TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_marketplace_listings" ON marketplace_listings;
CREATE POLICY "anon_insert_marketplace_listings" ON marketplace_listings FOR INSERT
    TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_update_marketplace_listings" ON marketplace_listings;
CREATE POLICY "anon_update_marketplace_listings" ON marketplace_listings FOR UPDATE
    TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon_delete_marketplace_listings" ON marketplace_listings;
CREATE POLICY "anon_delete_marketplace_listings" ON marketplace_listings FOR DELETE
    TO anon, authenticated USING (true);

-- ── Indexes ──
CREATE INDEX IF NOT EXISTS idx_strategies_type ON strategies(type);
CREATE INDEX IF NOT EXISTS idx_strategies_active ON strategies(is_active);
CREATE INDEX IF NOT EXISTS idx_strategy_versions_strategy ON strategy_versions(strategy_id);
CREATE INDEX IF NOT EXISTS idx_strategy_signals_strategy ON strategy_signals(strategy_id);
CREATE INDEX IF NOT EXISTS idx_strategy_signals_symbol ON strategy_signals(symbol);
CREATE INDEX IF NOT EXISTS idx_backtest_results_strategy ON backtest_results(strategy_id);
CREATE INDEX IF NOT EXISTS idx_backtest_results_symbol ON backtest_results(symbol);
CREATE INDEX IF NOT EXISTS idx_marketplace_listings_published ON marketplace_listings(is_published);
CREATE INDEX IF NOT EXISTS idx_marketplace_listings_featured ON marketplace_listings(is_featured);