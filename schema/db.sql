-- PostgreSQL schema for elogfetch
-- Auto-generated from SQLModel metadata via scripts/gen_ddl.py
-- DO NOT EDIT MANUALLY — run `make schema` to regenerate.
--
-- Design decisions are documented in the migration files under
-- src/elogfetch/alembic/versions/.

-- ENUMs
CREATE TYPE workflow_trigger_type AS ENUM ('MANUAL', 'START_OF_RUN', 'END_OF_RUN', 'FIRST_FILE_TRANSFERRED', 'ALL_FILES_TRANSFERRED', 'ALL_NONREC_FILES_TRANSFERRED', 'RUN_PARAM_IS_VALUE');
CREATE TYPE elog_content_type AS ENUM ('TEXT', 'HTML', 'MARKDOWN');


CREATE TABLE detector (
	id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	description VARCHAR, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE posix_group (
	name VARCHAR NOT NULL, 
	PRIMARY KEY (name)
);

CREATE TABLE "user" (
	id VARCHAR NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE workflowdefinition (
	id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	executable VARCHAR NOT NULL, 
	trigger workflow_trigger_type NOT NULL, 
	location VARCHAR NOT NULL, 
	parameters VARCHAR, 
	run_param_name VARCHAR, 
	run_param_value VARCHAR, 
	run_as_user VARCHAR, 
	PRIMARY KEY (id)
);

CREATE TABLE pi (
	id VARCHAR NOT NULL, 
	name VARCHAR, 
	email VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(id) REFERENCES "user" (id) ON DELETE CASCADE
);

CREATE TABLE user_posix_group (
	user_id VARCHAR NOT NULL, 
	posix_group_name VARCHAR NOT NULL, 
	PRIMARY KEY (user_id, posix_group_name), 
	FOREIGN KEY(user_id) REFERENCES "user" (id) ON DELETE CASCADE, 
	FOREIGN KEY(posix_group_name) REFERENCES posix_group (name) ON DELETE CASCADE
);

CREATE TABLE experiment (
	experiment_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	instrument VARCHAR NOT NULL, 
	start_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	end_time TIMESTAMP WITH TIME ZONE, 
	pi_id VARCHAR NOT NULL, 
	leader_account VARCHAR NOT NULL, 
	posix_group VARCHAR NOT NULL, 
	description VARCHAR, 
	fetched_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (experiment_id), 
	FOREIGN KEY(pi_id) REFERENCES pi (id), 
	FOREIGN KEY(posix_group) REFERENCES posix_group (name)
);
CREATE INDEX ix_experiment_pi_id ON experiment (pi_id);

CREATE TABLE experiment_analysis_queue (
	experiment_id VARCHAR NOT NULL, 
	queue VARCHAR NOT NULL, 
	PRIMARY KEY (experiment_id, queue), 
	FOREIGN KEY(experiment_id) REFERENCES experiment (experiment_id) ON DELETE CASCADE
);

CREATE TABLE experiment_slack_channel (
	experiment_id VARCHAR NOT NULL, 
	channel VARCHAR NOT NULL, 
	PRIMARY KEY (experiment_id), 
	FOREIGN KEY(experiment_id) REFERENCES experiment (experiment_id) ON DELETE CASCADE
);

CREATE TABLE questionnaire (
	questionnaire_id BIGSERIAL NOT NULL, 
	experiment_id VARCHAR NOT NULL, 
	proposal VARCHAR, 
	category VARCHAR NOT NULL, 
	field_id VARCHAR NOT NULL, 
	field_name VARCHAR, 
	field_value VARCHAR, 
	modified_time TIMESTAMP WITH TIME ZONE, 
	modified_uid VARCHAR, 
	created_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (questionnaire_id), 
	CONSTRAINT uq_questionnaire_exp_field UNIQUE (experiment_id, field_id), 
	FOREIGN KEY(experiment_id) REFERENCES experiment (experiment_id) ON DELETE CASCADE
);
CREATE INDEX ix_questionnaire_experiment_id ON questionnaire (experiment_id);

CREATE TABLE run (
	id VARCHAR NOT NULL, 
	run_number INTEGER NOT NULL, 
	experiment_id VARCHAR NOT NULL, 
	start_time TIMESTAMP WITH TIME ZONE, 
	end_time TIMESTAMP WITH TIME ZONE, 
	fetched_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_run_number_exp UNIQUE (run_number, experiment_id), 
	FOREIGN KEY(experiment_id) REFERENCES experiment (experiment_id) ON DELETE CASCADE
);
CREATE INDEX ix_run_experiment_id ON run (experiment_id);

CREATE TABLE logbook (
	id VARCHAR NOT NULL, 
	experiment_id VARCHAR NOT NULL, 
	run_id VARCHAR, 
	created_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	content VARCHAR, 
	content_type elog_content_type NOT NULL, 
	tags VARCHAR[], 
	author VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(experiment_id) REFERENCES experiment (experiment_id) ON DELETE CASCADE, 
	FOREIGN KEY(run_id) REFERENCES run (id) ON DELETE SET NULL
);
CREATE INDEX ix_logbook_run_id ON logbook (run_id);
CREATE INDEX ix_logbook_experiment_id ON logbook (experiment_id);

CREATE TABLE run_detector (
	run_id VARCHAR NOT NULL, 
	detector_id VARCHAR NOT NULL, 
	experiment_id VARCHAR NOT NULL, 
	value VARCHAR NOT NULL, 
	PRIMARY KEY (run_id, detector_id), 
	FOREIGN KEY(run_id) REFERENCES run (id) ON DELETE CASCADE, 
	FOREIGN KEY(detector_id) REFERENCES detector (id) ON DELETE RESTRICT, 
	FOREIGN KEY(experiment_id) REFERENCES experiment (experiment_id) ON DELETE CASCADE
);
CREATE INDEX ix_run_detector_detector_id ON run_detector (detector_id);
CREATE INDEX ix_run_detector_experiment_id ON run_detector (experiment_id);

CREATE TABLE run_production_data (
	run_id VARCHAR NOT NULL, 
	experiment_id VARCHAR NOT NULL, 
	n_events BIGINT, 
	n_damaged BIGINT, 
	n_dropped BIGINT, 
	start_timestamp TIMESTAMP WITH TIME ZONE, 
	end_timestamp TIMESTAMP WITH TIME ZONE, 
	file_count BIGINT, 
	file_size_bytes BIGINT, 
	PRIMARY KEY (run_id), 
	FOREIGN KEY(run_id) REFERENCES run (id) ON DELETE CASCADE, 
	FOREIGN KEY(experiment_id) REFERENCES experiment (experiment_id) ON DELETE CASCADE
);
CREATE INDEX ix_run_production_data_experiment_id ON run_production_data (experiment_id);

CREATE TABLE workflow (
	id VARCHAR NOT NULL, 
	experiment_id VARCHAR NOT NULL, 
	run_id VARCHAR NOT NULL, 
	def_id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	submit_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	tool_id BIGINT, 
	log_file_path VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(experiment_id) REFERENCES experiment (experiment_id) ON DELETE CASCADE, 
	FOREIGN KEY(run_id) REFERENCES run (id) ON DELETE RESTRICT, 
	FOREIGN KEY(def_id) REFERENCES workflowdefinition (id) ON DELETE RESTRICT, 
	FOREIGN KEY(user_id) REFERENCES "user" (id) ON DELETE RESTRICT
);
CREATE INDEX ix_workflow_run_id ON workflow (run_id);
CREATE INDEX ix_workflow_user_id ON workflow (user_id);
CREATE INDEX ix_workflow_experiment_id ON workflow (experiment_id);
CREATE INDEX ix_workflow_def_id ON workflow (def_id);
