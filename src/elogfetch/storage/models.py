from __future__ import annotations

import enum
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, Relationship, SQLModel

# =============================================================================
# ENUMs
# =============================================================================


class WorkflowTriggerType(str, enum.Enum):
    MANUAL = "MANUAL"
    START_OF_RUN = "START_OF_RUN"
    END_OF_RUN = "END_OF_RUN"
    FIRST_FILE_TRANSFERRED = "FIRST_FILE_TRANSFERRED"
    ALL_FILES_TRANSFERRED = "ALL_FILES_TRANSFERRED"
    ALL_NONREC_FILES_TRANSFERRED = "ALL_NONREC_FILES_TRANSFERRED"
    RUN_PARAM_IS_VALUE = "RUN_PARAM_IS_VALUE"


class ElogContentType(str, enum.Enum):
    TEXT = "TEXT"
    HTML = "HTML"
    MARKDOWN = "MARKDOWN"


# =============================================================================
# Junction tables (defined first so link_model= references resolve)
# =============================================================================


class UserPosixGroup(SQLModel, table=True):
    """Junction: user <-> posix_group (many-to-many)."""

    __tablename__ = "user_posix_group"  # type: ignore[assignment]

    user_id: str = Field(primary_key=True, foreign_key="user.id")
    posix_group_name: str = Field(primary_key=True, foreign_key="posix_group.name")


# =============================================================================
# Independent lookup / reference tables (no FKs to other tables)
# =============================================================================


class User(SQLModel, table=True):
    id: str = Field(primary_key=True)

    pi: PI | None = Relationship(back_populates="user")
    posix_groups: list[PosixGroup] = Relationship(
        back_populates="users", link_model=UserPosixGroup
    )
    workflows: list[Workflow] = Relationship(back_populates="user")


class PosixGroup(SQLModel, table=True):
    __tablename__ = "posix_group"  # type: ignore[assignment]

    name: str = Field(primary_key=True)

    users: list[User] = Relationship(
        back_populates="posix_groups", link_model=UserPosixGroup
    )
    experiments: list[Experiment] = Relationship(back_populates="posix_group_obj")


class Detector(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str = Field(unique=True)
    description: str | None = None

    run_detectors: list[RunDetector] = Relationship(back_populates="detector")


# =============================================================================
# PI extends user with contact info
# =============================================================================


class PI(SQLModel, table=True):
    id: str = Field(primary_key=True, foreign_key="user.id")
    name: str
    email: str

    user: User | None = Relationship(back_populates="pi")
    experiments: list[Experiment] = Relationship(back_populates="pi")


# =============================================================================
# Experiment (central entity)
# =============================================================================


class Experiment(SQLModel, table=True):
    experiment_id: str = Field(primary_key=True)
    name: str
    instrument: str
    start_time: datetime = Field(
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False)
    )
    end_time: datetime | None = Field(
        default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True)
    )
    pi_id: str = Field(foreign_key="pi.id")
    leader_account: str
    posix_group: str = Field(foreign_key="posix_group.name")
    description: str | None = None
    fetched_at: datetime = Field(
        sa_column=sa.Column(
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    pi: PI | None = Relationship(back_populates="experiments")
    posix_group_obj: PosixGroup | None = Relationship(back_populates="experiments")
    slack_channel: ExperimentSlackChannel | None = Relationship(
        back_populates="experiment"
    )
    analysis_queues: list[ExperimentAnalysisQueue] = Relationship(
        back_populates="experiment"
    )
    questionnaire_fields: list[Questionnaire] = Relationship(
        back_populates="experiment"
    )
    workflow_definitions: list[WorkflowDefinition] = Relationship(
        back_populates="experiment"
    )
    runs: list[Run] = Relationship(back_populates="experiment")
    logbook_entries: list[Logbook] = Relationship(back_populates="experiment")
    workflows: list[Workflow] = Relationship(back_populates="experiment")


# =============================================================================
# Experiment auxiliary tables
# =============================================================================


class ExperimentSlackChannel(SQLModel, table=True):
    """At most one Slack channel per experiment."""

    __tablename__ = "experiment_slack_channel"  # type: ignore[assignment]

    experiment_id: str = Field(primary_key=True, foreign_key="experiment.experiment_id")
    channel: str

    experiment: Experiment | None = Relationship(back_populates="slack_channel")


class ExperimentAnalysisQueue(SQLModel, table=True):
    """Multiple analysis queues per experiment (normalized from space-separated source)."""

    __tablename__ = "experiment_analysis_queue"  # type: ignore[assignment]

    experiment_id: str = Field(primary_key=True, foreign_key="experiment.experiment_id")
    queue: str = Field(primary_key=True)

    experiment: Experiment | None = Relationship(back_populates="analysis_queues")


# =============================================================================
# Questionnaire fields (per experiment)
# =============================================================================


class Questionnaire(SQLModel, table=True):
    __table_args__ = (
        sa.UniqueConstraint(
            "experiment_id", "field_id", name="uq_questionnaire_exp_field"
        ),
    )

    questionnaire_id: int | None = Field(
        default=None,
        sa_column=sa.Column(sa.BigInteger, primary_key=True, autoincrement=True),
    )
    experiment_id: str = Field(foreign_key="experiment.experiment_id", index=True)
    proposal: str | None = None
    category: str
    field_id: str
    field_name: str | None = None
    field_value: str | None = None
    modified_time: datetime | None = Field(
        default=None, sa_column=sa.Column(sa.DateTime(timezone=True))
    )
    modified_uid: str | None = None
    created_time: datetime = Field(
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False)
    )

    experiment: Experiment | None = Relationship(back_populates="questionnaire_fields")


# =============================================================================
# Workflow definitions (templates, per experiment)
# =============================================================================


class WorkflowDefinition(SQLModel, table=True):
    id: str = Field(primary_key=True)
    experiment_id: str = Field(foreign_key="experiment.experiment_id", index=True)
    name: str
    executable: str
    trigger: WorkflowTriggerType = Field(
        sa_column=sa.Column(
            sa.Enum(
                WorkflowTriggerType,
                name="workflow_trigger_type",
                create_type=True,
            ),
            nullable=False,
        )
    )
    location: str
    parameters: str | None = None  # raw string as returned by API
    run_param_name: str | None = None
    run_param_value: str | None = None
    run_as_user: str | None = None

    experiment: Experiment | None = Relationship(back_populates="workflow_definitions")
    workflows: list[Workflow] = Relationship(back_populates="definition")


# =============================================================================
# Runs (per experiment)
# =============================================================================


class Run(SQLModel, table=True):
    __table_args__ = (
        sa.UniqueConstraint("run_number", "experiment_id", name="uq_run_number_exp"),
    )

    id: str = Field(primary_key=True)
    run_number: int
    experiment_id: str = Field(foreign_key="experiment.experiment_id", index=True)
    start_time: datetime | None = Field(
        default=None, sa_column=sa.Column(sa.DateTime(timezone=True))
    )
    end_time: datetime | None = Field(
        default=None, sa_column=sa.Column(sa.DateTime(timezone=True))
    )
    fetched_at: datetime = Field(
        sa_column=sa.Column(
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    experiment: Experiment | None = Relationship(back_populates="runs")
    production_data: RunProductionData | None = Relationship(back_populates="run")
    detectors: list[RunDetector] = Relationship(back_populates="run")
    logbook_entries: list[Logbook] = Relationship(back_populates="run")
    workflows: list[Workflow] = Relationship(back_populates="run")


# =============================================================================
# Run production data + file stats (1:1 with run)
# =============================================================================


class RunProductionData(SQLModel, table=True):
    __tablename__ = "run_production_data"  # type: ignore[assignment]

    run_id: str = Field(primary_key=True, foreign_key="run.id")
    experiment_id: str = Field(foreign_key="experiment.experiment_id", index=True)
    n_events: int | None = Field(default=None, sa_column=sa.Column(sa.BigInteger))
    n_damaged: int | None = Field(default=None, sa_column=sa.Column(sa.BigInteger))
    n_dropped: int | None = Field(default=None, sa_column=sa.Column(sa.BigInteger))
    start_timestamp: datetime | None = Field(
        default=None, sa_column=sa.Column(sa.DateTime(timezone=True))
    )
    end_timestamp: datetime | None = Field(
        default=None, sa_column=sa.Column(sa.DateTime(timezone=True))
    )
    file_count: int | None = Field(default=None, sa_column=sa.Column(sa.BigInteger))
    file_size_bytes: int | None = Field(
        default=None, sa_column=sa.Column(sa.BigInteger)
    )

    run: Run | None = Relationship(back_populates="production_data")


# =============================================================================
# Run <-> Detector junction (with status value)
# =============================================================================


class RunDetector(SQLModel, table=True):
    __tablename__ = "run_detector"  # type: ignore[assignment]

    run_id: str = Field(primary_key=True, foreign_key="run.id")
    detector_id: str = Field(primary_key=True, foreign_key="detector.id")
    experiment_id: str = Field(foreign_key="experiment.experiment_id", index=True)
    value: str

    run: Run | None = Relationship(back_populates="detectors")
    detector: Detector | None = Relationship(back_populates="run_detectors")


# =============================================================================
# Logbook entries
# =============================================================================


class Logbook(SQLModel, table=True):
    id: str = Field(primary_key=True)
    experiment_id: str = Field(foreign_key="experiment.experiment_id", index=True)
    run_id: str | None = Field(default=None, foreign_key="run.id", index=True)
    created_time: datetime = Field(
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False)
    )
    content: str | None = None
    content_type: ElogContentType = Field(
        sa_column=sa.Column(
            sa.Enum(ElogContentType, name="elog_content_type", create_type=True),
            nullable=False,
        )
    )
    tags: list[str] | None = Field(default=None, sa_column=sa.Column(ARRAY(sa.Text)))
    author: str

    experiment: Experiment | None = Relationship(back_populates="logbook_entries")
    run: Run | None = Relationship(back_populates="logbook_entries")


# =============================================================================
# Workflow executions (job runs, references a definition)
# =============================================================================


class Workflow(SQLModel, table=True):
    id: str = Field(primary_key=True)
    experiment_id: str = Field(foreign_key="experiment.experiment_id", index=True)
    run_id: str = Field(foreign_key="run.id")
    def_id: str = Field(foreign_key="workflowdefinition.id", index=True)
    user_id: str = Field(foreign_key="user.id")
    status: str
    submit_time: datetime = Field(
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False)
    )
    tool_id: int | None = Field(default=None, sa_column=sa.Column(sa.BigInteger))
    log_file_path: str | None = None

    experiment: Experiment | None = Relationship(back_populates="workflows")
    run: Run | None = Relationship(back_populates="workflows")
    definition: WorkflowDefinition | None = Relationship(back_populates="workflows")
    user: User | None = Relationship(back_populates="workflows")
