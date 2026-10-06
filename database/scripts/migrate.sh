#!/usr/bin/env bash
set -euo pipefail
alembic -c database/alembic.ini upgrade head
