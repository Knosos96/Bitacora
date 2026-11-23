"""superusuario e historial permanente de cuentas y actividad

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("COMMIT")
        op.execute("ALTER TYPE rol ADD VALUE IF NOT EXISTS 'superusuario'")

    op.create_table(
        "cuenta_historica",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("correo", sa.String(255), nullable=False),
        sa.Column("rol", sa.String(40), nullable=False),
        sa.Column("rol_custom_nombre", sa.String(80), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="activa"),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("eliminado_por_id", sa.Uuid(), nullable=True),
        sa.Column("eliminado_por_nombre", sa.String(120), nullable=True),
        sa.Column("eliminado_por_correo", sa.String(255), nullable=True),
    )
    op.create_index("ix_cuenta_hist_correo", "cuenta_historica", ["correo"])
    op.create_index("ix_cuenta_hist_estado", "cuenta_historica", ["estado", "creado_en"])

    op.create_table(
        "evento_origen",
        sa.Column("evento_id", sa.Uuid(), sa.ForeignKey("evento.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("autor_id", sa.Uuid(), nullable=False),
        sa.Column("autor_nombre", sa.String(120), nullable=False),
        sa.Column("autor_correo", sa.String(255), nullable=False),
        sa.Column("responsable_id", sa.Uuid(), nullable=True),
        sa.Column("responsable_nombre", sa.String(120), nullable=True),
        sa.Column("responsable_correo", sa.String(255), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evento_origen_autor", "evento_origen", ["autor_id"])
    op.create_index("ix_evento_origen_resp", "evento_origen", ["responsable_id"])

    op.create_table(
        "actividad_bitacora",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("actor_nombre", sa.String(120), nullable=False),
        sa.Column("actor_correo", sa.String(255), nullable=False),
        sa.Column("actor_rol", sa.String(40), nullable=False),
        sa.Column("accion", sa.String(60), nullable=False),
        sa.Column("entidad", sa.String(40), nullable=False),
        sa.Column("entidad_id", sa.String(64), nullable=True),
        sa.Column("folio", sa.String(30), nullable=True),
        sa.Column("titulo", sa.String(250), nullable=True),
        sa.Column("detalle", sa.Text(), nullable=False, server_default=""),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_actividad_actor_fecha", "actividad_bitacora", ["actor_id", "creado_en"])
    op.create_index("ix_actividad_entidad_fecha", "actividad_bitacora", ["entidad", "creado_en"])
    op.create_index("ix_actividad_accion", "actividad_bitacora", ["accion"])
    op.create_index("ix_actividad_folio", "actividad_bitacora", ["folio"])
    op.create_index("ix_actividad_creado", "actividad_bitacora", ["creado_en"])


def downgrade():
    op.drop_table("actividad_bitacora")
    op.drop_table("evento_origen")
    op.drop_table("cuenta_historica")
