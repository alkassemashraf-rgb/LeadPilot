---
title: LeadPilot
emoji: 🚀
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
datasets:
  - ashrafkassem/leadpilot-data
---

# LeadPilot - Multi-tenant SaaS Automation Platform

LeadPilot is a professional-grade automation platform designed for high scalability and hard data isolation.

## Tech Stack

- **Backend:** Python FastAPI, SQLAlchemy 2.0 (Async), Alembic, Postgres
- **Worker:** Celery, Redis
- **Frontend:** Next.js (App Router), Tailwind CSS, shadcn/ui

## Project Structure

- `/backend`: FastAPI application and Celery workers.
- `/frontend`: Next.js application.

## Local Development Setup

### Prerequisites

- Docker & Docker Compose
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### 1. Infrastructure

Spin up the database and redis using Docker:

```bash
docker-compose up -d
```

### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt
# Run migrations (once implemented)
# alembic upgrade head
python3 -m uvicorn main:app --reload --port 8000
```

### 3. Celery Worker (Task Queue)

To start the background worker:

```bash
cd backend
celery -A app.core.celery_app worker -l info
```

### 4. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## Google OAuth Setup

To enable "Sign in with Google":

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or select an existing one).
3. Navigate to **APIs & Services > Credentials**.
4. Click **Create Credentials > OAuth client ID**.
5. Select **Web application** as the application type.
6. Add **Authorized JavaScript origins**: `http://localhost:3000`
7. Add **Authorized redirect URIs**: `http://localhost:3000/auth/google/callback`
8. Copy the **Client ID** and **Client Secret**.
9. Add these to your `backend/.env` file:

    ```env
    GOOGLE_OAUTH_CLIENT_ID=your_client_id
    GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret
    ```

## Implementation Contract

- **Base API Path:** `/api/v1/`
- **Response Envelope:** `{ success, data, error }`
- **Auth:** `Authorization: Bearer <JWT>`
- **Workspace Selection:** `X-Workspace-ID` header required for scoped endpoints.
