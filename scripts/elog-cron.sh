#!/bin/bash
#
# elog-cron.sh — Cron wrapper for elog-copilot (elogfetch)
#
# Usage:
#   ./elog-cron.sh status              Show cron and data status
#   ./elog-cron.sh enable              Add cron entry on sdfcron001
#   ./elog-cron.sh disable             Remove cron entry from sdfcron001
#   ./elog-cron.sh run [OPTIONS]       Run update now (with Kerberos init)
#   ./elog-cron.sh test [OPTIONS]      Dry run (no DB changes)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Source env.sh (sets ELOG_COPILOT_APP_DIR, ELOG_COPILOT_DATA_DIR, etc.)
source "$PROJECT_DIR/env.sh"

# Cron configuration
CRON_NODE="${CRON_NODE:-sdfcron001}"
CRON_SCHEDULE="${CRON_SCHEDULE:-0 */6 * * *}"
CRON_LOG="${CRON_LOG:-$ELOG_COPILOT_DATA_DIR/cron.log}"
CRON_MARKER="elog-cron.sh"

# elogfetch settings
HOURS_LOOKBACK="${HOURS_LOOKBACK:-168}"
PARALLEL_JOBS="${PARALLEL_JOBS:-10}"
KEEP_DB_COUNT="${KEEP_DB_COUNT:-8}"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

ensure_kerberos() {
    # If we already have a valid ticket, skip
    if klist -s 2>/dev/null; then
        log "Kerberos ticket valid"
        return 0
    fi

    # Try password file
    if [[ -n "${KRB5_PASSWORD_FILE:-}" ]] && [[ -f "$KRB5_PASSWORD_FILE" ]]; then
        log "Initializing Kerberos from password file..."
        kinit "$KRB5_PRINCIPAL" < "$KRB5_PASSWORD_FILE"
        log "Kerberos ticket obtained for $KRB5_PRINCIPAL"
        return 0
    fi

    log "ERROR: No valid Kerberos ticket and no password file configured"
    log "  Either run 'kinit' manually, or set KRB5_PASSWORD_FILE in env.local"
    return 1
}

update_symlink() {
    # Find the latest elog_*.db file
    local latest_db
    latest_db=$(ls -t "$ELOG_COPILOT_DATA_DIR"/elog_*.db 2>/dev/null | head -1)

    if [[ -z "$latest_db" ]]; then
        log "ERROR: No elog_*.db found in $ELOG_COPILOT_DATA_DIR"
        return 1
    fi

    local db_basename
    db_basename=$(basename "$latest_db")

    log "Updating symlink: elog-copilot.db -> $db_basename"
    ln -sf "$db_basename" "$ELOG_COPILOT_DATA_DIR/elog-copilot.db"
}

cleanup_old_dbs() {
    # Keep only the N most recent elog_*.db files, delete the rest
    local db_files
    db_files=$(ls -t "$ELOG_COPILOT_DATA_DIR"/elog_*.db 2>/dev/null)

    if [[ -z "$db_files" ]]; then
        return 0
    fi

    local count=0
    while IFS= read -r db_file; do
        count=$((count + 1))
        if [[ $count -gt $KEEP_DB_COUNT ]]; then
            log "Removing old database: $(basename "$db_file")"
            rm -f "$db_file"
        fi
    done <<< "$db_files"
}

run_elogfetch() {
    local extra_args=("$@")

    # Activate venv
    source "$ELOG_COPILOT_APP_DIR/.venv/bin/activate"

    log "Running: elogfetch update --incremental --hours $HOURS_LOOKBACK --parallel $PARALLEL_JOBS --output-dir $ELOG_COPILOT_DATA_DIR ${extra_args[*]:-}"
    elogfetch update \
        --incremental \
        --hours "$HOURS_LOOKBACK" \
        --parallel "$PARALLEL_JOBS" \
        --output-dir "$ELOG_COPILOT_DATA_DIR" \
        "${extra_args[@]}"

    deactivate 2>/dev/null || true
}

# --- Commands ---

cmd_status() {
    echo "=== Cron Status (on $CRON_NODE) ==="
    if ssh "$CRON_NODE" "crontab -l 2>/dev/null" 2>/dev/null | grep -q "$CRON_MARKER"; then
        echo "Cron: ENABLED"
        ssh "$CRON_NODE" "crontab -l" 2>/dev/null | grep "$CRON_MARKER"
    else
        echo "Cron: DISABLED (or cannot reach $CRON_NODE)"
    fi

    echo ""
    echo "=== Kerberos Status ==="
    if klist -s 2>/dev/null; then
        echo "Ticket: VALID"
        klist 2>/dev/null | head -5
    else
        echo "Ticket: EXPIRED or MISSING"
    fi

    echo ""
    echo "=== Data Directory ==="
    echo "Path: $ELOG_COPILOT_DATA_DIR"
    if [[ -L "$ELOG_COPILOT_DATA_DIR/elog-copilot.db" ]]; then
        echo "Symlink: elog-copilot.db -> $(readlink "$ELOG_COPILOT_DATA_DIR/elog-copilot.db")"
    fi
    ls -lh "$ELOG_COPILOT_DATA_DIR"/elog_*.db 2>/dev/null | tail -5 || echo "(no databases)"

    echo ""
    echo "=== Recent Log Entries ==="
    if [[ -f "$CRON_LOG" ]]; then
        tail -10 "$CRON_LOG"
    else
        echo "(no log file yet)"
    fi
}

cmd_enable() {
    local cron_entry="$CRON_SCHEDULE $SCRIPT_DIR/elog-cron.sh run >> $CRON_LOG 2>&1"

    echo "Enabling cron on $CRON_NODE..."
    echo "Schedule: $CRON_SCHEDULE"
    echo "Entry: $cron_entry"

    ssh "$CRON_NODE" bash -c "'
        # Remove old entry if exists
        if crontab -l 2>/dev/null | grep -q \"$CRON_MARKER\"; then
            echo \"Removing old entry first\"
            crontab -l | grep -v \"$CRON_MARKER\" | crontab -
        fi
        # Add new entry
        (crontab -l 2>/dev/null; echo \"$cron_entry\") | crontab -
        echo \"Cron entry added:\"
        crontab -l | grep \"$CRON_MARKER\" || true
    '"
}

cmd_disable() {
    echo "Disabling cron on $CRON_NODE..."
    ssh "$CRON_NODE" bash -c "'
        if crontab -l 2>/dev/null | grep -q \"$CRON_MARKER\"; then
            crontab -l | grep -v \"$CRON_MARKER\" | crontab -
            echo \"Cron entry removed\"
        else
            echo \"No cron entry found\"
        fi
    '"
}

cmd_run() {
    log "========================================"
    log "Elog-Copilot Cron Update Starting"
    log "========================================"
    log "APP_DIR: $ELOG_COPILOT_APP_DIR"
    log "DATA_DIR: $ELOG_COPILOT_DATA_DIR"

    ensure_kerberos || exit 1
    run_elogfetch "$@"
    update_symlink
    cleanup_old_dbs

    log "========================================"
    log "Elog-Copilot Cron Update Complete"
    log "========================================"
}

cmd_test() {
    log "Test mode (dry run)..."
    ensure_kerberos || exit 1
    run_elogfetch --dry-run "$@"
}

# --- Main ---
if [[ $# -lt 1 ]]; then
    echo "Usage: $(basename "$0") {status|enable|disable|run|test} [OPTIONS]"
    exit 1
fi

COMMAND="$1"
shift

case "$COMMAND" in
    status)  cmd_status ;;
    enable)  cmd_enable "$@" ;;
    disable) cmd_disable ;;
    run)     cmd_run "$@" ;;
    test)    cmd_test "$@" ;;
    *)       echo "Unknown command: $COMMAND" >&2; exit 1 ;;
esac
