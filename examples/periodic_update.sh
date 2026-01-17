#!/bin/bash
# Periodic update wrapper for fetch-elog
# Copy this file to your working directory and customize the configuration below.
#
# Handles: frequency checking, deployment, logging
#
# Usage: ./periodic_update.sh [--force] [--skip-deploy] [--dry-run]
#
# Cron example (run every 3 hours, update if 6+ hours since last):
#   0 */3 * * * cd ~/elog-updates && ./periodic_update.sh >> update.log 2>&1

set -e

# ============================================================
# Configuration - EDIT THESE FOR YOUR ENVIRONMENT
# ============================================================
# Path to fetch-elog command (default: find in PATH)
FETCH_ELOG="${FETCH_ELOG:-fetch-elog}"

# Directory for database files (default: current directory)
DB_DIR="${DB_DIR:-$(pwd)}"

# Optional: Deploy database to this path after update
# Leave empty to skip deployment
DEPLOY_PATH="${DEPLOY_PATH:-}"

# Update settings
UPDATE_FREQUENCY_HOURS="${UPDATE_FREQUENCY_HOURS:-6}"    # Skip if updated within N hours
HOURS_LOOKBACK="${HOURS_LOOKBACK:-168}"                  # How far back to look (168 = 7 days)
PARALLEL_JOBS="${PARALLEL_JOBS:-10}"                     # Number of parallel fetch jobs
EXCLUDE_PATTERNS="${EXCLUDE_PATTERNS:-}"                 # Space-separated patterns: "txi* asc*"

# ============================================================
# Parse arguments
# ============================================================
FORCE=false
SKIP_DEPLOY=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE=true
            shift
            ;;
        --skip-deploy)
            SKIP_DEPLOY=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--force] [--skip-deploy] [--dry-run]"
            echo ""
            echo "Options:"
            echo "  --force        Force update regardless of frequency check"
            echo "  --skip-deploy  Skip deployment step"
            echo "  --dry-run      Show what would be done without making changes"
            echo ""
            echo "Environment variables:"
            echo "  FETCH_ELOG              Path to fetch-elog command"
            echo "  DB_DIR                  Directory for database files"
            echo "  DEPLOY_PATH             Path to deploy database (optional)"
            echo "  UPDATE_FREQUENCY_HOURS  Hours between updates (default: 6)"
            echo "  HOURS_LOOKBACK          Hours to look back (default: 168)"
            echo "  PARALLEL_JOBS           Parallel fetch jobs (default: 10)"
            echo "  EXCLUDE_PATTERNS        Patterns to exclude (e.g., 'txi* asc*')"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--force] [--skip-deploy] [--dry-run]"
            exit 1
            ;;
    esac
done

# ============================================================
# Functions
# ============================================================
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

find_latest_db() {
    # Find the most recent elog_*.db file
    ls -t "$DB_DIR"/elog_*.db 2>/dev/null | head -1
}

check_update_needed() {
    local latest_db="$1"

    if [[ -z "$latest_db" ]] || [[ ! -f "$latest_db" ]]; then
        log "No existing database found - update needed"
        return 0  # Update needed
    fi

    # Get modification time in seconds since epoch
    local db_mtime=$(stat -c %Y "$latest_db" 2>/dev/null || stat -f %m "$latest_db")
    local now=$(date +%s)
    local age_hours=$(( (now - db_mtime) / 3600 ))

    log "Latest database: $latest_db"
    log "Age: ${age_hours} hours (threshold: ${UPDATE_FREQUENCY_HOURS} hours)"

    if [[ $age_hours -ge $UPDATE_FREQUENCY_HOURS ]]; then
        log "Update needed (${age_hours}h >= ${UPDATE_FREQUENCY_HOURS}h)"
        return 0  # Update needed
    else
        local next_update=$(( UPDATE_FREQUENCY_HOURS - age_hours ))
        log "Update not needed yet (next update in ~${next_update} hours)"
        return 1  # Update not needed
    fi
}

# ============================================================
# Main
# ============================================================
log "========================================"
log "Periodic Update Starting"
log "========================================"
log "DB_DIR: $DB_DIR"
log "FETCH_ELOG: $FETCH_ELOG"

# Verify fetch-elog is available
if ! command -v "$FETCH_ELOG" &> /dev/null; then
    log "ERROR: fetch-elog command not found: $FETCH_ELOG"
    log "Make sure fetch-elog is installed and in your PATH, or set FETCH_ELOG"
    exit 1
fi

# Find latest database
LATEST_DB=$(find_latest_db)

# Check if update is needed
if [[ "$FORCE" == "true" ]]; then
    log "Force update requested"
elif ! check_update_needed "$LATEST_DB"; then
    log "Skipping update (use --force to override)"
    exit 0
fi

# Dry run mode
if [[ "$DRY_RUN" == "true" ]]; then
    log "DRY RUN MODE - would execute:"
    log "  $FETCH_ELOG update --incremental --hours $HOURS_LOOKBACK --parallel $PARALLEL_JOBS --output-dir $DB_DIR"
    if [[ -n "$EXCLUDE_PATTERNS" ]]; then
        for pattern in $EXCLUDE_PATTERNS; do
            log "    --exclude '$pattern'"
        done
    fi
    if [[ -n "$DEPLOY_PATH" ]] && [[ "$SKIP_DEPLOY" != "true" ]]; then
        log "  Deploy to: $DEPLOY_PATH"
    fi
    exit 0
fi

# Build exclude arguments
EXCLUDE_ARGS=""
if [[ -n "$EXCLUDE_PATTERNS" ]]; then
    for pattern in $EXCLUDE_PATTERNS; do
        EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude '$pattern'"
    done
fi

# Run fetch-elog update
log "Running fetch-elog update..."
eval "$FETCH_ELOG update --incremental --hours $HOURS_LOOKBACK --parallel $PARALLEL_JOBS --output-dir $DB_DIR $EXCLUDE_ARGS"

# Find the newly created database
NEW_DB=$(find_latest_db)
if [[ -z "$NEW_DB" ]]; then
    log "ERROR: No database found after update"
    exit 1
fi

log "New database: $NEW_DB"
log "Size: $(du -h "$NEW_DB" | cut -f1)"

# Deploy
if [[ "$SKIP_DEPLOY" == "true" ]]; then
    log "Skipping deployment (--skip-deploy)"
elif [[ -n "$DEPLOY_PATH" ]]; then
    log "Deploying to: $DEPLOY_PATH"
    # Use cat for atomic deployment
    cat "$NEW_DB" > "$DEPLOY_PATH"
    log "Deployment complete"
else
    log "No DEPLOY_PATH set, skipping deployment"
fi

log "========================================"
log "Periodic Update Complete"
log "========================================"
