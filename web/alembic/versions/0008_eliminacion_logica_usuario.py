"""eliminacion logica de usuarios y snapshot de area en evento_origen

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("usuario", sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_usuario_eliminado", "usuario", ["eliminado_en"])
    op.add_column("evento_origen", sa.Column("area_nombre", sa.String(120), nullable=True))


def downgrade():
    op.drop_column("evento_origen", "area_nombre")
    op.drop_index("ix_usuario_eliminado", table_name="usuario")
    op.drop_column("usuario", "eliminado_en")
