#!/usr/bin/env bash
set -euo pipefail
python scripts/check_schema_revision.py
alembic -c database/alembic.ini check
