import os
from logging.config import fileConfig
from sqlalchemy import pool, create_engine
from alembic import context

from app.core.database import Base
from app.models import order as order_model

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = "postgresql+psycopg2://postgres:postgres@localhost:5435/orders_db"

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(database_url, poolclass=pool.NullPool)
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
