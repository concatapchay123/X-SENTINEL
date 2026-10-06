#!/usr/bin/env bash
set -euo pipefail
python scripts/baseline_audit.py
pytest -q
ruff check backend frontend tests scripts
mypy backend/src
