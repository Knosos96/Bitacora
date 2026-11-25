"""fix columna busqueda: tsvector -> text

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-19
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("DROP INDEX IF EXISTS ix_evento_busqueda")
    op.execute("DROP INDEX IF EXISTS ix_evento_busqueda_trgm")
    op.execute("ALTER TABLE evento ALTER COLUMN busqueda TYPE TEXT USING busqueda::text")
    op.execute("ALTER TABLE evento ALTER COLUMN busqueda SET DEFAULT ''")
    op.execute("CREATE INDEX IF NOT EXISTS ix_evento_busqueda_trgm ON evento USING gin (busqueda gin_trgm_ops)")


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("DROP INDEX IF EXISTS ix_evento_busqueda_trgm")
    op.execute("ALTER TABLE evento ALTER COLUMN busqueda TYPE tsvector USING busqueda::tsvector")
