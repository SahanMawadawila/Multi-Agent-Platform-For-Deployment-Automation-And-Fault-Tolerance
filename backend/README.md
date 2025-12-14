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
