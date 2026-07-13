"""add kubernetes cluster onboarding fields

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-13
"""
from alembic import op
import sqlalchemy as sa


revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("kubernetes_clusters") as batch_op:
        batch_op.add_column(sa.Column("environment_label", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("encrypted_kubeconfig", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column(
            "connection_status",
            sa.String(length=20),
            nullable=False,
            server_default="untested",
        ))
        batch_op.add_column(sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("kubernetes_version", sa.String(length=80), nullable=True))


def downgrade():
    with op.batch_alter_table("kubernetes_clusters") as batch_op:
        batch_op.drop_column("kubernetes_version")
        batch_op.drop_column("last_checked_at")
        batch_op.drop_column("connection_status")
        batch_op.drop_column("encrypted_kubeconfig")
        batch_op.drop_column("environment_label")
