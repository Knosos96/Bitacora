"""búsqueda de texto y auditoría de cabecera (sprint 3)

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("evento", sa.Column("busqueda", sa.Text, nullable=False, server_default=""))

    op.create_table(
        "auditoria",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("evento_id", sa.Uuid, sa.ForeignKey("evento.id"), nullable=False),
        sa.Column("campo", sa.String(40), nullable=False),
        sa.Column("valor_anterior", sa.Text),
        sa.Column("valor_nuevo", sa.Text),
        sa.Column("usuario_id", sa.Uuid, sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_auditoria_evento", "auditoria", ["evento_id", "creado_en"])

    # pg_trgm acelera los LIKE '%fragmento%' sobre el texto de búsqueda.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE INDEX ix_evento_busqueda_trgm ON evento USING gin (busqueda gin_trgm_ops)")

    # Rellenar el texto de búsqueda de los eventos que ya existían (Sprints 1 y 2).
    from app.services.busqueda import normalizar

    bind = op.get_bind()
    eventos = bind.execute(sa.text(
        "SELECT id, titulo, descripcion, solicitante_nombre, referencia FROM evento")).fetchall()
    for ev in eventos:
        partes = [ev.titulo, ev.descripcion, ev.solicitante_nombre, ev.referencia]
        partes += [r[0] for r in bind.execute(
            sa.text("SELECT nota FROM seguimiento WHERE evento_id = :i AND estado_nuevo IS NULL"), {"i": ev.id})]
        partes += [r[0] for r in bind.execute(
            sa.text("SELECT descripcion FROM compromiso WHERE evento_id = :i"), {"i": ev.id})]
        texto = normalizar(" \n ".join(p for p in partes if p))
        bind.execute(sa.text("UPDATE evento SET busqueda = :t WHERE id = :i"), {"t": texto, "i": ev.id})


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_evento_busqueda_trgm")
    op.drop_table("auditoria")
    op.drop_column("evento", "busqueda")
