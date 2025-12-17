from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# --- ścieżki / importy aplikacji ---

# dodaj root projektu do sys.path (env.py jest w katalogu "alembic/")
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from app import models  # noqa: F401  - ważne: ładuje modele, żeby Base.metadata je znał
from app.config import settings  # type: ignore  # z Twojego app/config.py
from app.database import Base  # type: ignore  # z app/database.py

# --- standardowy kawałek Alembica ---

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ustawiamy URL bazy z Settings, zamiast trzymać go w alembic.ini
if settings.DATABASE_URL:
    config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# To jest ważne dla autogenerate
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
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
