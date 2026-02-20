#!/usr/bin/env python
"""
Comprehensive API dump script for the explgbk logbook API.

Attempts every GET endpoint and saves each response to a separate JSON file
under ./api_dump/. POST/PUT/DELETE endpoints are skipped to avoid side effects.

Dependencies between endpoints are handled explicitly, e.g. run numbers and
table names are extracted from earlier responses before being used in later calls.

Usage:
    python experiment_dump.py [experiment_name [uid]]

    experiment_name defaults to "rix101332624" if not given.
    uid defaults to the current OS username (getpass.getuser()).
"""

import getpass
import json
import sys
import tarfile
from pathlib import Path
from typing import Dict, List, Optional

import requests
from krtc import KerberosTicket

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://pswww.slac.stanford.edu/ws-kerb/lgbk"
EXPERIMENT_NAME = sys.argv[1] if len(sys.argv) > 1 else "rix101332624"
UID = sys.argv[2] if len(sys.argv) > 2 else getpass.getuser()
OUTPUT_DIR = Path("api_dump")

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

print("Acquiring Kerberos ticket …")
krbheaders = KerberosTicket("HTTP@pswww.slac.stanford.edu").getAuthHeaders()

OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_errors: List[str] = []


def _safe_filename(s: str) -> str:
    """Convert a URL path to a safe filename."""
    return (
        s.strip("/")
        .replace("/", "__")
        .replace("<", "")
        .replace(">", "")
        .replace("?", "__")
    )


def save_json(name: str, data) -> None:
    path = OUTPUT_DIR / f"{name}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  ✓  saved {path}")


def get_binary(
    url_path: str,
    params: Optional[Dict] = None,
    *,
    name: Optional[str] = None,
    ext: str = "bin",
):
    """
    GET BASE_URL + url_path, save the raw binary response.
    Used for endpoints that return binary data (e.g. attachments).
    """
    full_url = f"{BASE_URL}{url_path}"
    file_name = name or _safe_filename(url_path)
    if params:

        def _sanitize(v):
            return str(v).replace("/", "-").replace(" ", "_")

        param_suffix = "__" + "__".join(
            f"{k}={_sanitize(v)}" for k, v in params.items()
        )
        file_name += param_suffix

    try:
        r = requests.get(full_url, headers=krbheaders, params=params, timeout=30)
    except Exception as exc:
        msg = f"NETWORK ERROR  {full_url}: {exc}"
        print(f"  ✗  {msg}")
        _errors.append(msg)
        return None

    if r.status_code != 200:
        msg = f"HTTP {r.status_code}  {full_url}"
        print(f"  ✗  {msg}")
        _errors.append(msg)
        return None

    # Derive extension from Content-Type if possible
    ct = r.headers.get("Content-Type", "")
    if "image/" in ct:
        ext = ct.split("/")[-1].split(";")[0].strip()
    elif "pdf" in ct:
        ext = "pdf"

    path = OUTPUT_DIR / f"{file_name}.{ext}"
    with open(path, "wb") as f:
        f.write(r.content)
    print(f"  ✓  saved {path}")
    return r.content


def get_text(
    url_path: str,
    params: Optional[Dict] = None,
    *,
    name: Optional[str] = None,
    ext: str = "txt",
):
    """
    GET BASE_URL + url_path, save the raw text response, and return the text.
    Used for endpoints that return non-JSON (e.g. CSV).
    """
    full_url = f"{BASE_URL}{url_path}"
    file_name = name or _safe_filename(url_path)
    if params:

        def _sanitize(v):
            return str(v).replace("/", "-").replace(" ", "_")

        param_suffix = "__" + "__".join(
            f"{k}={_sanitize(v)}" for k, v in params.items()
        )
        file_name += param_suffix

    try:
        r = requests.get(full_url, headers=krbheaders, params=params, timeout=30)
    except Exception as exc:
        msg = f"NETWORK ERROR  {full_url}: {exc}"
        print(f"  ✗  {msg}")
        _errors.append(msg)
        return None

    if r.status_code != 200:
        msg = f"HTTP {r.status_code}  {full_url}"
        print(f"  ✗  {msg}")
        _errors.append(msg)
        return None

    path = OUTPUT_DIR / f"{file_name}.{ext}"
    with open(path, "w") as f:
        f.write(r.text)
    print(f"  ✓  saved {path}")
    return r.text


def get(url_path: str, params: Optional[Dict] = None, *, name: Optional[str] = None):
    """
    GET BASE_URL + url_path, save the response JSON, and return the parsed data.

    On any non-200 or parse error the failure is logged to _errors and None is
    returned so the caller can decide whether to skip dependent calls.
    """
    full_url = f"{BASE_URL}{url_path}"
    file_name = name or _safe_filename(url_path)
    if params:

        def _sanitize(v):
            return str(v).replace("/", "-").replace(" ", "_")

        param_suffix = "__" + "__".join(
            f"{k}={_sanitize(v)}" for k, v in params.items()
        )
        file_name += param_suffix

    try:
        r = requests.get(full_url, headers=krbheaders, params=params, timeout=30)
    except Exception as exc:
        msg = f"NETWORK ERROR  {full_url}: {exc}"
        print(f"  ✗  {msg}")
        _errors.append(msg)
        return None

    if r.status_code != 200:
        msg = f"HTTP {r.status_code}  {full_url}"
        print(f"  ✗  {msg}")
        _errors.append(msg)
        return None

    try:
        data = r.json()
    except Exception as exc:
        msg = f"JSON PARSE ERROR  {full_url}: {exc}"
        print(f"  ✗  {msg}")
        _errors.append(msg)
        save_json(file_name + "__raw", {"raw_text": r.text[:4096]})
        return None

    save_json(file_name, data)
    return data


# ---------------------------------------------------------------------------
# Phase 1 – Global / site-level endpoints (no experiment context needed)
# ---------------------------------------------------------------------------

print("\n=== Phase 1: Global endpoints ===\n")

get("/lgbk/ws/empty", name="global__empty")
get("/lgbk/ws/get_cached_experiment_names", name="global__cached_experiment_names")
get(
    "/lgbk/ws/experiment_names_updated_within",
    name="global__experiment_names_updated_within",
)
get("/lgbk/ws/experiments_to_proposal", name="global__experiments_to_proposal")
get(
    "/lgbk/ws/experiments_with_user_as_collaborator",
    params={"uid": UID},
    name="global__experiments_with_user_as_collaborator",
)

get("/lgbk/ws/experiments", name="global__experiments")
get("/lgbk/ws/instruments", name="global__instruments")
get("/lgbk/ws/instrument_station_list", name="global__instrument_station_list")
_active_resp = get("/lgbk/ws/activeexperiments", name="global__activeexperiments")
_active_exps: List[Dict] = (
    _active_resp.get("value", []) if isinstance(_active_resp, dict) else []
)
get("/lgbk/ws/experiment_stats", name="global__experiment_stats")
get(
    "/lgbk/ws/experiment_daily_data_breakdown",
    params={"instrument": "ALL", "report_type": "file_sizes"},
    name="global__experiment_daily_data_breakdown",
)
get("/lgbk/ws/potentiallyactiveusers", name="global__potentiallyactiveusers")
get("/lgbk/ws/usergroups", name="global__usergroups")
get(
    "/lgbk/ws/search_experiment_info",
    params={"search_text": "rix"},
    name="global__search_experiment_info",
)
get("/lgbk/ws/postable_experiments", name="global__postable_experiments")
get("/lgbk/ws/api_endpoints", name="global__api_endpoints")
get("/lgbk/naming_conventions", name="global__naming_conventions")
get("/lgbk/filemanager_file_types", name="global__filemanager_file_types")
get("/lgbk/ws/poc_feedback/schema", name="global__poc_feedback_schema")
get("/lgbk/ws/poc_feedback/experiments", name="global__poc_feedback_experiments")
get("/lgbk/ws/projects", name="global__projects")
get(
    "/lgbk/ws/get_params_matching_prefix",
    params={"prefix": "DAQ"},
    name="global__get_params_matching_prefix",
)
get(
    "/lgbk/get_modal_param_definitions",
    params={"modal_type": "run"},
    name="global__get_modal_param_definitions",
)
get(
    "/lgbk/ws/get_matching_uids",
    params={"uid": UID},
    name="global__get_matching_uids",
)
get(
    "/lgbk/ws/get_matching_groups",
    params={"group_name": "ps-"},
    name="global__get_matching_groups",
)

# lookup_experiment_in_urawi
get(
    "/lgbk/ws/lookup_experiment_in_urawi",
    params={"experiment_name": EXPERIMENT_NAME},
    name="global__lookup_experiment_in_urawi",
)

# Grab instrument list to use for instrument-specific calls later
_instruments_resp = get("/lgbk/ws/instruments", name="global__instruments")
_instruments: List[Dict] = (
    _instruments_resp.get("value", []) if isinstance(_instruments_resp, dict) else []
)
_first_instrument = _instruments[0]["_id"] if _instruments else "RIX"

# Use an instrument that has an active experiment to avoid 500s on this endpoint
_active_instrument = (
    _active_exps[0]["instrument"] if _active_exps else _first_instrument
)

get(
    "/lgbk/ws/activeexperiment_for_instrument_station",
    params={"instrument_name": _active_instrument, "station": 0},
    name="global__activeexperiment_for_instrument_station",
)
get(
    "/lgbk/ws/instrument_switch_history",
    params={"instrument": _first_instrument, "station": 0},
    name="global__instrument_switch_history",
)

get("/lgbk/ws/global_roles", name="global__global_roles")

# ---------------------------------------------------------------------------
# Phase 2 – Experiment-level endpoints
# ---------------------------------------------------------------------------

print(f"\n=== Phase 2: Experiment endpoints (experiment={EXPERIMENT_NAME}) ===\n")

EXP = f"/lgbk/{EXPERIMENT_NAME}"

exp_info_resp = get(f"{EXP}/ws/info", name="exp__info")
get(f"{EXP}/ws/internalinfo", name="exp__internalinfo")
get(
    f"{EXP}/ws/has_role",
    params={"role_fq_name": "LogBook/Editor"},
    name="exp__has_role",
)
get(f"{EXP}/ws/elog", name="exp__elog")
get(f"{EXP}/ws/elog_emails", name="exp__elog_emails")
get(f"{EXP}/ws/elog_email_subscriptions", name="exp__elog_email_subscriptions")
get(f"{EXP}/ws/get_elog_tags", name="exp__elog_tags")
get(f"{EXP}/ws/get_instrument_elogs", name="exp__instrument_elogs")
get(f"{EXP}/ws/search_elog", params={"search_text": "run"}, name="exp__search_elog")
get(f"{EXP}/ws/files", name="exp__files")
get(f"{EXP}/ws/file_counts_by_extension", name="exp__file_counts_by_extension")
get(f"{EXP}/ws/collaborators", name="exp__collaborators")
get(f"{EXP}/ws/exp_posix_group_members", name="exp__posix_group_members")
get(f"{EXP}/ws/samples", name="exp__samples")
get(f"{EXP}/ws/current_sample_name", name="exp__current_sample_name")
get(f"{EXP}/ws/shifts", name="exp__shifts")
get(f"{EXP}/ws/get_latest_shift", name="exp__latest_shift")
get(f"{EXP}/ws/current_run", name="exp__current_run")
get(f"{EXP}/ws/runs_for_calib", name="exp__runs_for_calib")
get(f"{EXP}/ws/dm_locations", name="exp__dm_locations")
get(f"{EXP}/ws/workflow_definitions", name="exp__workflow_definitions")
get(f"{EXP}/ws/workflow_triggers", name="exp__workflow_triggers")
get(f"{EXP}/ws/workflow_jobs", name="exp__workflow_jobs")
get(f"{EXP}/ws/run_param_descriptions", name="exp__run_param_descriptions")
get(f"{EXP}/ws/run_tables", name="exp__run_tables")
get(f"{EXP}/ws/run_table_sources", name="exp__run_table_sources")
get(f"{EXP}/ws/get_tags_to_runs", name="exp__tags_to_runs")
get(f"{EXP}/ws/get_runs_to_tags", name="exp__runs_to_tags")
get(f"{EXP}/ws/get_feedback_document", name="exp__feedback_document")
get(
    f"{EXP}/ws/get_modal_param_definitions",
    params={"modal_type": "run"},
    name="exp__modal_param_definitions",
)
get(
    f"{EXP}/ws/get_runs_with_tag",
    params={"tag": "DARK"},
    name="exp__runs_with_tag_DARK",
)
get(
    f"{EXP}/ws/get_run_params_for_all_runs",
    params={"param_names": "DAQ Detectors/Total"},
    name="exp__run_params_for_all_runs",
)
get(
    f"{EXP}/ws/get_runs_matching_editable",
    params={"param_name": "Comment", "param_value": ".*"},
    name="exp__runs_matching_editable",
)
get(
    f"{EXP}/ws/map_param_editable_to_run_nums",
    params={"param_name": "Comment"},
    name="exp__map_param_editable_to_run_nums",
)
# ---------------------------------------------------------------------------
# Phase 3 – Run-specific endpoints (picks a run number from phase 2)
# ---------------------------------------------------------------------------

print("\n=== Phase 3: Run-specific endpoints ===\n")

runs_resp = get(f"{EXP}/ws/runs", name="exp__runs")
_runs: List[Dict] = runs_resp.get("value", []) if isinstance(runs_resp, dict) else []

if _runs:
    # Use the latest closed run for per-run calls
    closed = [r for r in _runs if r.get("end_time")]
    sample_run = closed[-1] if closed else _runs[-1]
    run_num = sample_run["num"]
    print(f"  Using run {run_num} for per-run calls …")

    RUN = f"{EXP}/ws/{run_num}"

    get(f"{EXP}/ws/runs/{run_num}", name=f"exp__run_{run_num}")
    get(f"{RUN}/files", name=f"exp__run_{run_num}__files")
    get(f"{RUN}/files_for_live_mode", name=f"exp__run_{run_num}__files_for_live_mode")
    get(f"{RUN}/get_tags_for_run", name=f"exp__run_{run_num}__tags")
    get(
        f"{RUN}/get_params_matching_prefix",
        params={"prefix": "DAQ"},
        name=f"exp__run_{run_num}__params_matching_prefix",
    )
    get(f"{RUN}/daq_run_params", name=f"exp__run_{run_num}__daq_run_params")

    # elog for run
    get(
        f"{EXP}/ws/search_elog",
        params={"run_num": str(run_num)},
        name=f"exp__search_elog__run_{run_num}",
    )

    # files_for_live_mode_at_location – needs a valid location name
    # also fetch <run_num>/files_for_live_mode_at_location (done below with location name)
    dm_resp = get(f"{EXP}/ws/dm_locations", name="exp__dm_locations")
    _locations: List[Dict] = (
        dm_resp.get("value", []) if isinstance(dm_resp, dict) else []
    )
    if _locations:
        loc_name = _locations[0]["name"]
        get(
            f"{RUN}/files_for_live_mode_at_location",
            params={"location": loc_name},
            name=f"exp__run_{run_num}__files_live_mode_at_{loc_name}",
        )
        get(
            f"{EXP}/ws/files_for_live_mode_at_location",
            params={"location": loc_name},
            name=f"exp__files_live_mode_at_{loc_name}",
        )
else:
    print("  No runs found – skipping per-run endpoints.")

# ---------------------------------------------------------------------------
# Phase 3b – Attachment downloads (pick first elog entry with an attachment)
# ---------------------------------------------------------------------------

print("\n=== Phase 3b: Attachment download ===\n")

_elog_for_attach = get(f"{EXP}/ws/elog", name="exp__elog")
_elogs_for_attach: List[Dict] = (
    _elog_for_attach.get("value", []) if isinstance(_elog_for_attach, dict) else []
)
_found_attachment = False
for _entry in _elogs_for_attach:
    _attachments = _entry.get("attachments", [])
    if _attachments:
        _entry_id = str(_entry.get("_id", ""))
        _attach_id = str(_attachments[0].get("_id", ""))
        print(f"  Fetching attachment {_attach_id} from entry {_entry_id} …")
        get_binary(
            f"{EXP}/ws/attachment",
            params={"entry_id": _entry_id, "attachment_id": _attach_id},
            name=f"exp__attachment__{_entry_id}__{_attach_id}",
        )
        _found_attachment = True
        break
if not _found_attachment:
    print("  No elog entries with attachments found – skipping.")

# ---------------------------------------------------------------------------
# Phase 3c – Workflow job details (if workflow jobs exist)
# ---------------------------------------------------------------------------

print("\n=== Phase 3c: Workflow job details ===\n")

_wf_jobs_resp = get(f"{EXP}/ws/workflow_jobs", name="exp__workflow_jobs")
_wf_jobs: List[Dict] = (
    _wf_jobs_resp.get("value", []) if isinstance(_wf_jobs_resp, dict) else []
)
if _wf_jobs:
    _sample_job_id = str(_wf_jobs[0].get("_id", ""))
    print(f"  Using workflow job {_sample_job_id} …")
    for _action in ["job_statuses", "job_details", "job_log_file"]:
        get_text(
            f"{EXP}/ws/workflow/{_sample_job_id}/{_action}",
            name=f"exp__wf_job__{_sample_job_id}__{_action}",
        )
else:
    print("  No workflow jobs found – skipping.")

# ---------------------------------------------------------------------------
# Phase 4 – Run table data (picks a table name from phase 2)
# ---------------------------------------------------------------------------

print("\n=== Phase 4: Run table data ===\n")

rt_resp = get(f"{EXP}/ws/run_tables", name="exp__run_tables")
_tables: List[Dict] = rt_resp.get("value", []) if isinstance(rt_resp, dict) else []
for table in _tables[:3]:  # limit to first 3 tables to avoid very large dumps
    tname = table.get("name")
    if tname:
        get(
            f"{EXP}/ws/run_table_data",
            params={"tableName": tname},
            name=f"exp__run_table_data__{tname.replace(' ', '_')}",
        )
        get_text(
            f"{EXP}/ws/runtables/export_as_csv",
            params={"runtable": tname},
            name=f"exp__runtable_csv__{tname.replace(' ', '_')}",
            ext="csv",
        )

# ---------------------------------------------------------------------------
# Phase 5 – Sample details
# ---------------------------------------------------------------------------

print("\n=== Phase 5: Sample details ===\n")

samples_resp = get(f"{EXP}/ws/samples", name="exp__samples")
_samples: List[Dict] = (
    samples_resp.get("value", []) if isinstance(samples_resp, dict) else []
)
for s in _samples[:3]:
    sname = s.get("name")
    if sname:
        get(
            f"{EXP}/ws/samples/{sname}",
            name=f"exp__sample__{sname.replace(' ', '_')}",
        )

# ---------------------------------------------------------------------------
# Phase 6 – Elog tree for a specific entry (optional)
# ---------------------------------------------------------------------------

print("\n=== Phase 6: Elog entry tree ===\n")

elog_resp = get(f"{EXP}/ws/elog", name="exp__elog")
_elogs: List[Dict] = elog_resp.get("value", []) if isinstance(elog_resp, dict) else []
if _elogs:
    entry_id = str(_elogs[0].get("_id", ""))
    if entry_id:
        get(
            f"{EXP}/ws/elog/{entry_id}/complete_elog_tree",
            name="exp__elog__complete_tree",
        )

# ---------------------------------------------------------------------------
# Phase 7 – Project details (iterate over project IDs from Phase 1)
# ---------------------------------------------------------------------------

print("\n=== Phase 7: Project details ===\n")

_projects_resp = get("/lgbk/ws/projects", name="global__projects")
_projects: List[Dict] = (
    _projects_resp.get("value", []) if isinstance(_projects_resp, dict) else []
)
for _prj in _projects[:3]:  # limit to first 3 projects
    _prj_id = str(_prj.get("_id", ""))
    if not _prj_id:
        continue
    print(f"  Project {_prj_id} …")
    get(f"/lgbk/ws/projects/{_prj_id}", name=f"project__{_prj_id}__info")
    _grids_resp = get(
        f"/lgbk/ws/projects/{_prj_id}/grids", name=f"project__{_prj_id}__grids"
    )
    get(
        f"/lgbk/ws/projects/{_prj_id}/sessions",
        name=f"project__{_prj_id}__sessions",
    )
    _grids: List[Dict] = (
        _grids_resp.get("value", []) if isinstance(_grids_resp, dict) else []
    )
    for _grid in _grids[:2]:  # limit to first 2 grids per project
        _grid_id = str(_grid.get("_id", ""))
        if _grid_id:
            get(
                f"/lgbk/ws/projects/{_prj_id}/grids/{_grid_id}",
                name=f"project__{_prj_id}__grid__{_grid_id}",
            )
if not _projects:
    print("  No accessible projects found – skipping.")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print(f"\n{'=' * 60}")
print(f"Dump complete. Files written to: {OUTPUT_DIR.resolve()}")
print(f"Total files: {len(list(OUTPUT_DIR.glob('*.json')))}")
if _errors:
    print(f"\n{len(_errors)} endpoint(s) failed:")
    for e in _errors:
        print(f"  ✗  {e}")
else:
    print("\nAll attempted endpoints succeeded.")

# ---------------------------------------------------------------------------
# Create tarball
# ---------------------------------------------------------------------------

tar_path = Path(f"{EXPERIMENT_NAME}.tar")
with tarfile.open(tar_path, "w") as tar:
    tar.add(OUTPUT_DIR)
print(f"\nArchive created: {tar_path.resolve()}")
print(f"To extract: tar -xf {tar_path} [-C <destination_dir>]")
