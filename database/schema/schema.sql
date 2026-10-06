-- X-SENTINEL V3 canonical schema reference for Microsoft SQL Server (T-SQL).
-- DO NOT apply this file manually in normal development. Alembic migrations are authoritative.
-- Revision head: 0002_v3_jev_ai_audit

CREATE TABLE users (
  id uniqueidentifier PRIMARY KEY,
  email nvarchar(320) NOT NULL,
  normalized_email nvarchar(320) NOT NULL UNIQUE,
  display_name nvarchar(200) NULL,
  is_active bit NOT NULL DEFAULT 1,
  created_at datetimeoffset NOT NULL DEFAULT sysdatetimeoffset(),
  updated_at datetimeoffset NOT NULL DEFAULT sysdatetimeoffset()
);

CREATE TABLE roles (
  id int IDENTITY(1,1) PRIMARY KEY,
  code nvarchar(64) NOT NULL UNIQUE,
  description nvarchar(255) NULL
);

CREATE TABLE user_roles (
  user_id uniqueidentifier NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id int NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  assigned_at datetimeoffset NOT NULL DEFAULT sysdatetimeoffset(),
  PRIMARY KEY (user_id, role_id)
);

CREATE TABLE model_versions (
  id uniqueidentifier PRIMARY KEY,
  name nvarchar(120) NOT NULL,
  version nvarchar(120) NOT NULL,
  sha256 varchar(64) NOT NULL,
  config_hash varchar(64) NOT NULL,
  metadata_json nvarchar(max) NOT NULL DEFAULT N'{}',
  is_active bit NOT NULL DEFAULT 0,
  created_at datetimeoffset NOT NULL DEFAULT sysdatetimeoffset(),
  CONSTRAINT uq_model_versions_name_version UNIQUE (name, version)
);

CREATE TABLE analysis_jobs (
  id uniqueidentifier PRIMARY KEY,
  request_id nvarchar(128) NOT NULL UNIQUE,
  user_id uniqueidentifier NULL REFERENCES users(id) ON DELETE SET NULL,
  model_version_id uniqueidentifier NULL REFERENCES model_versions(id) ON DELETE SET NULL,
  status nvarchar(32) NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','completed','failed','quarantined')),
  input_mode nvarchar(32) NOT NULL DEFAULT 'vector' CHECK (input_mode IN ('vector','raw_pe')),
  input_sha256 varchar(64) NULL,
  input_artifact_uri nvarchar(max) NULL,
  config_version nvarchar(128) NULL,
  demo_mode bit NOT NULL DEFAULT 1,
  error_code nvarchar(128) NULL,
  error_message nvarchar(max) NULL,
  created_at datetimeoffset NOT NULL DEFAULT sysdatetimeoffset(),
  started_at datetimeoffset NULL,
  completed_at datetimeoffset NULL
);

CREATE TABLE analysis_results (
  analysis_job_id uniqueidentifier PRIMARY KEY REFERENCES analysis_jobs(id) ON DELETE CASCADE,
  malware_score float NULL,
  suspicion_score float NULL,
  threshold float NULL,
  decision nvarchar(32) NOT NULL DEFAULT 'unknown' CHECK (decision IN ('unknown','pass','alert','quarantine')),
  latency_ms float NULL,
  view_contributions nvarchar(max) NOT NULL DEFAULT N'{}',
  result_json nvarchar(max) NOT NULL DEFAULT N'{}',
  evidence_uri nvarchar(max) NULL,
  created_at datetimeoffset NOT NULL DEFAULT sysdatetimeoffset()
);

CREATE TABLE detector_scores (
  analysis_job_id uniqueidentifier NOT NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE,
  detector_code nvarchar(16) NOT NULL CHECK (detector_code IN ('M1','M2','M3','M4','M5')),
  score float NOT NULL,
  diagnostics nvarchar(max) NOT NULL DEFAULT N'{}',
  created_at datetimeoffset NOT NULL DEFAULT sysdatetimeoffset(),
  PRIMARY KEY (analysis_job_id, detector_code)
);

CREATE TABLE alerts (
  id uniqueidentifier PRIMARY KEY,
  analysis_job_id uniqueidentifier NOT NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE,
  severity nvarchar(16) NOT NULL DEFAULT 'medium' CHECK (severity IN ('low','medium','high','critical')),
  status nvarchar(32) NOT NULL DEFAULT 'open' CHECK (status IN ('open','acknowledged','resolved','dismissed')),
  reason nvarchar(max) NOT NULL,
  created_at datetimeoffset NOT NULL DEFAULT sysdatetimeoffset(),
  resolved_at datetimeoffset NULL
);

CREATE TABLE artifacts (
  id uniqueidentifier PRIMARY KEY,
  analysis_job_id uniqueidentifier NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE,
  kind nvarchar(64) NOT NULL,
  uri nvarchar(max) NOT NULL,
  sha256 varchar(64) NOT NULL,
  content_type nvarchar(255) NULL,
  size_bytes bigint NULL,
  metadata_json nvarchar(max) NOT NULL DEFAULT N'{}',
  created_at datetimeoffset NOT NULL DEFAULT sysdatetimeoffset()
);

CREATE TABLE audit_events (
  id bigint IDENTITY(1,1) PRIMARY KEY,
  request_id nvarchar(128) NULL,
  user_id uniqueidentifier NULL REFERENCES users(id) ON DELETE SET NULL,
  event_type nvarchar(128) NOT NULL,
  entity_type nvarchar(64) NULL,
  entity_id nvarchar(128) NULL,
  payload nvarchar(max) NOT NULL DEFAULT N'{}',
  created_at datetimeoffset NOT NULL DEFAULT sysdatetimeoffset()
);

CREATE TABLE experiment_runs (
  id uniqueidentifier PRIMARY KEY,
  created_by_user_id uniqueidentifier NULL REFERENCES users(id) ON DELETE SET NULL,
  experiment_code nvarchar(16) NOT NULL CHECK (experiment_code IN ('E0','E1','E2','E3','E4','E5')),
  status nvarchar(32) NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','running','completed','failed')),
  config_hash varchar(64) NOT NULL,
  seed int NULL,
  results_uri nvarchar(max) NULL,
  metrics_json nvarchar(max) NOT NULL DEFAULT N'{}',
  created_at datetimeoffset NOT NULL DEFAULT sysdatetimeoffset(),
  completed_at datetimeoffset NULL
);

-- Blind ground-truth/manifest data is intentionally absent from this application schema.

-- V3 optional local Jev AI advisory audit tables.
CREATE TABLE jev_ai_runs (
  id uniqueidentifier PRIMARY KEY,
  analysis_job_id uniqueidentifier NULL REFERENCES analysis_jobs(id) ON DELETE SET NULL,
  requested_by_user_id uniqueidentifier NULL REFERENCES users(id) ON DELETE SET NULL,
  mode nvarchar(32) NOT NULL CHECK (mode IN ('explain','triage','compare','report','docs')),
  status nvarchar(32) NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','completed','failed','blocked')),
  model_id nvarchar(255) NOT NULL,
  endpoint_label nvarchar(120) NOT NULL DEFAULT 'lm_studio_local',
  prompt_version nvarchar(120) NOT NULL,
  input_digest_sha256 varchar(64) NOT NULL,
  output_digest_sha256 varchar(64) NULL,
  context_summary nvarchar(max) NOT NULL DEFAULT N'{}',
  response_text nvarchar(max) NULL,
  latency_ms float NULL,
  error_code nvarchar(128) NULL,
  error_message nvarchar(max) NULL,
  created_at datetimeoffset NOT NULL DEFAULT sysdatetimeoffset(),
  completed_at datetimeoffset NULL
);

CREATE TABLE jev_ai_feedback (
  id uniqueidentifier PRIMARY KEY,
  jev_ai_run_id uniqueidentifier NOT NULL REFERENCES jev_ai_runs(id) ON DELETE CASCADE,
  user_id uniqueidentifier NULL REFERENCES users(id) ON DELETE SET NULL,
  rating int CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5)),
  label nvarchar(32) CHECK (label IS NULL OR label IN ('helpful','not_helpful','incorrect','unsafe','unclear')),
  comment nvarchar(max) NULL,
  created_at datetimeoffset NOT NULL DEFAULT sysdatetimeoffset()
);

-- Jev AI Indexes (matching 0002_v3_jev_ai_audit migration)
CREATE INDEX ix_jev_ai_runs_analysis_job_id ON jev_ai_runs (analysis_job_id);
CREATE INDEX ix_jev_ai_runs_requested_by_user_id ON jev_ai_runs (requested_by_user_id);
CREATE INDEX ix_jev_ai_runs_mode ON jev_ai_runs (mode);
CREATE INDEX ix_jev_ai_runs_status ON jev_ai_runs (status);
CREATE INDEX ix_jev_ai_runs_input_digest_sha256 ON jev_ai_runs (input_digest_sha256);
CREATE INDEX ix_jev_ai_runs_output_digest_sha256 ON jev_ai_runs (output_digest_sha256);
CREATE INDEX ix_jev_ai_runs_created_at ON jev_ai_runs (created_at);
CREATE INDEX ix_jev_ai_runs_analysis_created ON jev_ai_runs (analysis_job_id, created_at);

CREATE INDEX ix_jev_ai_feedback_jev_ai_run_id ON jev_ai_feedback (jev_ai_run_id);
CREATE INDEX ix_jev_ai_feedback_user_id ON jev_ai_feedback (user_id);
