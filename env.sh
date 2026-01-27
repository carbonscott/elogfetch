# elog-copilot (elogfetch) environment setup
# Source this file before running elogfetch:  source env.sh

# Auto-detect project directory
export ELOG_COPILOT_APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Python from conda env with krtc (required for Kerberos auth)
export UV_PYTHON="${UV_PYTHON:-/sdf/group/lcls/ds/ana/sw/conda1/inst/envs/ana-4.0.62-py3/bin/python}"

# UV cache
export UV_CACHE_DIR="${UV_CACHE_DIR:-$ELOG_COPILOT_APP_DIR/.uv-cache}"

# Database directory (override in env.local for deployments)
export ELOG_COPILOT_DATA_DIR="${ELOG_COPILOT_DATA_DIR:-$ELOG_COPILOT_APP_DIR}"

# Deploy path for canonical DB symlink (override in env.local)
export ELOG_COPILOT_DEPLOY_PATH="${ELOG_COPILOT_DEPLOY_PATH:-}"

# Kerberos password file (override in env.local)
export KRB5_PASSWORD_FILE="${KRB5_PASSWORD_FILE:-}"
export KRB5_PRINCIPAL="${KRB5_PRINCIPAL:-cwang31@SLAC.STANFORD.EDU}"

# Source local overrides if present
if [[ -f "$ELOG_COPILOT_APP_DIR/env.local" ]]; then
    source "$ELOG_COPILOT_APP_DIR/env.local"
fi
