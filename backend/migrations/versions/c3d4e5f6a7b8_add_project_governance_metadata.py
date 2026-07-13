"""add project governance metadata

Revision ID: c3d4e5f6a7b8
Revises: a7c8d9e0f1a2
Create Date: 2026-07-13
"""
from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6a7b8"
down_revision = "a7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(
            sa.Column("status", sa.String(length=30), nullable=False, server_default="active")
        )
        batch_op.add_column(sa.Column("business_owner", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("billing_owner", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("github_group", sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column(
                "github_default_visibility",
                sa.String(length=30),
                nullable=False,
                server_default="private",
            )
        )
        batch_op.add_column(sa.Column("aliyun_account_id", sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column("aliyun_resource_group_id", sa.String(length=120), nullable=True)
        )
        batch_op.add_column(sa.Column("aliyun_region", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("aliyun_vpc_id", sa.String(length=120), nullable=True))
        batch_op.add_column(
            sa.Column(
                "aliyun_binding_status",
                sa.String(length=30),
                nullable=False,
                server_default="unbound",
            )
        )
        batch_op.create_index(batch_op.f("ix_projects_status"), ["status"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_projects_aliyun_binding_status"),
            ["aliyun_binding_status"],
            unique=False,
        )

    with op.batch_alter_table("projects") as batch_op:
        batch_op.alter_column("status", server_default=None)
        batch_op.alter_column("github_default_visibility", server_default=None)
        batch_op.alter_column("aliyun_binding_status", server_default=None)


def downgrade():
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_index(batch_op.f("ix_projects_aliyun_binding_status"))
        batch_op.drop_index(batch_op.f("ix_projects_status"))
        batch_op.drop_column("aliyun_binding_status")
        batch_op.drop_column("aliyun_vpc_id")
        batch_op.drop_column("aliyun_region")
        batch_op.drop_column("aliyun_resource_group_id")
        batch_op.drop_column("aliyun_account_id")
        batch_op.drop_column("github_default_visibility")
        batch_op.drop_column("github_group")
        batch_op.drop_column("billing_owner")
        batch_op.drop_column("business_owner")
        batch_op.drop_column("status")
