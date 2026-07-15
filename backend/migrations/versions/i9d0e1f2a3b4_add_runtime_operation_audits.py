"""add runtime operation audits

Revision ID: i9d0e1f2a3b4
Revises: h8c9d0e1f2a3
"""
from alembic import op
import sqlalchemy as sa


revision = "i9d0e1f2a3b4"
down_revision = "h8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "runtime_operation_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("environment", sa.String(30), nullable=False),
        sa.Column("cluster_id", sa.Integer(), nullable=False),
        sa.Column("namespace", sa.String(253), nullable=False),
        sa.Column("resource_kind", sa.String(30), nullable=False),
        sa.Column("resource_name", sa.String(253), nullable=False),
        sa.Column("container", sa.String(253)),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("reason", sa.String(500)),
        sa.Column("status", sa.String(30), nullable=False, server_default="Running"),
        sa.Column("error_message", sa.String(500)),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["application_id"], ["applications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["cluster_id"], ["kubernetes_clusters.id"], ondelete="RESTRICT"
        ),
    )
    op.create_index("ix_runtime_audits_user_id", "runtime_operation_audits", ["user_id"])
    op.create_index("ix_runtime_audits_project_id", "runtime_operation_audits", ["project_id"])
    op.create_index(
        "ix_runtime_audits_application_id", "runtime_operation_audits", ["application_id"]
    )
    op.create_index("ix_runtime_audits_status", "runtime_operation_audits", ["status"])
    op.create_index(
        "ix_runtime_audits_started_at", "runtime_operation_audits", ["started_at"]
    )


def downgrade():
    for name in (
        "ix_runtime_audits_started_at",
        "ix_runtime_audits_status",
        "ix_runtime_audits_application_id",
        "ix_runtime_audits_project_id",
        "ix_runtime_audits_user_id",
    ):
        op.drop_index(name, table_name="runtime_operation_audits")
    op.drop_table("runtime_operation_audits")
