"""add container registries

Revision ID: e7f42d9ac310
Revises: b2ea64f02095
Create Date: 2026-07-02
"""
from alembic import op
import sqlalchemy as sa


revision = "e7f42d9ac310"
down_revision = "b2ea64f02095"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "container_registries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("server", sa.String(length=300), nullable=False),
        sa.Column("namespace", sa.String(length=200), nullable=True),
        sa.Column("username", sa.String(length=300), nullable=True),
        sa.Column("encrypted_password", sa.Text(), nullable=True),
        sa.Column("email", sa.String(length=300), nullable=True),
        sa.Column("pull_secret_name", sa.String(length=253), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    with op.batch_alter_table("container_registries") as batch_op:
        batch_op.create_index(
            batch_op.f("ix_container_registries_is_active"),
            ["is_active"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_container_registries_is_default"),
            ["is_default"], unique=False
        )


def downgrade():
    with op.batch_alter_table("container_registries") as batch_op:
        batch_op.drop_index(batch_op.f("ix_container_registries_is_default"))
        batch_op.drop_index(batch_op.f("ix_container_registries_is_active"))
    op.drop_table("container_registries")
