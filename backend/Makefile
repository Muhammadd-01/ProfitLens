.PHONY: backend dev run start install test seed-db

backend dev run start:
	. venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

install:
	. venv/bin/activate && pip install -r requirements.txt

test:
	PYTHONPATH=. venv/bin/pytest ../tests/backend -v

seed-db:
	PYTHONPATH=. venv/bin/python ../data/seed_mongodb.py
