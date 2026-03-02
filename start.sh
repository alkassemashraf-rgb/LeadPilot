#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────────
# HuggingFace Persistent Storage Detection
# ─────────────────────────────────────────────────────────────
# HF Spaces mounts a persistent volume at /data when enabled.
# Without it, the database resets on every container restart.
# Enable it at: Space Settings → Persistent Storage → Enable
# ─────────────────────────────────────────────────────────────

if [ -d "/data" ]; then
    echo "[DB] HuggingFace Persistent Storage detected at /data"

    # Ensure /data is writable
    if [ ! -w "/data" ]; then
        echo "[DB] WARNING: /data is not writable. Falling back to ephemeral storage."
        export DATABASE_URL="sqlite+aiosqlite:////app/backend/leadpilot.db"
    else
        # First-time init: move or create DB file in /data
        if [ ! -f "/data/leadpilot.db" ]; then
            echo "[DB] Initializing persistent database at /data/leadpilot.db"
            if [ -f "/app/backend/leadpilot.db" ] && [ -s "/app/backend/leadpilot.db" ]; then
                echo "[DB] Copying existing DB from /app/backend/leadpilot.db"
                cp /app/backend/leadpilot.db /data/leadpilot.db
            else
                echo "[DB] Creating empty DB file"
                touch /data/leadpilot.db
            fi
        fi
        export DATABASE_URL="sqlite+aiosqlite:////data/leadpilot.db"
        echo "[DB] Using persistent database: $DATABASE_URL"
    fi
else
    echo "[DB] WARNING: No /data directory found."
    echo "[DB] WARNING: Database is EPHEMERAL and will reset on every container restart."
    echo "[DB] To persist data: enable Persistent Storage in the HuggingFace Space settings."
    export DATABASE_URL="sqlite+aiosqlite:////app/backend/leadpilot.db"
fi

# Extract the DB file path from DATABASE_URL for backup
DB_FILE="/${DATABASE_URL#sqlite+aiosqlite:////}"

cd /app/backend

# ─────────────────────────────────────────────────────────────
# Step 1: Backup database before running migrations
# Protects against data loss if a migration fails or times out
# ─────────────────────────────────────────────────────────────
if [ -f "$DB_FILE" ] && [ -s "$DB_FILE" ]; then
    echo "[DB] Creating pre-migration backup at ${DB_FILE}.bak"
    cp "$DB_FILE" "${DB_FILE}.bak"
fi

# ─────────────────────────────────────────────────────────────
# Step 2: Apply database migrations
# ─────────────────────────────────────────────────────────────
echo "[DB] Running database migrations..."
if timeout 60s python3 -m alembic upgrade head; then
    echo "[DB] Migrations completed successfully."
    rm -f "${DB_FILE}.bak"
else
    echo "[DB] WARNING: Migration failed or timed out."
    if [ -f "${DB_FILE}.bak" ]; then
        echo "[DB] Restoring database from pre-migration backup."
        cp "${DB_FILE}.bak" "$DB_FILE"
    fi
fi

# ─────────────────────────────────────────────────────────────
# Step 3: Seed initial data (idempotent — safe to run every time)
# ─────────────────────────────────────────────────────────────
echo "[DB] Seeding initial data..."
python3 scripts/create_test_user.py

# ─────────────────────────────────────────────────────────────
# Step 4: Start Redis (broker for Celery)
# ─────────────────────────────────────────────────────────────
echo "[SVC] Starting Redis server..."
redis-server --daemonize yes || echo "Redis already running or failed to start"

# ─────────────────────────────────────────────────────────────
# Step 5: Start Celery Worker & Beat
# ─────────────────────────────────────────────────────────────
echo "[SVC] Starting Celery Worker..."
nohup celery -A app.core.celery_app worker --loglevel=info -Q main-queue,celery > /tmp/celery_worker.log 2>&1 &

echo "[SVC] Starting Celery Beat (scheduler)..."
nohup celery -A app.core.celery_app beat --loglevel=info > /tmp/celery_beat.log 2>&1 &

# ─────────────────────────────────────────────────────────────
# Step 6: Start FastAPI backend
# ─────────────────────────────────────────────────────────────
echo "[SVC] Starting FastAPI backend on :8000..."
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 &

# ─────────────────────────────────────────────────────────────
# Step 7: Start Next.js frontend (App)
# ─────────────────────────────────────────────────────────────
echo "[SVC] Starting Next.js frontend on :3000..."
cd /app/frontend/.next/standalone
HOSTNAME=0.0.0.0 PORT=3000 node server.js &

# ─────────────────────────────────────────────────────────────
# Step 7.5: Start Next.js website (Marketing)
# ─────────────────────────────────────────────────────────────
echo "[SVC] Starting Next.js website on :3002..."
cd /app/Website/.next/standalone
HOSTNAME=0.0.0.0 PORT=3002 node server.js &

# ─────────────────────────────────────────────────────────────
# Step 8: Start Nginx (single public entry point on port 7860)
# ─────────────────────────────────────────────────────────────
echo "[SVC] Starting Nginx reverse proxy on :7860..."
nginx -g "daemon off;"
