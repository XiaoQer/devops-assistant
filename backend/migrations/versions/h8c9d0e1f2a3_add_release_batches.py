"""add release batches and environment targets

Revision ID: h8c9d0e1f2a3
Revises: g7b8c9d0e1f2
"""
from alembic import op
import sqlalchemy as sa

revision = "h8c9d0e1f2a3"
down_revision = "g7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("application_build_versions", sa.Column("commit_message", sa.String(500)))
    op.add_column("application_build_versions", sa.Column("commit_author", sa.String(255)))
    op.create_table(
        "application_release_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("build_version_id", sa.Integer(), nullable=True),
        sa.Column("branch", sa.String(120), nullable=False),
        sa.Column("git_commit", sa.String(64), nullable=False),
        sa.Column("commit_message", sa.String(500)),
        sa.Column("commit_author", sa.String(255)),
        sa.Column("status", sa.String(30), nullable=False, server_default="Building"),
        sa.Column("created_by", sa.String(120), nullable=False, server_default="local-user"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["build_version_id"], ["application_build_versions.id"]),
    )
    op.create_index("ix_release_batches_application_id", "application_release_batches", ["application_id"])
    op.create_index("ix_release_batches_project_id", "application_release_batches", ["project_id"])
    op.create_index("ix_release_batches_build_version_id", "application_release_batches", ["build_version_id"])
    op.create_index("ix_release_batches_status", "application_release_batches", ["status"])
    op.create_table(
        "application_release_targets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("environment_id", sa.Integer(), nullable=False),
        sa.Column("build_version_id", sa.Integer(), nullable=True),
        sa.Column("pipeline_run_name", sa.String(253)),
        sa.Column("status", sa.String(30), nullable=False, server_default="Pending"),
        sa.Column("approval_id", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["application_release_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["environment_id"], ["application_environments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["build_version_id"], ["application_build_versions.id"]),
        sa.ForeignKeyConstraint(["approval_id"], ["approval_records.id"]),
        sa.UniqueConstraint("batch_id", "environment_id", name="uq_release_target_environment"),
    )
    for name, column in (("batch_id", "batch_id"), ("environment_id", "environment_id"), ("build_version_id", "build_version_id"), ("status", "status"), ("approval_id", "approval_id")):
        op.create_index(f"ix_release_targets_{name}", "application_release_targets", [column])


def downgrade():
    for name in ("ix_release_targets_approval_id", "ix_release_targets_status", "ix_release_targets_build_version_id", "ix_release_targets_environment_id", "ix_release_targets_batch_id"):
        op.drop_index(name, table_name="application_release_targets")
    op.drop_table("application_release_targets")
    for name in ("ix_release_batches_status", "ix_release_batches_build_version_id", "ix_release_batches_project_id", "ix_release_batches_application_id"):
        op.drop_index(name, table_name="application_release_batches")
    op.drop_table("application_release_batches")
    op.drop_column("application_build_versions", "commit_author")
    op.drop_column("application_build_versions", "commit_message")
