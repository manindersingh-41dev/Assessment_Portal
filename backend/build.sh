#!/usr/bin/env bash
set -euo pipefail

python -m pip install -r requirements.txt

# Run schema changes against Neon’s direct endpoint when it is configured.
if [[ -n "${DATABASE_URL_UNPOOLED:-}" ]]; then
  export DATABASE_URL="$DATABASE_URL_UNPOOLED"
fi

python manage.py migrate --noinput
