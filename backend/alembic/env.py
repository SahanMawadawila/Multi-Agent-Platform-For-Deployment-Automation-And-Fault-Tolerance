from logging.config import fileConfig
import os
from pathlib import Path
from dotenv import load_dotenv

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# load backend/.env (if present)
HERE = Path(__file__).resolve().parent.parent
dotenv_file = HERE / ".env"
if dotenv_file.exists():
    load_dotenv(dotenv_file)

# prefer ALEMBIC_DATABASE_URL, then DATABASE_URL; fall back to alembic.ini value
db_url = (
    os.getenv("ALEMBIC_DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or config.get_main_option("sqlalchemy.url")
)

# if your app uses asyncpg in .env, Alembic needs a sync driver; convert if appropriate
if db_url and db_url.startswith("postgresql+asyncpg"):
    db_url = db_url.replace("+asyncpg", "+psycopg2")

if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Import the shared Base and all models
from app.models import Base

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()