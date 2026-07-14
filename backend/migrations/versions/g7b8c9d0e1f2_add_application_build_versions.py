"""add application build versions

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-14
"""

from alembic import op
import sqlalchemy as sa


revision = "g7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "application_build_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(length=120), nullable=False),
        sa.Column("git_repo", sa.String(length=500), nullable=False),
        sa.Column("git_branch", sa.String(length=120), nullable=False),
        sa.Column("git_commit", sa.String(length=64)),
        sa.Column("image_name", sa.String(length=300), nullable=False),
        sa.Column("image_tag", sa.String(length=120), nullable=False),
        sa.Column("image_digest", sa.String(length=255)),
        sa.Column("pipeline_run_name", sa.String(length=253)),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="Pending"),
        sa.Column("created_by", sa.String(length=120), nullable=False, server_default="local-user"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text()),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_application_build_versions_application_id", "application_build_versions", ["application_id"])
    op.create_index("ix_application_build_versions_project_id", "application_build_versions", ["project_id"])
    op.create_index("ix_application_build_versions_status", "application_build_versions", ["status"])
    op.create_index("ix_application_build_versions_pipeline_run_name", "application_build_versions", ["pipeline_run_name"])
    for table in ("pipeline_executions", "release_records", "approval_records"):
        op.add_column(table, sa.Column("build_version_id", sa.Integer(), nullable=True))
        op.create_index(f"ix_{table}_build_version_id", table, ["build_version_id"])
        op.create_foreign_key(
            f"fk_{table}_build_version_id_application_build_versions",
            table,
            "application_build_versions",
            ["build_version_id"],
            ["id"],
        )


def downgrade():
    for table in ("approval_records", "release_records", "pipeline_executions"):
        op.drop_constraint(f"fk_{table}_build_version_id_application_build_versions", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_build_version_id", table_name=table)
        op.drop_column(table, "build_version_id")
    for index in (
        "ix_application_build_versions_pipeline_run_name",
        "ix_application_build_versions_status",
        "ix_application_build_versions_project_id",
        "ix_application_build_versions_application_id",
    ):
        op.drop_index(index, table_name="application_build_versions")
    op.drop_table("application_build_versions")
