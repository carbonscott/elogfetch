import enum
from datetime import datetime
from typing import Optional

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

    user_id: str = Field(
        sa_column=sa.Column(
            sa.Text,
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    posix_group_name: str = Field(
        sa_column=sa.Column(
            sa.Text,
            sa.ForeignKey("posix_group.name", ondelete="CASCADE"),
            primary_key=True,
        )
    )


# =============================================================================
# Independent lookup / reference tables (no FKs to other tables)
# =============================================================================


class User(SQLModel, table=True):
    id: str = Field(primary_key=True)

    pi: Optional["PI"] = Relationship(
        back_populates="user",
        cascade_delete=True,
    )
    posix_groups: list["PosixGroup"] = Relationship(
        back_populates="users", link_model=UserPosixGroup, passive_deletes=True
    )
    workflows: list["Workflow"] = Relationship(
        back_populates="user",
        passive_deletes=True,
    )


class PosixGroup(SQLModel, table=True):
    __tablename__ = "posix_group"  # type: ignore[assignment]

    name: str = Field(primary_key=True)

    users: list[User] = Relationship(
        back_populates="posix_groups", link_model=UserPosixGroup, passive_deletes=True
    )
    experiments: list["Experiment"] = Relationship(
        back_populates="posix_group_obj",
        passive_deletes=True,
    )


class Detector(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str = Field(unique=True)
    description: str | None = None

    run_detectors: list["RunDetector"] = Relationship(
        back_populates="detector",
        passive_deletes=True,
    )


# =============================================================================
# PI extends user with contact info
# =============================================================================


class PI(SQLModel, table=True):
    id: str = Field(
        sa_column=sa.Column(
            sa.Text,
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    # Parsed from the experiment's free-form contact_info string; nullable in
    # case the string format doesn't match the expected "Name (email)" pattern.
    name: str | None = None
    email: str | None = None

    user: User | None = Relationship(back_populates="pi")
    experiments: list["Experiment"] = Relationship(
        back_populates="pi",
        passive_deletes=True,
    )


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
    pi_id: str = Field(foreign_key="pi.id", index=True)
    leader_account: str
    posix_group: str = Field(foreign_key="posix_group.name")
    description: str | None = None
    # D3: ETL sync tracking
    fetched_at: datetime | None = Field(
        default=None,
        sa_column=sa.Column(
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    pi: PI | None = Relationship(back_populates="experiments")
    posix_group_obj: PosixGroup | None = Relationship(back_populates="experiments")
    slack_channel: Optional["ExperimentSlackChannel"] = Relationship(
        back_populates="experiment",
        passive_deletes=True,
    )
    analysis_queues: list["ExperimentAnalysisQueue"] = Relationship(
        back_populates="experiment",
        passive_deletes=True,
    )
    questionnaire_fields: list["Questionnaire"] = Relationship(
        back_populates="experiment",
        passive_deletes=True,
    )
    runs: list["Run"] = Relationship(
        back_populates="experiment",
        cascade_delete=True,
    )
    logbook_entries: list["Logbook"] = Relationship(
        back_populates="experiment",
        passive_deletes=True,
    )
    workflows: list["Workflow"] = Relationship(
        back_populates="experiment",
        cascade_delete=True,
    )


# =============================================================================
# Experiment auxiliary tables
# =============================================================================


class ExperimentSlackChannel(SQLModel, table=True):
    """At most one Slack channel per experiment."""

    __tablename__ = "experiment_slack_channel"  # type: ignore[assignment]

    experiment_id: str = Field(
        sa_column=sa.Column(
            sa.Text,
            sa.ForeignKey("experiment.experiment_id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    channel: str

    experiment: Experiment | None = Relationship(back_populates="slack_channel")


class ExperimentAnalysisQueue(SQLModel, table=True):
    """Multiple analysis queues per experiment (normalized from space-separated source)."""

    __tablename__ = "experiment_analysis_queue"  # type: ignore[assignment]

    experiment_id: str = Field(
        sa_column=sa.Column(
            sa.Text,
            sa.ForeignKey("experiment.experiment_id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
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
    experiment_id: str = Field(
        sa_column=sa.Column(
            sa.Text,
            sa.ForeignKey("experiment.experiment_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
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
# Workflow definitions
# =============================================================================


class WorkflowDefinition(SQLModel, table=True):
    id: str = Field(primary_key=True)
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

    workflows: list["Workflow"] = Relationship(
        back_populates="definition",
        passive_deletes=True,
    )


# =============================================================================
# Runs (per experiment)
# =============================================================================


class Run(SQLModel, table=True):
    __table_args__ = (
        sa.UniqueConstraint("run_number", "experiment_id", name="uq_run_number_exp"),
    )

    id: str = Field(primary_key=True)
    run_number: int
    experiment_id: str = Field(
        sa_column=sa.Column(
            sa.Text,
            sa.ForeignKey("experiment.experiment_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    start_time: datetime | None = Field(
        default=None, sa_column=sa.Column(sa.DateTime(timezone=True))
    )
    end_time: datetime | None = Field(
        default=None, sa_column=sa.Column(sa.DateTime(timezone=True))
    )
    # D3: ETL sync tracking
    fetched_at: datetime | None = Field(
        default=None,
        sa_column=sa.Column(
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    experiment: Experiment | None = Relationship(back_populates="runs")
    production_data: Optional["RunProductionData"] = Relationship(
        back_populates="run",
        cascade_delete=True,
    )
    detectors: list["RunDetector"] = Relationship(
        back_populates="run",
        passive_deletes=True,
    )
    logbook_entries: list["Logbook"] = Relationship(
        back_populates="run",
        passive_deletes=True,
    )
    workflows: list["Workflow"] = Relationship(
        back_populates="run",
        passive_deletes=True,
    )


# =============================================================================
# Run production data + file stats (1:1 with run)
# =============================================================================


class RunProductionData(SQLModel, table=True):
    __tablename__ = "run_production_data"  # type: ignore[assignment]

    # INVARIANT: experiment_id must equal run.experiment_id for run_id.
    # This is enforced at the application/ETL layer. A DB trigger will be added
    # when RLS is enabled to prevent silent corruption.
    run_id: str = Field(
        sa_column=sa.Column(
            sa.Text,
            sa.ForeignKey("run.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    experiment_id: str = Field(
        sa_column=sa.Column(
            sa.Text,
            sa.ForeignKey("experiment.experiment_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
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
    __table_args__ = (sa.Index("ix_run_detector_detector_id", "detector_id"),)

    # INVARIANT: experiment_id must equal run.experiment_id for run_id.
    # This is enforced at the application/ETL layer. A DB trigger will be added
    # when RLS is enabled to prevent silent corruption.
    run_id: str = Field(
        sa_column=sa.Column(
            sa.Text,
            sa.ForeignKey("run.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    detector_id: str = Field(
        sa_column=sa.Column(
            sa.Text,
            sa.ForeignKey("detector.id", ondelete="RESTRICT"),
            primary_key=True,
        )
    )
    experiment_id: str = Field(
        sa_column=sa.Column(
            sa.Text,
            sa.ForeignKey("experiment.experiment_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    value: str

    run: Run | None = Relationship(back_populates="detectors")
    detector: Detector | None = Relationship(back_populates="run_detectors")


# =============================================================================
# Logbook entries
# =============================================================================


class Logbook(SQLModel, table=True):
    id: str = Field(primary_key=True)
    experiment_id: str = Field(
        sa_column=sa.Column(
            sa.Text,
            sa.ForeignKey("experiment.experiment_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    run_id: str | None = Field(
        default=None,
        sa_column=sa.Column(
            sa.Text,
            sa.ForeignKey("run.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
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

    # INVARIANT: experiment_id must equal run.experiment_id for run_id.
    # This is enforced at the application/ETL layer. A DB trigger will be added
    # when RLS is enabled to prevent silent corruption.
    experiment_id: str = Field(
        sa_column=sa.Column(
            sa.Text,
            sa.ForeignKey("experiment.experiment_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    run_id: str = Field(
        sa_column=sa.Column(
            sa.Text,
            sa.ForeignKey("run.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    def_id: str = Field(
        sa_column=sa.Column(
            sa.Text,
            sa.ForeignKey("workflowdefinition.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    user_id: str = Field(
        sa_column=sa.Column(
            sa.Text,
            sa.ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
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
