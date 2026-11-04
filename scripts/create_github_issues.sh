#!/usr/bin/env bash
set -euo pipefail
# Por defecto solo muestra una vista previa. Para crear o actualizar: bash scripts/create_github_issues.sh --apply
cd "$(dirname "$0")/.."
python scripts/sync_issues.py "$@"
