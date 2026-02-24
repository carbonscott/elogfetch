"""
This was generated with GH Copilot (Claude 4.6) in the following way:
1. Generate tarred jsons for each endpoint with `experiment_dump.py`
2. Ask claude to inspect the results and generate pydantic models
3. Claude does a good job. Leaves out "params", but for good reason -
it is OK we can deal with them internally if we have specifics we want to get out.

TODO: this should be tested with many types of experiments, we should run a test
case for the various facilities using it.

All GET endpoints follow one of two envelope shapes:
  Standard:  {"success": bool, "value": <payload>}
  Special:   {"status": "success", "defs": [...]}  (POC feedback schema only)
"""

import re as _re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Generic, Self, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Reusable annotated types
# ---------------------------------------------------------------------------

_SLASH_DATE_FMT = "%m/%d/%Y %H:%M:%S"


def _parse_slash_date(value: Any) -> Any:
    """Convert MM/DD/YYYY HH:MM:SS strings to ISO-8601."""
    if isinstance(value, str) and "/" in value:
        try:
            return datetime.strptime(value, _SLASH_DATE_FMT).isoformat()
        except ValueError:
            pass
    return value


# replacement for ``datetime`` fields that may arrive as
# ``"MM/DD/YYYY HH:MM:SS"`` strings
SlashDatetime = Annotated[datetime, BeforeValidator(_parse_slash_date)]

# ---------------------------------------------------------------------------
# Shared model config
# ---------------------------------------------------------------------------

_cfg = ConfigDict(validate_by_alias=True, validate_by_name=True, extra="allow")


# ===========================================================================
# Section 1 – Response envelopes
# ===========================================================================


class LgbkResponse(BaseModel, Generic[T]):
    """Standard API envelope: ``{"success": bool, "value": <payload>}``."""

    model_config = _cfg

    success: bool
    value: T | None = None


class LgbkEmptyResponse(BaseModel):
    """Endpoints that return only ``{"success": true}`` with no value."""

    model_config = _cfg

    success: bool


# ===========================================================================
# Section 2 – Enumerations
# ===========================================================================


class WorkflowTrigger(str, Enum):
    MANUAL = "MANUAL"
    START_OF_RUN = "START_OF_RUN"
    END_OF_RUN = "END_OF_RUN"
    FIRST_FILE_TRANSFERRED = "FIRST_FILE_TRANSFERRED"
    ALL_FILES_TRANSFERRED = "ALL_FILES_TRANSFERRED"
    ALL_NONREC_FILES_TRANSFERRED = "ALL_NONREC_FILES_TRANSFERRED"
    RUN_PARAM_IS_VALUE = "RUN_PARAM_IS_VALUE"


class ElogContentType(str, Enum):
    TEXT = "TEXT"
    HTML = "HTML"
    MARKDOWN = "MARKDOWN"


# ===========================================================================
# Section 3 – Nested / shared sub-models
# ===========================================================================


# --------------- Elog -------------------------------------------------------


class ElogAttachment(BaseModel):
    """A file attachment on an elog entry."""

    model_config = _cfg

    id: str = Field(alias="_id")
    name: str
    type: str  # MIME type, e.g. "image/jpeg"
    url: str
    preview_url: str | None = None


class ElogEntry(BaseModel):
    """A single logbook entry, returned by ``/ws/elog`` and search endpoints.

    When returned by ``/ws/elog/<entry_id>/complete_elog_tree`` the entry may
    include ``children`` (replies/sub-entries).
    """

    model_config = _cfg

    id: str = Field(alias="_id")
    relevance_time: datetime
    insert_time: datetime
    author: str
    content: str
    content_type: ElogContentType = ElogContentType.TEXT
    attachments: list[ElogAttachment] = Field(default_factory=list)
    tags: list[str] | None = None
    run_num: int | None = None
    shift: str | None = None
    title: str | None = None
    # Populated by complete_elog_tree endpoint
    children: list[Self] | None = None
    root: str | None = None  # id of root entry
    parent: str | None = None  # id of parent entry


ElogEntry.model_rebuild()  # rebuild for forward ref (children)


# --------------- Files -------------------------------------------------------


class FileLocationInfo(BaseModel):
    """Per-location metadata for a file (value in ``locations`` dict)."""

    model_config = _cfg

    asof: datetime | None = None


class FileEntry(BaseModel):
    """A data file tracked by the file catalog.

    Returned by ``/ws/files``, ``/ws/<run_num>/files``, live-mode file
    endpoints, etc.
    """

    model_config = _cfg

    id: str = Field(alias="_id")
    absolute_path: str
    path: str
    run_num: int
    size: int
    gen: int | None = None
    hostname: str | None = None
    create_timestamp: datetime | None = None
    modify_timestamp: datetime | None = None
    # keys are location names (e.g. "S3DF", "SRCF_FFB")
    locations: dict[str, FileLocationInfo] = Field(default_factory=dict)


# --------------- Runs --------------------------------------------------------

DETECTOR_PREFIX = "DAQ Detectors/"


class RunDetector(BaseModel):
    id: str
    value: str


class RunParams(BaseModel):
    """Run parameters, returned by

    Returned by ``/ws/runs/<num>?includeParams=true``, etc.
    """

    model_config = _cfg

    n_events: int | None = Field(default=None, alias="DAQ Detector Totals/Events")
    n_damaged: int | None = Field(default=None, alias="DAQ Detector Totals/Damaged")
    n_dropped: int | None = Field(default=None, alias="N dropped Shots")
    prod_start: SlashDatetime | None = Field(default=None, alias="Prod_start")
    prod_end: SlashDatetime | None = Field(default=None, alias="Prod_end")
    prod_jobstart: SlashDatetime | None = Field(default=None, alias="Prod_jobstart")
    detectors: list[RunDetector] | None = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def apply_detectors(cls, data: Any):
        if not isinstance(data, dict):
            return data
        det_ids = [k for k in data.keys() if k.startswith(DETECTOR_PREFIX)]

        # TODO: I think this is fine to mutate the incoming data as long as "detectors"
        # is not a part of the incoming data (which it is not, to my knowledge)
        dets = [{"id": det_id, "value": data[det_id]} for det_id in det_ids]
        data["detectors"] = dets
        return data


class Run(BaseModel):
    """A single DAQ run.

    Returned by ``/ws/runs``, ``/ws/runs/<num>``, ``/ws/current_run``, etc.
    """

    model_config = _cfg

    id: str = Field(alias="_id")
    num: int
    type: str  # TODO: should be an enum, but really only looks to be of type "DATA"
    begin_time: datetime
    end_time: datetime
    # Arbitrary EPICS / DAQ / user parameters recorded at run start
    params: RunParams = Field(default_factory=RunParams)
    sample: str | None = None


class RunTableRow(BaseModel):
    """A row in run-table export data (``/ws/run_table_data``)."""

    model_config = _cfg

    id: str = Field(alias="_id")
    num: int
    begin_time: datetime
    end_time: datetime | None = None
    params: dict[str, Any] = Field(
        default_factory=dict
    )  # TODO: this could be RunParams too, probably but double check
    # millisecond epoch equivalents, added by the API for front-end use
    begin_time_epoch: int | None = None
    end_time_epoch: int | None = None


class RunParamSummary(BaseModel):
    """Sparse run returned by ``/ws/get_run_params_for_all_runs``."""

    model_config = _cfg

    id: str = Field(alias="_id")
    num: int
    params: dict[str, Any] = Field(
        default_factory=dict
    )  # TODO: this could be RunParams too, probably but double check


class RunForCalib(BaseModel):
    """Compact run record returned by ``/ws/runs_for_calib``."""

    model_config = _cfg

    run_num: int
    run_type: str
    begin_time: int  # Unix epoch seconds
    end_time: int | None = None


class RunParamDescription(BaseModel):
    """Human-readable description for a run parameter PV name."""

    model_config = _cfg

    id: str = Field(alias="_id")
    param_name: str
    description: str


# --------------- Run tables --------------------------------------------------


class RunTableColDef(BaseModel):
    """Column definition inside a RunTable."""

    model_config = _cfg

    label: str
    type: str
    source: str
    is_editable: bool = False
    position: int
    mime_type: str = "text"


class RunTable(BaseModel):
    """Definition of a run table (``/ws/run_tables``)."""

    model_config = _cfg

    id: str = Field(alias="_id")
    name: str
    description: str | None = None
    is_editable: bool = False
    table_type: str = "table"
    sort_index: int | None = None
    coldefs: list[RunTableColDef] = Field(default_factory=list)
    is_system_run_table: bool | None = None


class RunTableSourceEntry(BaseModel):
    """One entry in the run-table column-source catalogue (``/ws/run_table_sources``)."""

    model_config = _cfg

    label: str
    description: str
    source: str
    category: str


# --------------- Shifts ------------------------------------------------------


class Shift(BaseModel):
    """An experimental shift (``/ws/shifts``, ``/ws/get_latest_shift``)."""

    model_config = _cfg

    id: str = Field(alias="_id")
    name: str
    begin_time: datetime
    end_time: datetime | None = None
    leader: str
    description: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    # Computed field added by the API for the "current" logical end time
    logical_end_time: datetime | None = None


# --------------- Samples -----------------------------------------------------


class Sample(BaseModel):
    """A sample definition (``/ws/samples``, ``/ws/samples/<name>``)."""

    model_config = _cfg

    id: str | None = Field(default=None, alias="_id")
    name: str | None = None
    description: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


# --------------- Collaborators -----------------------------------------------


class Collaborator(BaseModel):
    """A collaborator / role assignment on an experiment (``/ws/collaborators``)."""

    model_config = _cfg

    uid: str
    is_group: bool
    full_name: str
    uid_number: str | None = Field(default=None, alias="uidNumber")
    roles: list[str] = Field(default_factory=list)


# --------------- DM locations ------------------------------------------------


class DmLocation(BaseModel):
    """Data-management storage location (``/ws/dm_locations``)."""

    model_config = _cfg

    name: str
    all_experiments: bool = False
    jid_prefix: str | None = None


# --------------- Contact info ------------------------------------------------


_CONTACT_RE = _re.compile(r"^\s*(.+?)\s*\(([^)]+)\)\s*$")


def _parse_contact_info(value: Any) -> Any:
    """BeforeValidator: accept either a raw ``"Name (email)"`` string or an
    already-decomposed dict.  Falls back gracefully if the pattern doesn't match.
    """
    if not isinstance(value, str):
        return value
    m = _CONTACT_RE.match(value)
    if m:
        name, email = m.group(1), m.group(2)
        # Only treat as email if it contains '@'
        if "@" in email:
            return {"name": name.strip(), "email": email.strip()}
        # Parens but no email — treat the whole thing as name
        return {"name": value.strip(), "email": None}
    return {"name": value.strip(), "email": None}


class ContactInfo(BaseModel):
    """Parsed from the experiment ``contact_info`` free-form string.

    Accepts either a raw ``"Name (email@example.com)"`` string (via
    ``BeforeValidator``) or a pre-decomposed dict.
    """

    model_config = _cfg

    name: str | None = None
    email: str | None = None

    # Applied before field-level validation so the string → dict conversion
    # runs once at the model boundary, not per-field.
    @model_validator(mode="before")
    @classmethod
    def parse_string(cls, data: Any) -> Any:
        return _parse_contact_info(data)


# --------------- Experiments -------------------------------------------------


class ExperimentParams(BaseModel):
    """Flexible extra params dict stored on an experiment."""

    model_config = _cfg

    PNR: str | None = None
    dm_locations: str | None = None
    zoom_meeting_id: str | None = None
    zoom_meeting_pwd: str | None = None
    zoom_meeting_url: str | None = None
    slack_channels: str | None = None
    analysis_queues: str | None = None
    data_path: Path | None = Field(alias="DATA_PATH")


class Experiment(BaseModel):
    """Core experiment / proposal record.

    Used by ``/ws/info``, ``/ws/experiments``, search results, etc.
    """

    model_config = _cfg

    id: str = Field(alias="_id")
    name: str
    instrument: str  # TODO: should be an enum
    posix_group: str
    leader_account: str
    start_time: datetime
    end_time: datetime
    contact_info: str
    type: str | None = None
    description: str
    data_collection_software: str | None = None
    registration_time: datetime | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    # Fields present in the global experiments list
    players: list[str] | None = None
    post_players: list[str] | None = None
    run_count: int | None = None
    total_files: int | None = Field(default=None, alias="totalFiles")
    total_data_size: float | None = Field(default=None, alias="totalDataSize")


class CurrentRunRef(BaseModel):
    """Minimal run reference embedded in ActiveExperiment."""

    model_config = _cfg

    num: int
    begin_time: datetime


class ActiveExperiment(Experiment):
    """An experiment currently active on an instrument station.

    Returned by ``/ws/activeexperiments`` and
    ``/ws/activeexperiment_for_instrument_station``.

    When a station is in standby mode the record omits ``_id`` and ``name``.
    """

    # Override parent required fields – standby entries omit both.
    id: str | None = Field(default=None, alias="_id")
    name: str | None = None

    station: int | None = None
    switch_time: datetime | None = None
    requestor_uid: str | None = None
    current_run: CurrentRunRef | None = None


class InternalInfo(BaseModel):
    """Internal/proposal metadata for an experiment (``/ws/internalinfo``)."""

    model_config = _cfg

    instrument: str
    proposal_id: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    posix_group: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class HasRoleResult(BaseModel):
    """Result of ``/ws/has_role``."""

    model_config = _cfg

    role_fq_name: str
    application_name: str
    role_name: str
    has_role: bool = Field(alias="hasRole")


# --------------- Instruments -------------------------------------------------


class InstrumentRole(BaseModel):
    """A role definition on an instrument."""

    model_config = _cfg

    app: str
    name: str
    players: list[str] = Field(default_factory=list)


class Instrument(BaseModel):
    """An LCLS instrument record (``/ws/instruments``)."""

    model_config = _cfg

    id: str = Field(alias="_id")
    color: str | None = None
    description: str | None = None
    # Values are usually strings but numeric fields (e.g. num_stations) can be int.
    params: dict[str, Any] = Field(default_factory=dict)
    roles: list[InstrumentRole] = Field(default_factory=list)


class InstrumentStation(BaseModel):
    """An instrument/station pair (``/ws/instrument_station_list``)."""

    model_config = _cfg

    instrument: str
    station: int


class InstrumentSwitchHistoryEntry(BaseModel):
    """One entry in the instrument switch history log."""

    model_config = _cfg

    id: str = Field(alias="_id")
    experiment_name: str
    instrument: str
    station: int
    switch_time: datetime
    requestor_uid: str | None = None
    is_standby: bool | None = None
    description: str | None = None


# --------------- Roles -------------------------------------------------------


class GlobalRole(BaseModel):
    """A site-wide role definition (``/ws/global_roles``)."""

    model_config = _cfg

    id: str = Field(alias="_id")
    app: str
    name: str
    privileges: list[str] = Field(default_factory=list)
    players: list[str] = Field(default_factory=list)


# --------------- Workflow ----------------------------------------------------


class WorkflowDefinition(BaseModel):
    """A workflow / analysis job definition (``/ws/workflow_definitions``)."""

    model_config = _cfg

    id: str = Field(alias="_id")
    name: str
    executable: str
    trigger: str  # WorkflowTrigger or free-form legacy value
    location: str
    parameters: str | None = None
    run_as_user: str | None = None
    run_param_name: str | None = None
    run_param_value: str | None = None


class WorkflowCounter(BaseModel):
    """A key/value counter badge on a workflow job."""

    model_config = _cfg

    key: str
    # The API sends strings (e.g. HTML like "<b>Last Event</b>") but also
    # plain integers for numeric counters.
    value: str | int


class WorkflowJob(BaseModel):
    """A workflow job instance (``/ws/workflow_jobs``)."""

    model_config = _cfg

    id: str = Field(alias="_id")
    run_num: int
    def_id: str
    user: str
    status: str
    submit_time: datetime
    experiment: str
    # Embed the definition snapshot stored at submission time
    definition: WorkflowDefinition | None = Field(default=None, alias="def")
    tool_id: int | None = None
    log_file_path: str | None = None
    counters: list[WorkflowCounter] = Field(default_factory=list)


class WorkflowTriggerInfo(BaseModel):
    """Metadata about a supported workflow trigger type (``/ws/workflow_triggers``)."""

    model_config = _cfg

    value: str
    label: str


# --------------- File management ---------------------------------------------


class FileManagerFileType(BaseModel):
    """A file-type filter definition (``/filemanager_file_types``)."""

    model_config = _cfg

    name: str
    label: str
    tooltip: str | None = None
    patterns: list[str] = Field(default_factory=list)
    selected: bool = False


# --------------- Experiment stats --------------------------------------------


class DailyDataBreakdown(BaseModel):
    """Daily data size entry inside ExperimentStat."""

    model_config = _cfg

    id: str = Field(alias="_id")  # date string, e.g. "Mon, 14 Oct 2013 00:00:00 GMT"
    total_size: float  # size in GB


class ExperimentStat(BaseModel):
    """Per-experiment data-size statistics (``/ws/experiment_stats``)."""

    model_config = _cfg

    id: str = Field(alias="_id")  # experiment name
    data_daily_breakdown: list[DailyDataBreakdown] = Field(
        default_factory=list, alias="dataDailyBreakdown"
    )


# --------------- POC feedback ------------------------------------------------


class PocFeedbackSchemaGroup(BaseModel):
    """Recursive definition of a feedback form group/field.

    Section-header groups act as containers and may omit ``id`` and ``type``.
    """

    model_config = _cfg

    title: str
    id: str | None = None
    default_value: Any = None
    type: str | None = None  # "Number", "Boolean", "String", etc.
    groups: list[Self] | None = None


PocFeedbackSchemaGroup.model_rebuild()


class PocFeedbackSchemaDef(BaseModel):
    """Top-level section of the POC feedback schema."""

    model_config = _cfg

    title: str
    groups: list[PocFeedbackSchemaGroup] = Field(default_factory=list)


class PocFeedbackSchemaResponse(BaseModel):
    """Special envelope used only by ``/ws/poc_feedback/schema``."""

    model_config = _cfg

    status: str
    defs: list[PocFeedbackSchemaDef] = Field(default_factory=list)


# --------------- API endpoint metadata ---------------------------------------


class ApiEndpoint(BaseModel):
    """One registered Flask route (``/ws/api_endpoints``)."""

    model_config = _cfg

    url: str | None = None
    methods: list[str] = Field(default_factory=list)


# ===========================================================================
# Section 4 – Typed response aliases
#
# Each alias gives a concrete, import-friendly name for the response of a
# specific GET endpoint.
# ===========================================================================

# ---- Global / site-level endpoints ----------------------------------------

#: GET /lgbk/ws/instruments
InstrumentsResponse = LgbkResponse[list[Instrument]]

#: GET /lgbk/ws/instrument_station_list
InstrumentStationListResponse = LgbkResponse[list[InstrumentStation]]

#: GET /lgbk/ws/instrument_switch_history
InstrumentSwitchHistoryResponse = LgbkResponse[list[InstrumentSwitchHistoryEntry]]

#: GET /lgbk/ws/activeexperiments
ActiveExperimentsResponse = LgbkResponse[list[ActiveExperiment]]

#: GET /lgbk/ws/activeexperiment_for_instrument_station
ActiveExperimentForStationResponse = LgbkResponse[Experiment]

#: GET /lgbk/ws/experiments
ExperimentsResponse = LgbkResponse[list[Experiment]]

#: GET /lgbk/ws/search_experiment_info
SearchExperimentInfoResponse = LgbkResponse[list[Experiment]]

#: GET /lgbk/ws/experiments_with_user_as_collaborator
ExperimentsWithUserResponse = LgbkResponse[list[Experiment]]

#: GET /lgbk/ws/get_cached_experiment_names
#: value is list[str]
CachedExperimentNamesResponse = LgbkResponse[list[str]]

#: GET /lgbk/ws/experiment_names_updated_within
ExperimentNamesUpdatedWithinResponse = LgbkResponse[list[str]]

#: GET /lgbk/ws/experiments_to_proposal
#: value is dict[proposal_id, experiment_name]
ExperimentsToProposalResponse = LgbkResponse[dict[str, str]]

#: GET /lgbk/ws/postable_experiments
PostableExperimentsResponse = LgbkResponse[list[str]]

#: GET /lgbk/ws/potentiallyactiveusers
#: value is list of uid strings
PotentiallyActiveUsersResponse = LgbkResponse[list[str]]

#: GET /lgbk/ws/usergroups
#: value is list of group strings
UserGroupsResponse = LgbkResponse[list[str]]

#: GET /lgbk/ws/global_roles
GlobalRolesResponse = LgbkResponse[list[GlobalRole]]

#: GET /lgbk/ws/experiment_stats
ExperimentStatsResponse = LgbkResponse[list[ExperimentStat]]

#: GET /lgbk/ws/experiment_daily_data_breakdown
#: value shape varies; use Any
ExperimentDailyDataBreakdownResponse = LgbkResponse[Any]

#: GET /lgbk/ws/api_endpoints
ApiEndpointsResponse = LgbkResponse[list[ApiEndpoint]]

#: GET /lgbk/naming_conventions
#: value is dict (site-specific, may be empty)
NamingConventionsResponse = LgbkResponse[dict[str, Any]]

#: GET /lgbk/filemanager_file_types
#: value is dict[type_name, FileManagerFileType]
FileManagerFileTypesResponse = LgbkResponse[dict[str, FileManagerFileType]]

#: GET /lgbk/ws/projects
ProjectsResponse = LgbkResponse[list[Any]]

#: GET /lgbk/ws/get_matching_uids
GetMatchingUidsResponse = LgbkResponse[list[str]]

#: GET /lgbk/ws/get_matching_groups
GetMatchingGroupsResponse = LgbkResponse[list[str]]

#: GET /lgbk/ws/get_params_matching_prefix (global)
#: value is list of param name strings
GlobalParamsMatchingPrefixResponse = LgbkResponse[list[str]]

#: GET /lgbk/ws/get_modal_param_definitions
#: value is dict (may be empty)
GlobalModalParamDefinitionsResponse = LgbkResponse[dict[str, Any]]

#: GET /lgbk/ws/lookup_experiment_in_urawi
LookupExperimentInUrawiResponse = LgbkResponse[Any]

#: GET /lgbk/ws/poc_feedback/experiments
PocFeedbackExperimentsResponse = LgbkResponse[list[str]]

#: GET /lgbk/ws/empty  – health-check endpoint
EmptyResponse = LgbkResponse[None]


# ---- Experiment-level endpoints -------------------------------------------

#: GET /lgbk/<exp>/ws/info
InfoResponse = LgbkResponse[Experiment]

#: GET /lgbk/<exp>/ws/internalinfo
InternalInfoResponse = LgbkResponse[InternalInfo]

#: GET /lgbk/<exp>/ws/has_role
HasRoleResponse = LgbkResponse[HasRoleResult]

#: GET /lgbk/<exp>/ws/collaborators
CollaboratorsResponse = LgbkResponse[list[Collaborator]]

#: GET /lgbk/<exp>/ws/exp_posix_group_members
#: value is list[str] of uid strings
PosixGroupMembersResponse = LgbkResponse[list[str]]

#: GET /lgbk/<exp>/ws/sync_collaborators (GET returns result dict)
SyncCollaboratorsResponse = LgbkEmptyResponse

#: GET /lgbk/<exp>/ws/elog
ElogResponse = LgbkResponse[list[ElogEntry]]

#: GET /lgbk/<exp>/ws/elog/<entry_id>/complete_elog_tree
ElogCompleteTreeResponse = LgbkResponse[list[ElogEntry]]

#: GET /lgbk/<exp>/ws/search_elog
SearchElogResponse = LgbkResponse[list[ElogEntry]]

#: GET /lgbk/<exp>/ws/get_elog_tags
#: value is list[str]
ElogTagsResponse = LgbkResponse[list[str]]

#: GET /lgbk/<exp>/ws/elog_emails
#: value is list[str]
ElogEmailsResponse = LgbkResponse[list[str]]

#: GET /lgbk/<exp>/ws/elog_email_subscriptions
#: value is list of subscription dicts
ElogEmailSubscriptionsResponse = LgbkResponse[list[Any]]

#: GET /lgbk/<exp>/ws/get_instrument_elogs
#: value is list[str] of instrument elog names
InstrumentElogsResponse = LgbkResponse[list[str]]

#: GET /lgbk/<exp>/ws/runs
RunsResponse = LgbkResponse[list[Run]]

#: GET /lgbk/<exp>/ws/runs/<run_num>
SingleRunResponse = LgbkResponse[Run]

#: GET /lgbk/<exp>/ws/current_run
CurrentRunResponse = LgbkResponse[Run]

#: GET /lgbk/<exp>/ws/runs_for_calib
RunsForCalibResponse = LgbkResponse[list[RunForCalib]]

#: GET /lgbk/<exp>/ws/run_param_descriptions
RunParamDescriptionsResponse = LgbkResponse[list[RunParamDescription]]

#: GET /lgbk/<exp>/ws/get_run_params_for_all_runs
RunParamsForAllRunsResponse = LgbkResponse[list[RunParamSummary]]

#: GET /lgbk/<exp>/ws/get_runs_matching_editable
RunsMatchingEditableResponse = LgbkResponse[list[Run]]

#: GET /lgbk/<exp>/ws/map_param_editable_to_run_nums
#: value is dict[param_value, list[int]]
MapParamEditableToRunNumsResponse = LgbkResponse[dict[str, list[int]]]

#: GET /lgbk/<exp>/ws/get_tags_to_runs
#: value is dict[tag, list[run_num]]
TagsToRunsResponse = LgbkResponse[dict[str, list[int]]]

#: GET /lgbk/<exp>/ws/get_runs_to_tags
#: value is dict[run_num_str, list[tag]]
RunsToTagsResponse = LgbkResponse[dict[str, list[str]]]

#: GET /lgbk/<exp>/ws/get_runs_with_tag
#: value is list[int] of run numbers
RunsWithTagResponse = LgbkResponse[list[int]]

#: GET /lgbk/<exp>/ws/<run_num>/get_tags_for_run
#: value is list[str]
TagsForRunResponse = LgbkResponse[list[str]]

#: GET /lgbk/<exp>/ws/<run_num>/get_params_matching_prefix
#: value is list[str] of param name strings
RunParamsMatchingPrefixResponse = LgbkResponse[list[str]]

#: GET /lgbk/<exp>/ws/<run_num>/daq_run_params
#: value is dict[str, str]
DaqRunParamsResponse = LgbkResponse[dict[str, str]]

#: GET /lgbk/<exp>/ws/get_modal_param_definitions
#: value is dict (may be empty)
ModalParamDefinitionsResponse = LgbkResponse[dict[str, Any]]

#: GET /lgbk/<exp>/ws/run_tables
RunTablesResponse = LgbkResponse[list[RunTable]]

#: GET /lgbk/<exp>/ws/run_table_sources
#: value is dict[category, list[RunTableSourceEntry]]
RunTableSourcesResponse = LgbkResponse[dict[str, list[RunTableSourceEntry]]]

#: GET /lgbk/<exp>/ws/run_table_data
RunTableDataResponse = LgbkResponse[list[RunTableRow]]

#: GET /lgbk/<exp>/ws/files
FilesResponse = LgbkResponse[list[FileEntry]]

#: GET /lgbk/<exp>/ws/<run_num>/files
RunFilesResponse = LgbkResponse[list[FileEntry]]

#: GET /lgbk/<exp>/ws/<run_num>/files_for_live_mode
#: value is list[str] of file paths
FilesForLiveModeResponse = LgbkResponse[list[str]]

#: GET /lgbk/<exp>/ws/<run_num>/files_for_live_mode_at_location
FilesForLiveModeAtLocationResponse = LgbkResponse[list[str]]

#: GET /lgbk/<exp>/ws/files_for_live_mode_at_location (experiment-wide)
ExpFilesForLiveModeAtLocationResponse = LgbkResponse[list[FileEntry]]

#: GET /lgbk/<exp>/ws/file_counts_by_extension
#: value is dict[ext, count]
FileCountsByExtensionResponse = LgbkResponse[dict[str, int]]

#: GET /lgbk/<exp>/ws/dm_locations
DmLocationsResponse = LgbkResponse[list[DmLocation]]

#: GET /lgbk/<exp>/ws/shifts
ShiftsResponse = LgbkResponse[list[Shift]]

#: GET /lgbk/<exp>/ws/get_latest_shift
LatestShiftResponse = LgbkResponse[Shift]

#: GET /lgbk/<exp>/ws/samples
SamplesResponse = LgbkResponse[list[Sample]]

#: GET /lgbk/<exp>/ws/samples/<name>
SingleSampleResponse = LgbkResponse[Sample]

#: GET /lgbk/<exp>/ws/current_sample_name
#: value is str | None
CurrentSampleNameResponse = LgbkResponse[str | None]

#: GET /lgbk/<exp>/ws/workflow_definitions
WorkflowDefinitionsResponse = LgbkResponse[list[WorkflowDefinition]]

#: GET /lgbk/<exp>/ws/workflow_triggers
WorkflowTriggersResponse = LgbkResponse[list[WorkflowTriggerInfo]]

#: GET /lgbk/<exp>/ws/workflow_jobs
WorkflowJobsResponse = LgbkResponse[list[WorkflowJob]]

#: GET /lgbk/<exp>/ws/workflow/<job_id>/job_details
#: value is str (text message or JSON string)
WorkflowJobDetailsResponse = LgbkResponse[str]

#: GET /lgbk/<exp>/ws/get_feedback_document
#: value is dict[id, value] of user-defined form values
FeedbackDocumentResponse = LgbkResponse[dict[str, Any]]

# __all__ for convenient star-imports
__all__ = [
    # Envelopes
    "LgbkResponse",
    "LgbkEmptyResponse",
    # Enums
    "WorkflowTrigger",
    "ElogContentType",
    # Sub-models
    "ElogAttachment",
    "ElogEntry",
    "FileLocationInfo",
    "FileEntry",
    "Run",
    "RunTableRow",
    "RunParamSummary",
    "RunForCalib",
    "RunParamDescription",
    "RunTableColDef",
    "RunTable",
    "RunTableSourceEntry",
    "Shift",
    "Sample",
    "Collaborator",
    "DmLocation",
    "ExperimentParams",
    "Experiment",
    "CurrentRunRef",
    "ActiveExperiment",
    "InternalInfo",
    "HasRoleResult",
    "InstrumentRole",
    "Instrument",
    "InstrumentStation",
    "InstrumentSwitchHistoryEntry",
    "GlobalRole",
    "WorkflowDefinition",
    "WorkflowCounter",
    "WorkflowJob",
    "WorkflowTriggerInfo",
    "FileManagerFileType",
    "DailyDataBreakdown",
    "ExperimentStat",
    "PocFeedbackSchemaGroup",
    "PocFeedbackSchemaDef",
    "PocFeedbackSchemaResponse",
    "ApiEndpoint",
    # Response aliases – global
    "InstrumentsResponse",
    "InstrumentStationListResponse",
    "InstrumentSwitchHistoryResponse",
    "ActiveExperimentsResponse",
    "ActiveExperimentForStationResponse",
    "ExperimentsResponse",
    "SearchExperimentInfoResponse",
    "ExperimentsWithUserResponse",
    "CachedExperimentNamesResponse",
    "ExperimentNamesUpdatedWithinResponse",
    "ExperimentsToProposalResponse",
    "PostableExperimentsResponse",
    "PotentiallyActiveUsersResponse",
    "UserGroupsResponse",
    "GlobalRolesResponse",
    "ExperimentStatsResponse",
    "ExperimentDailyDataBreakdownResponse",
    "ApiEndpointsResponse",
    "NamingConventionsResponse",
    "FileManagerFileTypesResponse",
    "ProjectsResponse",
    "GetMatchingUidsResponse",
    "GetMatchingGroupsResponse",
    "GlobalParamsMatchingPrefixResponse",
    "GlobalModalParamDefinitionsResponse",
    "LookupExperimentInUrawiResponse",
    "PocFeedbackExperimentsResponse",
    "EmptyResponse",
    # Response aliases – experiment-level
    "InfoResponse",
    "InternalInfoResponse",
    "HasRoleResponse",
    "CollaboratorsResponse",
    "PosixGroupMembersResponse",
    "SyncCollaboratorsResponse",
    "ElogResponse",
    "ElogCompleteTreeResponse",
    "SearchElogResponse",
    "ElogTagsResponse",
    "ElogEmailsResponse",
    "ElogEmailSubscriptionsResponse",
    "InstrumentElogsResponse",
    "RunsResponse",
    "SingleRunResponse",
    "CurrentRunResponse",
    "RunsForCalibResponse",
    "RunParamDescriptionsResponse",
    "RunParamsForAllRunsResponse",
    "RunsMatchingEditableResponse",
    "MapParamEditableToRunNumsResponse",
    "TagsToRunsResponse",
    "RunsToTagsResponse",
    "RunsWithTagResponse",
    "TagsForRunResponse",
    "RunParamsMatchingPrefixResponse",
    "DaqRunParamsResponse",
    "ModalParamDefinitionsResponse",
    "RunTablesResponse",
    "RunTableSourcesResponse",
    "RunTableDataResponse",
    "FilesResponse",
    "RunFilesResponse",
    "FilesForLiveModeResponse",
    "FilesForLiveModeAtLocationResponse",
    "ExpFilesForLiveModeAtLocationResponse",
    "FileCountsByExtensionResponse",
    "DmLocationsResponse",
    "ShiftsResponse",
    "LatestShiftResponse",
    "SamplesResponse",
    "SingleSampleResponse",
    "CurrentSampleNameResponse",
    "WorkflowDefinitionsResponse",
    "WorkflowTriggersResponse",
    "WorkflowJobsResponse",
    "WorkflowJobDetailsResponse",
    "FeedbackDocumentResponse",
]
