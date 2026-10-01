.PHONY: help install backend frontend dev clean test lint

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Installation ────────────────────────────────────────

install: install-backend install-frontend ## Install all dependencies

install-backend: ## Install backend dependencies
	cd backend && python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt

install-frontend: ## Install frontend dependencies
	cd frontend && npm install

# ─── Development ─────────────────────────────────────────

backend: ## Start backend dev server
	cd backend && . venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## Start frontend dev server
	cd frontend && npm run dev

dev: ## Start both servers (run in separate terminals)
	@echo "Run 'make backend' and 'make frontend' in separate terminals"

# ─── Database (MongoDB & Compass) ────────────────────────

seed-db: ## Seed MongoDB database with synthetic dataset for MongoDB Compass
	PYTHONPATH=backend backend/venv/bin/python data/seed_mongodb.py

# ─── Data ────────────────────────────────────────────────

generate-data: ## Generate synthetic dataset
	cd data/synthetic && python3 generate_data.py

# ─── Testing ─────────────────────────────────────────────

test: ## Run all tests
	PYTHONPATH=backend backend/venv/bin/pytest tests/backend -v

test-backend: ## Run backend tests
	PYTHONPATH=backend backend/venv/bin/pytest tests/backend -v --tb=short

# ─── Utilities ───────────────────────────────────────────

clean: ## Clean generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	rm -rf backend/.pytest_cache
	rm -rf frontend/dist

lint: ## Lint backend code
	cd backend && . venv/bin/activate && python -m py_compile app/main.py && echo "Syntax OK"
