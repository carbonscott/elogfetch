-- Revised schema for elogfetch (PostgreSQL)
--
-- Changes from original_proposed.sql:
--   1. Fixed reversed FKs: experiment → pi, pi → user (not the other way around)
--   2. Replaced user.posix_group column with posix_group table + user_posix_group junction
--   3. Fixed type mismatches: run_id and detector_id FKs now TEXT to match their targets
--   4. run.run_number is UNIQUE(run_number, experiment_id), not globally unique
--   5. Merged runfiles into run_production_data (file_count, file_size_bytes)
--   6. workflow.run_num → workflow.run_id (FK to run.id) since run_number isn't globally unique
--   7. Added experiment_id to run_production_data, run_detector, workflow for RLS support
--   8. Made nullable columns explicit (description, timestamps, etc.)
--   9. Moved slack_channels and analysis_queues out of experiment into auxiliary tables
--      (slack_channel: at most one per experiment; analysis_queue: multiple per experiment)
--  10. Added PostgreSQL ENUMs for columns with fixed value sets:
--      workflow_trigger_type (workflowdefinition.trigger),
--      elog_content_type (logbook.content_type — also added missing column)


-- =============================================================================
-- ENUMs
-- =============================================================================

-- Values from WorkflowTrigger in api/gen/models.py.
-- Note: the API marks trigger as "WorkflowTrigger or free-form legacy value"
-- so ETL may need to handle unknown values gracefully.
CREATE TYPE workflow_trigger_type AS ENUM (
    'MANUAL',
    'START_OF_RUN',
    'END_OF_RUN',
    'FIRST_FILE_TRANSFERRED',
    'ALL_FILES_TRANSFERRED',
    'ALL_NONREC_FILES_TRANSFERRED',
    'RUN_PARAM_IS_VALUE'
);

-- Values from ElogContentType in api/gen/models.py.
CREATE TYPE elog_content_type AS ENUM (
    'TEXT',
    'HTML',
    'MARKDOWN'
);


-- =============================================================================
-- Independent lookup / reference tables (no FKs to other tables)
-- =============================================================================

CREATE TABLE IF NOT EXISTS "user" (
    "id" TEXT NOT NULL,                         -- Linux username (e.g. "swelborn")
    PRIMARY KEY("id")
);


CREATE TABLE IF NOT EXISTS "posix_group" (
    "name" TEXT NOT NULL,                       -- e.g. "ps-xpp", "ps-mfx"
    PRIMARY KEY("name")
);


CREATE TABLE IF NOT EXISTS "detector" (
    "id" TEXT NOT NULL,                         -- e.g. "DAQ Detectors/Rayonix"
    "name" TEXT NOT NULL UNIQUE,
    "description" TEXT,
    PRIMARY KEY("id")
);


CREATE TABLE IF NOT EXISTS "metadata" (
    "key" TEXT NOT NULL,
    "value" TEXT,
    PRIMARY KEY("key")
);


-- =============================================================================
-- PI extends user with contact info
-- =============================================================================

CREATE TABLE IF NOT EXISTS "pi" (
    "id" TEXT NOT NULL,                         -- FK to user.id
    "name" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    PRIMARY KEY("id"),
    FOREIGN KEY("id") REFERENCES "user"("id")
);


-- =============================================================================
-- Junction: users ↔ posix_groups (many-to-many)
-- =============================================================================

CREATE TABLE IF NOT EXISTS "user_posix_group" (
    "user_id" TEXT NOT NULL,
    "posix_group_name" TEXT NOT NULL,
    PRIMARY KEY("user_id", "posix_group_name"),
    FOREIGN KEY("user_id") REFERENCES "user"("id"),
    FOREIGN KEY("posix_group_name") REFERENCES "posix_group"("name")
);


-- =============================================================================
-- Experiment (central entity)
-- =============================================================================

CREATE TABLE IF NOT EXISTS "experiment" (
    "experiment_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "instrument" TEXT NOT NULL,
    "start_time" TIMESTAMPTZ NOT NULL,
    "end_time" TIMESTAMPTZ NOT NULL,
    "pi_id" TEXT NOT NULL,                      -- FK to pi.id (single PI per experiment)
    "leader_account" TEXT NOT NULL,
    "posix_group" TEXT NOT NULL,                -- FK to posix_group.name
    "description" TEXT,
    PRIMARY KEY("experiment_id"),
    FOREIGN KEY("pi_id") REFERENCES "pi"("id"),
    FOREIGN KEY("posix_group") REFERENCES "posix_group"("name")
);


-- =============================================================================
-- Experiment auxiliary tables (operational config, extensible)
-- =============================================================================

CREATE TABLE IF NOT EXISTS "experiment_slack_channel" (
    "experiment_id" TEXT NOT NULL,              -- at most one channel per experiment
    "channel" TEXT NOT NULL,                    -- e.g. "#xpp-elog"
    PRIMARY KEY("experiment_id"),
    FOREIGN KEY("experiment_id") REFERENCES "experiment"("experiment_id")
);


CREATE TABLE IF NOT EXISTS "experiment_analysis_queue" (
    "experiment_id" TEXT NOT NULL,              -- space-separated in source, normalized here
    "queue" TEXT NOT NULL,                      -- e.g. "ffbh2q"
    PRIMARY KEY("experiment_id", "queue"),
    FOREIGN KEY("experiment_id") REFERENCES "experiment"("experiment_id")
);


-- =============================================================================
-- Questionnaire fields (per experiment)
-- =============================================================================

CREATE TABLE IF NOT EXISTS "questionnaire" (
    "questionnaire_id" BIGSERIAL,
    "experiment_id" TEXT NOT NULL,
    "proposal" TEXT,
    "category" TEXT NOT NULL,
    "field_id" TEXT NOT NULL,
    "field_name" TEXT,
    "field_value" TEXT,
    "modified_time" TIMESTAMPTZ,
    "modified_uid" TEXT,
    "created_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY("questionnaire_id"),
    UNIQUE("experiment_id", "field_id"),
    FOREIGN KEY("experiment_id") REFERENCES "experiment"("experiment_id")
);


-- =============================================================================
-- Workflow definitions (templates, per experiment)
-- =============================================================================

CREATE TABLE IF NOT EXISTS "workflowdefinition" (
    "id" TEXT NOT NULL,
    "experiment_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "executable" TEXT NOT NULL,
    "trigger" workflow_trigger_type NOT NULL,
    "location" TEXT NOT NULL,
    "parameters" JSONB,                         -- workflow parameter dict
    "run_param_name" TEXT,
    "run_param_value" TEXT,
    "run_as_user" TEXT,
    PRIMARY KEY("id"),
    FOREIGN KEY("experiment_id") REFERENCES "experiment"("experiment_id")
);


-- =============================================================================
-- Runs (per experiment)
-- =============================================================================

CREATE TABLE IF NOT EXISTS "run" (
    "id" TEXT NOT NULL,                         -- MongoDB ObjectId (e.g. "68040f4f84929222f10ffef4")
    "run_number" INTEGER NOT NULL,
    "experiment_id" TEXT NOT NULL,
    "start_time" TIMESTAMPTZ,
    "end_time" TIMESTAMPTZ,
    PRIMARY KEY("id"),
    UNIQUE("run_number", "experiment_id"),      -- run_number is unique per experiment, not globally
    FOREIGN KEY("experiment_id") REFERENCES "experiment"("experiment_id")
);


-- =============================================================================
-- Run production data + file stats (1:1 with run, merged from runfiles)
-- =============================================================================

CREATE TABLE IF NOT EXISTS "run_production_data" (
    "run_id" TEXT NOT NULL,                     -- FK to run.id (TEXT, not INTEGER)
    "experiment_id" TEXT NOT NULL,              -- denormalized for RLS
    "n_events" BIGINT,
    "n_damaged" BIGINT,
    "n_dropped" BIGINT,
    "start_timestamp" TIMESTAMPTZ,
    "end_timestamp" TIMESTAMPTZ,
    "file_count" BIGINT,                        -- merged from runfiles.count
    "file_size_bytes" BIGINT,                   -- merged from runfiles.size
    PRIMARY KEY("run_id"),
    FOREIGN KEY("run_id") REFERENCES "run"("id"),
    FOREIGN KEY("experiment_id") REFERENCES "experiment"("experiment_id")
);


-- =============================================================================
-- Run ↔ Detector junction (with status value)
-- =============================================================================

CREATE TABLE IF NOT EXISTS "run_detector" (
    "run_id" TEXT NOT NULL,                     -- FK to run.id (TEXT)
    "detector_id" TEXT NOT NULL,                -- FK to detector.id (TEXT)
    "experiment_id" TEXT NOT NULL,              -- denormalized for RLS
    "value" TEXT NOT NULL,
    PRIMARY KEY("run_id", "detector_id"),
    FOREIGN KEY("run_id") REFERENCES "run"("id"),
    FOREIGN KEY("detector_id") REFERENCES "detector"("id"),
    FOREIGN KEY("experiment_id") REFERENCES "experiment"("experiment_id")
);


-- =============================================================================
-- Logbook entries
-- =============================================================================

CREATE TABLE IF NOT EXISTS "logbook" (
    "id" TEXT NOT NULL,
    "experiment_id" TEXT NOT NULL,
    "run_id" TEXT,                              -- nullable: not all entries are tied to a run
    "created_time" TIMESTAMPTZ NOT NULL,
    "content" TEXT,
    "content_type" elog_content_type NOT NULL DEFAULT 'TEXT',
    "tags" TEXT[],                              -- PostgreSQL array
    "author" TEXT NOT NULL,
    PRIMARY KEY("id"),
    FOREIGN KEY("experiment_id") REFERENCES "experiment"("experiment_id"),
    FOREIGN KEY("run_id") REFERENCES "run"("id")
);


-- =============================================================================
-- Workflow executions (job runs, references a definition)
-- =============================================================================

CREATE TABLE IF NOT EXISTS "workflow" (
    "id" TEXT NOT NULL,
    "experiment_id" TEXT NOT NULL,              -- denormalized for RLS
    "run_id" TEXT NOT NULL,                     -- FK to run.id (replaces run_num since run_number isn't globally unique)
    "def_id" TEXT NOT NULL,                     -- FK to workflowdefinition.id
    "user_id" TEXT NOT NULL,                     -- FK to user.id
    "status" TEXT NOT NULL,
    "submit_time" TIMESTAMPTZ NOT NULL,
    "tool_id" BIGINT,
    "log_file_path" TEXT,
    PRIMARY KEY("id"),
    FOREIGN KEY("experiment_id") REFERENCES "experiment"("experiment_id"),
    FOREIGN KEY("run_id") REFERENCES "run"("id"),
    FOREIGN KEY("def_id") REFERENCES "workflowdefinition"("id"),
    FOREIGN KEY("user_id") REFERENCES "user"("id")
);


-- =============================================================================
-- Indexes
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_questionnaire_experiment ON "questionnaire"("experiment_id");
CREATE INDEX IF NOT EXISTS idx_run_experiment ON "run"("experiment_id");
CREATE INDEX IF NOT EXISTS idx_run_production_data_experiment ON "run_production_data"("experiment_id");
CREATE INDEX IF NOT EXISTS idx_run_detector_experiment ON "run_detector"("experiment_id");
CREATE INDEX IF NOT EXISTS idx_logbook_experiment ON "logbook"("experiment_id");
CREATE INDEX IF NOT EXISTS idx_logbook_run ON "logbook"("run_id");
CREATE INDEX IF NOT EXISTS idx_workflow_experiment ON "workflow"("experiment_id");
CREATE INDEX IF NOT EXISTS idx_workflow_def ON "workflow"("def_id");
CREATE INDEX IF NOT EXISTS idx_workflowdefinition_experiment ON "workflowdefinition"("experiment_id");
