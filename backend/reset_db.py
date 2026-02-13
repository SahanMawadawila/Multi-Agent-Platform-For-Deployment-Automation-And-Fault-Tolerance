import os
import sys
import asyncio
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Determine the project root (one level up from this script if run directly)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Add backend directory to sys.path so we can import 'app'
sys.path.append(CURRENT_DIR)

# Explicitly load .env from backend folder BEFORE importing settings
dotenv_path = os.path.join(CURRENT_DIR, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f"Loaded .env from {dotenv_path}")
else:
    print(f"Warning: .env not found at {dotenv_path}")

# NOW import settings, after env vars are loaded
from app.config import settings

async def reset_database():
    """
    Resets the database by dropping the 'public' schema and recreating it.
    Then runs alembic upgrade head.
    """
    db_url = settings.DATABASE_URL
    if not db_url:
        print("Error: DATABASE_URL not found in settings.")
        return

    print(f"Connecting to database...")
    # Create a null-pool engine just for this operation
    engine = create_async_engine(db_url, isolation_level="AUTOCOMMIT")

    try:
        async with engine.connect() as conn:
            print("Dropping schema 'public'...")
            await conn.execute(text("DROP SCHEMA public CASCADE;"))
            print("Recreating schema 'public'...")
            await conn.execute(text("CREATE SCHEMA public;"))
            print("Database schema reset successfully.")
    except Exception as e:
        print(f"Error resetting database: {e}")
        return
    finally:
        await engine.dispose()

    print("\nRunning Alembic migrations...")
    # Run alembic upgrade head using absolute path to config file
    alembic_ini_path = os.path.join(CURRENT_DIR, "alembic.ini")
    if not os.path.exists(alembic_ini_path):
        print(f"Error: alembic.ini not found at {alembic_ini_path}")
        return

    import subprocess
    
    # Run alembic using the same python interpreter (if possible) or just 'alembic'
    # Use subprocess to inject PYTHONPATH so alembic can find 'app'
    env = os.environ.copy()
    env["PYTHONPATH"] = CURRENT_DIR + os.pathsep + env.get("PYTHONPATH", "")

    # We use 'sys.executable -m alembic' to ensure we use the venv's alembic
    cmd = [sys.executable, "-m", "alembic", "-c", alembic_ini_path, "upgrade", "head"]
    
    print(f"Executing: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, env=env, check=True)
        print("\nDatabase reset and migration complete! 🚀")
    except subprocess.CalledProcessError as e:
        print(f"\nError running migrations: {e}")

if __name__ == "__main__":
    # Windows/Python 3.8+ asyncio policy fix if needed, though usually fine for scripts
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(reset_database())
