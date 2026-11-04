#!/usr/bin/env bash
set -euo pipefail
# Uso: bash scripts/set_issue_status.sh <ITEM_ID_DEL_PROJECT> <STATUS_OPTION_ID>
# IDs obtenidos con:
# gh project item-list 3 --owner mariaherrerosanchez --format json
# gh project field-list 3 --owner mariaherrerosanchez --format json
if [[ $# -ne 2 ]]; then
  echo 'Uso: bash scripts/set_issue_status.sh <ITEM_ID_DEL_PROJECT> <STATUS_OPTION_ID>'
  echo 'Consulta primero los IDs con gh project item-list / field-list (ver comentarios del script).'
  exit 2
fi
FIELD_ID="$(gh project field-list 3 --owner mariaherrerosanchez --format json --jq '.fields[] | select(.name=="Status") | .id')"
if [[ -z "$FIELD_ID" ]]; then echo 'No se encontró el campo Status'; exit 1; fi
gh project item-edit --project-id PVT_kwHOELrWYM4BnV_s --id "$1" --field-id "$FIELD_ID" --single-select-option-id "$2"
