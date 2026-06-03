.PHONY: build up down restart clean test run-dashboard run-dashboard-internal dbt-run dbt-test

# =============================================================================
# Docker Compose Management
# =============================================================================

build:
	docker-compose build

up:
	docker-compose up -d --build

down:
	docker-compose down

restart:
	docker-compose down && docker-compose up -d --build

clean:
	docker-compose down -v
	rm -rf logs/* data/minio/*

# =============================================================================
# local Development & Testing
# =============================================================================

test:
	python -m pytest tests/ -v

run-dashboard:
	streamlit run dashboard/app.py

run-dashboard-internal:
	streamlit run dashboard_interno/app.py

# =============================================================================
# dbt Commands
# =============================================================================

dbt-run:
	dbt run --project-dir dbt

dbt-test:
	dbt test --project-dir dbt
