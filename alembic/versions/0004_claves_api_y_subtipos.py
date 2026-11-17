"""claves de API, registro de uso y catálogo de subtipos (sprints 5 y 6)

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

TIPO = ("solicitud", "incidencia", "tarea", "visita", "otro")


def upgrade():
    op.create_table(
        "clave_api",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("prefijo", sa.String(12), nullable=False),
        sa.Column("hash", sa.String(64), nullable=False, unique=True),
        sa.Column("creada_por_id", sa.Uuid, sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revocada_en", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "uso_clave_api",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("clave_id", sa.Uuid, sa.ForeignKey("clave_api.id"), nullable=False),
        sa.Column("metodo", sa.String(8), nullable=False),
        sa.Column("ruta", sa.String(200), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_uso_clave", "uso_clave_api", ["clave_id", "creado_en"])
    op.create_table(
        "subtipo",
        sa.Column("tipo", pg.ENUM(*TIPO, name="tipo_evento", create_type=False), primary_key=True),
        sa.Column("nombre", sa.String(40), primary_key=True),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.true()),
    )


def downgrade():
    op.drop_table("subtipo")
    op.drop_table("uso_clave_api")
    op.drop_table("clave_api")
