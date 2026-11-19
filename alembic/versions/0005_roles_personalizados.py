"""roles personalizados con permisos granulares

Revision ID: 0005
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    # Tabla de roles personalizados
    op.create_table(
        "rol_personalizado",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(80), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False, server_default=""),
        sa.Column("permisos", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("creado_por_id", sa.Uuid(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["creado_por_id"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
    )

    # Columna en usuario: rol personalizado opcional
    op.add_column(
        "usuario",
        sa.Column("rol_custom_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_usuario_rol_custom",
        "usuario", "rol_personalizado",
        ["rol_custom_id"], ["id"],
    )


def downgrade():
    op.drop_constraint("fk_usuario_rol_custom", "usuario", type_="foreignkey")
    op.drop_column("usuario", "rol_custom_id")
    op.drop_table("rol_personalizado")

