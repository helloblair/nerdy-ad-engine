# Nerdy Ad Engine — Development Commands
#
# make install        Install backend (pip) and frontend (npm) dependencies
# make dev            Start backend (port 8080) and frontend (port 3000) in parallel
# make test           Run all backend tests (mocked, no API keys needed)
# make run-pipeline   Run a single ad generation pipeline (requires API keys)
# make clean          Remove SQLite database and Python/build caches

.PHONY: install dev test run-pipeline clean

install:
	cd backend && (pip3 install -r requirements.txt 2>/dev/null || pip3 install --break-system-packages -r requirements.txt)
	cd frontend && npm install

dev:
	@echo "Starting backend on :8080 and frontend on :3000..."
	@cd backend && DB_BACKEND=sqlite uvicorn main:app --reload --port 8080 &
	@cd frontend && npm run dev

test:
	cd backend && DB_BACKEND=sqlite python3 -m pytest tests/ -v

run-pipeline:
	cd backend && DB_BACKEND=sqlite python3 pipeline.py

clean:
	rm -rf backend/data/ads.db
	rm -rf backend/__pycache__ backend/**/__pycache__
	rm -rf backend/.pytest_cache backend/tests/.pytest_cache
	rm -rf frontend/.next
