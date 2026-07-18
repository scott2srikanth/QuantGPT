-- QuantGPT PostgreSQL init
-- Extensions enabled by default for the quantgpt database.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";        -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";       -- uuid_generate_v4()
CREATE EXTENSION IF NOT EXISTS "citext";          -- case-insensitive text (emails)

-- sane defaults
ALTER DATABASE "quantgpt" SET timezone TO 'UTC';
ALTER DATABASE "quantgpt" SET statement_timeout TO '30000';     -- 30s
ALTER DATABASE "quantgpt" SET lock_timeout TO '5000';           -- 5s
ALTER DATABASE "quantgpt" SET log_min_duration_statement TO '500';
