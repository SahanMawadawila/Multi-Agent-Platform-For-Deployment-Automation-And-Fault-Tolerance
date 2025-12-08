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
