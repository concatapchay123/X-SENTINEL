.PHONY: install test lint typecheck run-api run-ui docker-up docker-down docker-reset demo-vector baseline-audit db-migrate db-status db-check db-seed db-backup
install:
	python -m pip install -e '.[dev]'

test:
	pytest -q

lint:
	ruff check backend frontend tests scripts database

typecheck:
	mypy backend/src

run-api:
	uvicorn x_sentinel.main:app --app-dir backend/src --reload --port 8000

run-ui:
	streamlit run frontend/app.py

docker-up:
	docker compose up --build

docker-down:
	docker compose down

docker-reset:
	@echo "WARNING: destroys local SQL Server volume only. Never use for shared/staging/prod."
	docker compose down -v

db-migrate:
	alembic -c database/alembic.ini upgrade head

db-status:
	alembic -c database/alembic.ini current
	alembic -c database/alembic.ini heads

db-check:
	python scripts/check_schema_revision.py
	alembic -c database/alembic.ini check

db-seed:
	python database/seed/seed_dev.py

db-backup:
	bash database/scripts/backup.sh

demo-vector:
	python scripts/generate_demo_vector.py

baseline-audit:
	python scripts/baseline_audit.py
