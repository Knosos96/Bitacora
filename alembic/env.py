from alembic import context

from app import models  # noqa: F401  (registra las tablas)
from app.db import Base, engine

target_metadata = Base.metadata


def run_migrations_online():
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
