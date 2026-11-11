"""esquema inicial (sprint 1)

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

ROL = ("jefe", "encargado", "asistente")
TIPO = ("solicitud", "incidencia", "tarea", "visita", "otro")
ESTADO = ("informativo", "abierto", "en_proceso", "en_espera", "resuelto", "cerrado", "cancelado")
PRIORIDAD = ("baja", "media", "alta")


def _e(nombre, valores):
    # create_type=False: los tipos se crean una sola vez, de forma explícita, en upgrade().
    return pg.ENUM(*valores, name=nombre, create_type=False)


def upgrade():
    bind = op.get_bind()
    for nombre, valores in (("rol", ROL), ("tipo_evento", TIPO), ("estado_evento", ESTADO), ("prioridad_evento", PRIORIDAD)):
        pg.ENUM(*valores, name=nombre).create(bind, checkfirst=True)

    op.create_table(
        "usuario",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("correo", sa.String(255), nullable=False, unique=True),
        sa.Column("rol", _e("rol", ROL), nullable=False),
        sa.Column("clave_hash", sa.String(255), nullable=False),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "area",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("nombre", sa.String(120), nullable=False, unique=True),
        sa.Column("activa", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "folio_secuencia",
        sa.Column("anio", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("ultimo", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_table(
        "evento",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("folio", sa.String(20), nullable=False, unique=True),
        sa.Column("tipo", _e("tipo_evento", TIPO), nullable=False),
        sa.Column("subtipo", sa.String(40)),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=False),
        sa.Column("referencia", sa.String(500)),
        sa.Column("fecha_hecho", sa.Date, nullable=False),
        sa.Column("area_id", sa.Uuid, sa.ForeignKey("area.id")),
        sa.Column("solicitante_nombre", sa.String(120)),
        sa.Column("requiere_seguimiento", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("estado", _e("estado_evento", ESTADO), nullable=False),
        sa.Column("prioridad", _e("prioridad_evento", PRIORIDAD)),
        sa.Column("autor_id", sa.Uuid, sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("responsable_id", sa.Uuid, sa.ForeignKey("usuario.id")),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("cerrado_en", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_evento_fecha_tipo", "evento", ["fecha_hecho", "tipo"])
    op.create_index("ix_evento_estado", "evento", ["estado"])
    op.create_index("ix_evento_responsable", "evento", ["responsable_id"])


def downgrade():
    op.drop_table("evento")
    op.drop_table("folio_secuencia")
    op.drop_table("area")
    op.drop_table("usuario")
    bind = op.get_bind()
    for nombre in ("prioridad_evento", "estado_evento", "tipo_evento", "rol"):
        pg.ENUM(name=nombre).drop(bind, checkfirst=True)
