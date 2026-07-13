"""add registry connectivity fields

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-13
"""
from alembic import op
import sqlalchemy as sa


revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("container_registries") as batch_op:
        batch_op.add_column(sa.Column(
            "skip_tls_verify",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ))
        batch_op.add_column(sa.Column(
            "connection_status",
            sa.String(length=20),
            nullable=False,
            server_default="untested",
        ))
        batch_op.add_column(sa.Column(
            "last_checked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ))
        batch_op.add_column(sa.Column(
            "last_connection_message",
            sa.String(length=300),
            nullable=True,
        ))


def downgrade():
    with op.batch_alter_table("container_registries") as batch_op:
        batch_op.drop_column("last_connection_message")
        batch_op.drop_column("last_checked_at")
        batch_op.drop_column("connection_status")
        batch_op.drop_column("skip_tls_verify")
