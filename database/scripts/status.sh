#!/usr/bin/env bash
set -euo pipefail
alembic -c database/alembic.ini current
alembic -c database/alembic.ini heads
