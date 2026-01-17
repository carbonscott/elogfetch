# Example Scripts

This directory contains example wrapper scripts that you can copy and customize
for your deployment environment.

## periodic_update.sh

Wrapper script for automated database updates with:

- **Update frequency checking** - Skip if database was updated recently
- **Incremental updates** - Only update experiments that changed
- **Deployment** - Copy database to production location
- **Cron-friendly** - Logging with timestamps

### Quick Start

1. Copy to your working directory:
   ```bash
   cp examples/periodic_update.sh ~/elog-updates/
   cd ~/elog-updates/
   chmod +x periodic_update.sh
   ```

2. Edit the configuration section at the top of the script:
   ```bash
   # Edit these for your environment
   DEPLOY_PATH="/path/to/production/database.db"
   UPDATE_FREQUENCY_HOURS=6
   HOURS_LOOKBACK=168
   ```

3. Test with dry-run:
   ```bash
   ./periodic_update.sh --dry-run
   ```

4. Run manually:
   ```bash
   ./periodic_update.sh
   ```

### Command Line Options

```
./periodic_update.sh [--force] [--skip-deploy] [--dry-run]

Options:
  --force        Force update regardless of frequency check
  --skip-deploy  Skip deployment step
  --dry-run      Show what would be done without making changes
  --help         Show help message
```

### Environment Variables

Instead of editing the script, you can override settings via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ELOGFETCH` | `elogfetch` | Path to elogfetch command |
| `DB_DIR` | Current directory | Directory for database files |
| `DEPLOY_PATH` | (empty) | Path to deploy database |
| `UPDATE_FREQUENCY_HOURS` | `6` | Skip if updated within N hours |
| `HOURS_LOOKBACK` | `168` | Hours to look back (168 = 7 days) |
| `PARALLEL_JOBS` | `10` | Number of parallel fetch jobs |
| `EXCLUDE_PATTERNS` | (empty) | Space-separated patterns: `"txi* asc*"` |

Example using environment variables:
```bash
DEPLOY_PATH=/path/to/prod.db HOURS_LOOKBACK=24 ./periodic_update.sh
```

### Cron Setup

Run every 3 hours (will skip if last update was within 6 hours):

```bash
# Edit crontab
crontab -e

# Add this line:
0 */3 * * * cd ~/elog-updates && ./periodic_update.sh >> update.log 2>&1
```

### Typical Production Setup

```bash
# Create a directory for updates
mkdir -p ~/elog-production
cd ~/elog-production

# Copy and customize the script
cp /path/to/elogfetch/examples/periodic_update.sh .

# Edit configuration
vim periodic_update.sh
# Set DEPLOY_PATH, EXCLUDE_PATTERNS, etc.

# Test
./periodic_update.sh --dry-run
./periodic_update.sh --skip-deploy

# Set up cron
crontab -e
# 0 */3 * * * cd ~/elog-production && ./periodic_update.sh >> update.log 2>&1
```
