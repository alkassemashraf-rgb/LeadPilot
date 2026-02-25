.PHONY: dev services backend frontend test smoke lint db-reset

# Test-only Fernet key — 32-byte URL-safe base64. NOT a real secret.
TEST_FERNET_KEY := ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=

# ── Infrastructure ────────────────────────────────────────────────────────────

services:
	docker-compose up -d

# ── Development ───────────────────────────────────────────────────────────────

backend:
	cd backend && uvicorn main:app --reload --port 8000

frontend:
	cd frontend && npm install && npm run dev

dev:
	@echo "Run each of these in a separate terminal:"
	@echo "  make services   → PostgreSQL + Redis on :5432 / :6379"
	@echo "  make backend    → FastAPI on :8000"
	@echo "  make frontend   → Next.js on :3000"

# ── Testing ───────────────────────────────────────────────────────────────────

# Runs the full pytest suite.
# Must be invoked from backend/ so conftest.py can import from main.py.
test:
	cd backend && \
	  DATABASE_URL="sqlite+aiosqlite:///./test.db" \
	  REDIS_URL="redis://localhost:6379/0" \
	  JWT_SECRET="test_jwt_secret_ci_only" \
	  ADMIN_JWT_SECRET="test_admin_jwt_secret_ci_only" \
	  ENCRYPTION_KEY_FERNET="$(TEST_FERNET_KEY)" \
	  python -m pytest tests/ -v

# E2E smoke against a running server (default: http://localhost:8000)
smoke:
	python scripts/e2e_smoke_v2.py --base-url http://localhost:8000

# ── Linting ───────────────────────────────────────────────────────────────────

lint:
	cd backend && ruff check .

# ── Database Utilities ────────────────────────────────────────────────────────

# Remove local test database file
db-reset:
	rm -f backend/test.db
	@echo "Test database cleared."
