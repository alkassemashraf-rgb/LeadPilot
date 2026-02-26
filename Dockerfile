# --- Stage 1: Build Frontend ---
FROM node:20-bookworm-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --prefer-offline
COPY frontend/ ./
RUN NODE_OPTIONS="--max-old-space-size=4096" npm run build

# --- Stage 2: Build Backend & Final Image ---
FROM python:3.11-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nginx \
    curl \
    gnupg \
    redis-server \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set up user for Hugging Face (uid 1000)
RUN useradd -m -u 1000 user
WORKDIR /app

# Copy Backend
COPY --chown=user:user backend/ /app/backend/
RUN cp /app/backend/.env.example /app/backend/.env && chown user:user /app/backend/.env
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
# Ensure SQLite DB is writeable by the user
RUN touch /app/backend/leadpilot.db && chown user:user /app/backend/leadpilot.db

# Copy Frontend build from Stage 1
COPY --chown=user:user --from=frontend-builder /app/frontend/.next/standalone /app/frontend/.next/standalone
COPY --chown=user:user --from=frontend-builder /app/frontend/.next/static /app/frontend/.next/standalone/.next/static
COPY --chown=user:user --from=frontend-builder /app/frontend/public /app/frontend/.next/standalone/public

# Copy start script and nginx config
COPY nginx.conf /etc/nginx/nginx.conf
COPY --chown=user:user start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Environment variables
ENV PORT=7860
ENV DATABASE_URL=sqlite+aiosqlite:////app/backend/leadpilot.db
ENV NEXT_PUBLIC_API_BASE_URL=""
ENV APP_BASE_URL=https://ashrafkassem-leadpilot.hf.space

EXPOSE 7860

CMD ["/app/start.sh"]
