## Project Setup Guide

This guide provides instructions on how to set up and run the backend server for the project.

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

## 5. uvicorn main:app --reload

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
