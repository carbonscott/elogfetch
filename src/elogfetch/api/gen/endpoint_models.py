"""
Mapping of every GET endpoint URL pattern to its Pydantic response model.

Keys are URL patterns using Python ``{param}`` placeholders.

Values are ``Endpoint`` instances that pair the URL pattern with a Pydantic
response model.  ``None`` is retained for endpoints that return non-JSON
content (binary attachments, CSV exports).

Usage::

    from elogfetch.api.gen.endpoint_models import RUNS, RUN, ENDPOINT_MODELS

    # Named constant — for direct use in client.fetch()
    url = RUNS.url(experiment_name="mfxc00118")

    # Full registry — for introspection / future tooling
    endpoint = ENDPOINT_MODELS.get("/lgbk/{experiment_name}/ws/runs")
"""

from typing import Any

from .endpoint import Endpoint
from .models import (
    ActiveExperimentForStationResponse,
    ActiveExperimentsResponse,
    ApiEndpointsResponse,
    CachedExperimentNamesResponse,
    CollaboratorsResponse,
    CurrentRunResponse,
    CurrentSampleNameResponse,
    DaqRunParamsResponse,
    DmLocationsResponse,
    ElogCompleteTreeResponse,
    ElogEmailsResponse,
    ElogEmailSubscriptionsResponse,
    ElogResponse,
    ElogTagsResponse,
    EmptyResponse,
    ExperimentDailyDataBreakdownResponse,
    ExperimentNamesUpdatedWithinResponse,
    ExperimentsResponse,
    ExperimentStatsResponse,
    ExperimentsToProposalResponse,
    ExperimentsWithUserResponse,
    ExpFilesForLiveModeAtLocationResponse,
    FeedbackDocumentResponse,
    FileCountsByExtensionResponse,
    FileManagerFileTypesResponse,
    FilesForLiveModeAtLocationResponse,
    FilesForLiveModeResponse,
    FilesResponse,
    GetMatchingGroupsResponse,
    GetMatchingUidsResponse,
    GlobalModalParamDefinitionsResponse,
    GlobalParamsMatchingPrefixResponse,
    GlobalRolesResponse,
    HasRoleResponse,
    InfoResponse,
    InstrumentElogsResponse,
    InstrumentsResponse,
    InstrumentStationListResponse,
    InstrumentSwitchHistoryResponse,
    InternalInfoResponse,
    LatestShiftResponse,
    LgbkEmptyResponse,
    LgbkResponse,
    LookupExperimentInUrawiResponse,
    MapParamEditableToRunNumsResponse,
    ModalParamDefinitionsResponse,
    NamingConventionsResponse,
    PocFeedbackExperimentsResponse,
    PocFeedbackSchemaResponse,
    PosixGroupMembersResponse,
    PostableExperimentsResponse,
    PotentiallyActiveUsersResponse,
    ProjectsResponse,
    RunFilesResponse,
    RunParamDescriptionsResponse,
    RunParamsForAllRunsResponse,
    RunParamsMatchingPrefixResponse,
    RunsForCalibResponse,
    RunsMatchingEditableResponse,
    RunsResponse,
    RunsToTagsResponse,
    RunsWithTagResponse,
    RunTableDataResponse,
    RunTableSourcesResponse,
    RunTablesResponse,
    SamplesResponse,
    SearchElogResponse,
    SearchExperimentInfoResponse,
    ShiftsResponse,
    SingleRunResponse,
    SingleSampleResponse,
    SyncCollaboratorsResponse,
    TagsForRunResponse,
    TagsToRunsResponse,
    UserGroupsResponse,
    WorkflowDefinitionsResponse,
    WorkflowJobDetailsResponse,
    WorkflowJobsResponse,
    WorkflowTriggersResponse,
)

# ---------------------------------------------------------------------------
# Named constants — used directly by client.fetch()
# ---------------------------------------------------------------------------

EXPERIMENT_NAMES_UPDATED_WITHIN: Endpoint[ExperimentNamesUpdatedWithinResponse] = (
    Endpoint(
        "/lgbk/ws/experiment_names_updated_within",
        ExperimentNamesUpdatedWithinResponse,
        require_auth=False,
    )
)
EXPERIMENT_INFO: Endpoint[InfoResponse] = Endpoint(
    "/lgbk/{experiment_name}/ws/info",
    InfoResponse,
)
ELOG: Endpoint[ElogResponse] = Endpoint(
    "/lgbk/{experiment_name}/ws/elog",
    ElogResponse,
)
FILES: Endpoint[FilesResponse] = Endpoint(
    "/lgbk/{experiment_name}/ws/files",
    FilesResponse,
)
RUNS: Endpoint[RunsResponse] = Endpoint(
    "/lgbk/{experiment_name}/ws/runs",
    RunsResponse,
)
RUN: Endpoint[SingleRunResponse] = Endpoint(
    "/lgbk/{experiment_name}/ws/runs/{run_num}",
    SingleRunResponse,
)
WORKFLOW_DEFS: Endpoint[WorkflowDefinitionsResponse] = Endpoint(
    "/lgbk/{experiment_name}/ws/workflow_definitions",
    WorkflowDefinitionsResponse,
)

# ---------------------------------------------------------------------------
# Full registry  (pattern → Endpoint | None)
# ``None`` values indicate non-JSON responses (binary or CSV).
# ---------------------------------------------------------------------------

ENDPOINT_MODELS: dict[str, Endpoint | None] = {
    # ------------------------------------------------------------------
    # Global / site-level  (no experiment context)
    # ------------------------------------------------------------------
    # Health check
    "/lgbk/ws/empty": Endpoint("/lgbk/ws/empty", EmptyResponse, require_auth=False),
    # Experiment listings
    "/lgbk/ws/experiments": Endpoint(
        "/lgbk/ws/experiments", ExperimentsResponse, require_auth=False
    ),
    "/lgbk/ws/sorted_experiment_ids": Endpoint(
        "/lgbk/ws/sorted_experiment_ids",
        CachedExperimentNamesResponse,
        require_auth=False,
    ),
    "/lgbk/ws/get_cached_experiment_names": Endpoint(
        "/lgbk/ws/get_cached_experiment_names",
        CachedExperimentNamesResponse,
        require_auth=False,
    ),
    "/lgbk/ws/experiment_names_updated_within": EXPERIMENT_NAMES_UPDATED_WITHIN,
    "/lgbk/ws/experiments_to_proposal": Endpoint(
        "/lgbk/ws/experiments_to_proposal",
        ExperimentsToProposalResponse,
        require_auth=False,
    ),
    "/lgbk/ws/experiments_with_user_as_collaborator": Endpoint(
        "/lgbk/ws/experiments_with_user_as_collaborator",
        ExperimentsWithUserResponse,
        require_auth=False,
    ),
    "/lgbk/ws/search_experiment_info": Endpoint(
        "/lgbk/ws/search_experiment_info",
        SearchExperimentInfoResponse,
        require_auth=False,
    ),
    "/lgbk/ws/ops_search_exp_infos": Endpoint(
        "/lgbk/ws/ops_search_exp_infos", ExperimentsResponse, require_auth=False
    ),
    "/lgbk/ws/postable_experiments": Endpoint(
        "/lgbk/ws/postable_experiments", PostableExperimentsResponse, require_auth=False
    ),
    "/lgbk/ws/lookup_experiment_in_urawi": Endpoint(
        "/lgbk/ws/lookup_experiment_in_urawi",
        LookupExperimentInUrawiResponse,
        require_auth=False,
    ),
    # Instruments
    "/lgbk/ws/instruments": Endpoint(
        "/lgbk/ws/instruments", InstrumentsResponse, require_auth=False
    ),
    "/lgbk/ws/instrument_station_list": Endpoint(
        "/lgbk/ws/instrument_station_list",
        InstrumentStationListResponse,
        require_auth=False,
    ),
    "/lgbk/ws/instrument_switch_history": Endpoint(
        "/lgbk/ws/instrument_switch_history",
        InstrumentSwitchHistoryResponse,
        require_auth=False,
    ),
    # Active experiments
    "/lgbk/ws/activeexperiments": Endpoint(
        "/lgbk/ws/activeexperiments", ActiveExperimentsResponse, require_auth=False
    ),
    "/lgbk/ws/activeexperiment_for_instrument_station": Endpoint(
        "/lgbk/ws/activeexperiment_for_instrument_station",
        ActiveExperimentForStationResponse,
        require_auth=False,
    ),
    # Users / groups
    "/lgbk/ws/potentiallyactiveusers": Endpoint(
        "/lgbk/ws/potentiallyactiveusers",
        PotentiallyActiveUsersResponse,
        require_auth=False,
    ),
    "/lgbk/ws/usergroups": Endpoint(
        "/lgbk/ws/usergroups", UserGroupsResponse, require_auth=False
    ),
    "/lgbk/ws/get_matching_uids": Endpoint(
        "/lgbk/ws/get_matching_uids", GetMatchingUidsResponse, require_auth=False
    ),
    "/lgbk/ws/get_matching_groups": Endpoint(
        "/lgbk/ws/get_matching_groups", GetMatchingGroupsResponse, require_auth=False
    ),
    # Stats & data breakdown
    "/lgbk/ws/experiment_stats": Endpoint(
        "/lgbk/ws/experiment_stats", ExperimentStatsResponse, require_auth=False
    ),
    "/lgbk/ws/experiment_daily_data_breakdown": Endpoint(
        "/lgbk/ws/experiment_daily_data_breakdown",
        ExperimentDailyDataBreakdownResponse,
        require_auth=False,
    ),
    # Roles
    "/lgbk/ws/global_roles": Endpoint(
        "/lgbk/ws/global_roles", GlobalRolesResponse, require_auth=False
    ),
    # Params / modal defs
    "/lgbk/ws/get_params_matching_prefix": Endpoint(
        "/lgbk/ws/get_params_matching_prefix",
        GlobalParamsMatchingPrefixResponse,
        require_auth=False,
    ),
    "/lgbk/get_modal_param_definitions": Endpoint(
        "/lgbk/get_modal_param_definitions",
        GlobalModalParamDefinitionsResponse,
        require_auth=False,
    ),
    # API introspection
    "/lgbk/ws/api_endpoints": Endpoint(
        "/lgbk/ws/api_endpoints", ApiEndpointsResponse, require_auth=False
    ),
    "/lgbk/naming_conventions": Endpoint(
        "/lgbk/naming_conventions", NamingConventionsResponse, require_auth=False
    ),
    "/lgbk/filemanager_file_types": Endpoint(
        "/lgbk/filemanager_file_types", FileManagerFileTypesResponse, require_auth=False
    ),
    # POC feedback
    "/lgbk/ws/poc_feedback/schema": Endpoint(
        "/lgbk/ws/poc_feedback/schema", PocFeedbackSchemaResponse, require_auth=False
    ),
    "/lgbk/ws/poc_feedback/experiments": Endpoint(
        "/lgbk/ws/poc_feedback/experiments",
        PocFeedbackExperimentsResponse,
        require_auth=False,
    ),
    # Projects
    "/lgbk/ws/projects": Endpoint(
        "/lgbk/ws/projects", ProjectsResponse, require_auth=False
    ),
    "/lgbk/ws/projects/{prjid}": Endpoint(
        "/lgbk/ws/projects/{prjid}", LgbkResponse[Any], require_auth=False
    ),
    "/lgbk/ws/projects/{prjid}/grids": Endpoint(
        "/lgbk/ws/projects/{prjid}/grids", LgbkResponse[Any], require_auth=False
    ),
    "/lgbk/ws/projects/{prjid}/grids/{gridid}": Endpoint(
        "/lgbk/ws/projects/{prjid}/grids/{gridid}",
        LgbkResponse[Any],
        require_auth=False,
    ),
    "/lgbk/ws/projects/{prjid}/sessions": Endpoint(
        "/lgbk/ws/projects/{prjid}/sessions", LgbkResponse[Any], require_auth=False
    ),
    # Cache management (admin)
    "/lgbk/ws/reload_experiment_cache": Endpoint(
        "/lgbk/ws/reload_experiment_cache", LgbkEmptyResponse, require_auth=False
    ),
    "/lgbk/ws/reload_named_cache": Endpoint(
        "/lgbk/ws/reload_named_cache", LgbkEmptyResponse, require_auth=False
    ),
    "/lgbk/ws/rebuild_experiment_cache_for_experiment": Endpoint(
        "/lgbk/ws/rebuild_experiment_cache_for_experiment",
        LgbkEmptyResponse,
        require_auth=False,
    ),
    # ------------------------------------------------------------------
    # Experiment-level  (/lgbk/{experiment_name}/ws/...)
    # ------------------------------------------------------------------
    # Core experiment metadata
    "/lgbk/{experiment_name}/ws/info": EXPERIMENT_INFO,
    "/lgbk/{experiment_name}/ws/internalinfo": Endpoint(
        "/lgbk/{experiment_name}/ws/internalinfo", InternalInfoResponse
    ),
    "/lgbk/{experiment_name}/ws/has_role": Endpoint(
        "/lgbk/{experiment_name}/ws/has_role", HasRoleResponse
    ),
    "/lgbk/{experiment_name}/ws/get_modal_param_definitions": Endpoint(
        "/lgbk/{experiment_name}/ws/get_modal_param_definitions",
        ModalParamDefinitionsResponse,
    ),
    "/lgbk/{experiment_name}/ws/get_feedback_document": Endpoint(
        "/lgbk/{experiment_name}/ws/get_feedback_document", FeedbackDocumentResponse
    ),
    # Collaborators / roles
    "/lgbk/{experiment_name}/ws/collaborators": Endpoint(
        "/lgbk/{experiment_name}/ws/collaborators", CollaboratorsResponse
    ),
    "/lgbk/{experiment_name}/ws/exp_posix_group_members": Endpoint(
        "/lgbk/{experiment_name}/ws/exp_posix_group_members", PosixGroupMembersResponse
    ),
    "/lgbk/{experiment_name}/ws/sync_posix_group": Endpoint(
        "/lgbk/{experiment_name}/ws/sync_posix_group", SyncCollaboratorsResponse
    ),
    "/lgbk/{experiment_name}/ws/sync_collaborators_with_user_portal": Endpoint(
        "/lgbk/{experiment_name}/ws/sync_collaborators_with_user_portal",
        SyncCollaboratorsResponse,
    ),
    # Elog
    "/lgbk/{experiment_name}/ws/elog": ELOG,
    "/lgbk/{experiment_name}/ws/elog/{entry_id}/complete_elog_tree": Endpoint(
        "/lgbk/{experiment_name}/ws/elog/{entry_id}/complete_elog_tree",
        ElogCompleteTreeResponse,
    ),
    "/lgbk/{experiment_name}/ws/search_elog": Endpoint(
        "/lgbk/{experiment_name}/ws/search_elog", SearchElogResponse
    ),
    "/lgbk/{experiment_name}/ws/get_elog_tags": Endpoint(
        "/lgbk/{experiment_name}/ws/get_elog_tags", ElogTagsResponse
    ),
    "/lgbk/{experiment_name}/ws/elog_emails": Endpoint(
        "/lgbk/{experiment_name}/ws/elog_emails", ElogEmailsResponse
    ),
    "/lgbk/{experiment_name}/ws/elog_email_subscriptions": Endpoint(
        "/lgbk/{experiment_name}/ws/elog_email_subscriptions",
        ElogEmailSubscriptionsResponse,
    ),
    "/lgbk/{experiment_name}/ws/elog_email_subscribe": Endpoint(
        "/lgbk/{experiment_name}/ws/elog_email_subscribe", LgbkEmptyResponse
    ),
    "/lgbk/{experiment_name}/ws/elog_email_unsubscribe": Endpoint(
        "/lgbk/{experiment_name}/ws/elog_email_unsubscribe", LgbkEmptyResponse
    ),
    "/lgbk/{experiment_name}/ws/get_instrument_elogs": Endpoint(
        "/lgbk/{experiment_name}/ws/get_instrument_elogs", InstrumentElogsResponse
    ),
    "/lgbk/{experiment_name}/ws/cross_post_elogs": Endpoint(
        "/lgbk/{experiment_name}/ws/cross_post_elogs", ElogResponse
    ),
    # Attachments  (binary response – no JSON model)
    "/lgbk/{experiment_name}/ws/attachment": None,
    "/lgbk/{experiment_name}/ws/ext_preview/{path}": None,
    # Runs
    "/lgbk/{experiment_name}/ws/runs": RUNS,
    "/lgbk/{experiment_name}/ws/runs/{run_num}": RUN,
    "/lgbk/{experiment_name}/ws/current_run": Endpoint(
        "/lgbk/{experiment_name}/ws/current_run", CurrentRunResponse
    ),
    "/lgbk/{experiment_name}/ws/runs_for_calib": Endpoint(
        "/lgbk/{experiment_name}/ws/runs_for_calib", RunsForCalibResponse
    ),
    "/lgbk/{experiment_name}/ws/run_param_descriptions": Endpoint(
        "/lgbk/{experiment_name}/ws/run_param_descriptions",
        RunParamDescriptionsResponse,
    ),
    "/lgbk/{experiment_name}/ws/get_run_params_for_all_runs": Endpoint(
        "/lgbk/{experiment_name}/ws/get_run_params_for_all_runs",
        RunParamsForAllRunsResponse,
    ),
    "/lgbk/{experiment_name}/ws/get_runs_matching_editable": Endpoint(
        "/lgbk/{experiment_name}/ws/get_runs_matching_editable",
        RunsMatchingEditableResponse,
    ),
    "/lgbk/{experiment_name}/ws/get_tags_to_runs": Endpoint(
        "/lgbk/{experiment_name}/ws/get_tags_to_runs", TagsToRunsResponse
    ),
    "/lgbk/{experiment_name}/ws/get_runs_to_tags": Endpoint(
        "/lgbk/{experiment_name}/ws/get_runs_to_tags", RunsToTagsResponse
    ),
    "/lgbk/{experiment_name}/ws/get_runs_with_tag": Endpoint(
        "/lgbk/{experiment_name}/ws/get_runs_with_tag", RunsWithTagResponse
    ),
    "/lgbk/{experiment_name}/ws/map_param_editable_to_run_nums": Endpoint(
        "/lgbk/{experiment_name}/ws/map_param_editable_to_run_nums",
        MapParamEditableToRunNumsResponse,
    ),
    # Per-run sub-endpoints
    "/lgbk/{experiment_name}/ws/{run_num}/files": Endpoint(
        "/lgbk/{experiment_name}/ws/{run_num}/files", RunFilesResponse
    ),
    "/lgbk/{experiment_name}/ws/{run_num}/files_for_live_mode": Endpoint(
        "/lgbk/{experiment_name}/ws/{run_num}/files_for_live_mode",
        FilesForLiveModeResponse,
    ),
    "/lgbk/{experiment_name}/ws/{run_num}/files_for_live_mode_at_location": Endpoint(
        "/lgbk/{experiment_name}/ws/{run_num}/files_for_live_mode_at_location",
        FilesForLiveModeAtLocationResponse,
    ),
    "/lgbk/{experiment_name}/ws/{run_num}/get_tags_for_run": Endpoint(
        "/lgbk/{experiment_name}/ws/{run_num}/get_tags_for_run", TagsForRunResponse
    ),
    "/lgbk/{experiment_name}/ws/{run_num}/get_params_matching_prefix": Endpoint(
        "/lgbk/{experiment_name}/ws/{run_num}/get_params_matching_prefix",
        RunParamsMatchingPrefixResponse,
    ),
    "/lgbk/{experiment_name}/ws/{run_num}/daq_run_params": Endpoint(
        "/lgbk/{experiment_name}/ws/{run_num}/daq_run_params", DaqRunParamsResponse
    ),
    # Run tables
    "/lgbk/{experiment_name}/ws/run_tables": Endpoint(
        "/lgbk/{experiment_name}/ws/run_tables", RunTablesResponse
    ),
    "/lgbk/{experiment_name}/ws/run_table_sources": Endpoint(
        "/lgbk/{experiment_name}/ws/run_table_sources", RunTableSourcesResponse
    ),
    "/lgbk/{experiment_name}/ws/run_table_data": Endpoint(
        "/lgbk/{experiment_name}/ws/run_table_data", RunTableDataResponse
    ),
    "/lgbk/{experiment_name}/ws/runtables/export_as_csv": None,  # CSV text
    # Files
    "/lgbk/{experiment_name}/ws/files": FILES,
    "/lgbk/{experiment_name}/ws/files_for_live_mode_at_location": Endpoint(
        "/lgbk/{experiment_name}/ws/files_for_live_mode_at_location",
        ExpFilesForLiveModeAtLocationResponse,
    ),
    "/lgbk/{experiment_name}/ws/file_counts_by_extension": Endpoint(
        "/lgbk/{experiment_name}/ws/file_counts_by_extension",
        FileCountsByExtensionResponse,
    ),
    "/lgbk/{experiment_name}/ws/file_available_at_location": Endpoint(
        "/lgbk/{experiment_name}/ws/file_available_at_location", LgbkEmptyResponse
    ),
    # DM locations
    "/lgbk/{experiment_name}/ws/dm_locations": Endpoint(
        "/lgbk/{experiment_name}/ws/dm_locations", DmLocationsResponse
    ),
    # Shifts
    "/lgbk/{experiment_name}/ws/shifts": Endpoint(
        "/lgbk/{experiment_name}/ws/shifts", ShiftsResponse
    ),
    "/lgbk/{experiment_name}/ws/get_latest_shift": Endpoint(
        "/lgbk/{experiment_name}/ws/get_latest_shift", LatestShiftResponse
    ),
    # Samples
    "/lgbk/{experiment_name}/ws/samples": Endpoint(
        "/lgbk/{experiment_name}/ws/samples", SamplesResponse
    ),
    "/lgbk/{experiment_name}/ws/samples/": Endpoint(
        "/lgbk/{experiment_name}/ws/samples/", SamplesResponse
    ),
    "/lgbk/{experiment_name}/ws/samples/{sample_name}": Endpoint(
        "/lgbk/{experiment_name}/ws/samples/{sample_name}", SingleSampleResponse
    ),
    "/lgbk/{experiment_name}/ws/current_sample_name": Endpoint(
        "/lgbk/{experiment_name}/ws/current_sample_name", CurrentSampleNameResponse
    ),
    # Workflow
    "/lgbk/{experiment_name}/ws/workflow_definitions": WORKFLOW_DEFS,
    "/lgbk/{experiment_name}/ws/workflow_triggers": Endpoint(
        "/lgbk/{experiment_name}/ws/workflow_triggers", WorkflowTriggersResponse
    ),
    "/lgbk/{experiment_name}/ws/workflow_jobs": Endpoint(
        "/lgbk/{experiment_name}/ws/workflow_jobs", WorkflowJobsResponse
    ),
    "/lgbk/{experiment_name}/ws/workflow/{job_id}/{action}": Endpoint(
        "/lgbk/{experiment_name}/ws/workflow/{job_id}/{action}",
        WorkflowJobDetailsResponse,
    ),
    # Misc / admin
    "/lgbk/{experiment_name}/ws/generate_arp_token": Endpoint(
        "/lgbk/{experiment_name}/ws/generate_arp_token", LgbkResponse[Any]
    ),
    # ------------------------------------------------------------------
    # Run control  (/run_control/{experiment_name}/ws/...)
    # ------------------------------------------------------------------
    "/run_control/{experiment_name}/ws/current_run": Endpoint(
        "/run_control/{experiment_name}/ws/current_run", CurrentRunResponse
    ),
}
