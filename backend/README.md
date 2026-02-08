## Project Setup Guide

This guide provides instructions on how to set up and run the backend server for the project.

## Pre-requisites

- Python 3.10 or higher
- UV package manager
- PostgreSQL database
- Redis server



## 1. Install uv (if not already installed)

```bash
pip install uv
```

## 2. uv venv

```bash
uv venv
```

## 3. .venv/Scripts/activate

```bash
source .venv/Scripts/activate  # On Windows use: .venv\Scripts\activate
```

## 4. uv sync

## 5. Setup environment variables

duplicate the `.env.example` file and rename it to `.env`. Update the values as necessary, especially for database connection and Redis configuration.

## 6. uvicorn main:app --reload

to add new dependencies, use `uv add <package-name>`

📌 Database Setup & Migration Guide (PostgreSQL + SQLAlchemy + Alembic)

🔧 1. Install PostgreSQL - Download PostgreSQL from the official page:

🗄️ 2. Create a Database name - Flow_Pilot_AI

🔐 3. Set Environment Variables

Create a .env file in the backend folder:

DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/Flow_Pilot_AI
JWT_SECRET=your_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

🔧 4. Initialize Alembic (Run Once)
alembic init alembic -> only initial team mate, not for every one
This creates an alembic folder and alembic.ini. These files should pushed to github.

5. Apply migration
   alembic upgrade head

6. Create new migration (after making changes to models)
   alembic revision --autogenerate -m "your_message_here"

---

## Expose the backend locally with ngrok 🔌

1. Install ngrok
   - (download): Visit https://ngrok.com/download, extract, and add the `ngrok` binary to your PATH.

2. Authenticate your ngrok client with your authtoken

```bash
ngrok config add-authtoken <YOUR_NGROK_AUTHTOKEN>
# or (older CLI variants)
ngrok authtoken <YOUR_NGROK_AUTHTOKEN>
```

3. Start your backend locally (example):

4. Run ngrok to forward HTTP/HTTPS to your local server

```bash
ngrok http 8000
```

After starting ngrok you'll get a public URL like `https://abc123.ngrok-free.app` (HTTPS required for GitHub webhooks and OAuth callbacks).

### Update the project configuration (what to change) ✅

When using ngrok you should update the following so services and webhooks point to the public URL:

- `.env` (or environment variables)
  - **WEBHOOK_BASE_URL**: Set to your ngrok https URL (no trailing slash). Example:
    ```env
    WEBHOOK_BASE_URL=https://abc123.ngrok-free.app
    ``

