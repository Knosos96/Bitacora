"""seguimiento (notas) y compromiso (sprint 2)

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

ESTADO = ("informativo", "abierto", "en_proceso", "en_espera", "resuelto", "cerrado", "cancelado")
ESTADO_COMPROMISO = ("pendiente", "cumplido", "cancelado")


def upgrade():
    pg.ENUM(*ESTADO_COMPROMISO, name="estado_compromiso").create(op.get_bind(), checkfirst=True)
    estado_evento = pg.ENUM(*ESTADO, name="estado_evento", create_type=False)  # ya existe (0001)
    estado_compromiso = pg.ENUM(*ESTADO_COMPROMISO, name="estado_compromiso", create_type=False)

    op.create_table(
        "seguimiento",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("evento_id", sa.Uuid, sa.ForeignKey("evento.id"), nullable=False),
        sa.Column("autor_id", sa.Uuid, sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("nota", sa.Text, nullable=False),
        sa.Column("estado_anterior", estado_evento),
        sa.Column("estado_nuevo", estado_evento),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_seguimiento_evento", "seguimiento", ["evento_id", "creado_en"])

    op.create_table(
        "compromiso",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("evento_id", sa.Uuid, sa.ForeignKey("evento.id"), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=False),
        sa.Column("responsable_id", sa.Uuid, sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("fecha_limite", sa.Date, nullable=False),
        sa.Column("estado", estado_compromiso, nullable=False, server_default="pendiente"),
        sa.Column("cumplido_en", sa.DateTime(timezone=True)),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_compromiso_evento", "compromiso", ["evento_id"])
    op.create_index("ix_compromiso_estado_fecha", "compromiso", ["estado", "fecha_limite"])

    # Las notas son inmutables también a nivel de base de datos.
    op.execute(
        """
        CREATE FUNCTION seguimiento_inmutable() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Las notas de seguimiento no se editan ni se eliminan';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER seguimiento_inmutable BEFORE UPDATE OR DELETE ON seguimiento "
        "FOR EACH ROW EXECUTE FUNCTION seguimiento_inmutable()"
    )


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS seguimiento_inmutable ON seguimiento")
    op.execute("DROP FUNCTION IF EXISTS seguimiento_inmutable()")
    op.drop_table("compromiso")
    op.drop_table("seguimiento")
    pg.ENUM(name="estado_compromiso").drop(op.get_bind(), checkfirst=True)
