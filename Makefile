.PHONY: help install migrate seed run test lint clean

help:
	@echo "Platform-X - common tasks"
	@echo ""
	@echo "  make install    - install dependencies (venv assumed active)"
	@echo "  make migrate    - apply alembic migrations"
	@echo "  make seed       - load demo data (tenants, services, admin)"
	@echo "  make run        - start dev server on :8000"
	@echo "  make test       - run pytest"
	@echo "  make clean      - remove caches and temp files"

install:
	pip install -r requirements.txt

migrate:
	alembic upgrade head

seed:
	python -m app.scripts.seed_all

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
