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
    inspector = sa.inspect(op.get_bind())
    if "application_build_versions" not in inspector.get_table_names():
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
            sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE", name="fk_build_app"),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE", name="fk_build_project"),
        )
    inspector = sa.inspect(op.get_bind())
    existing_indexes = {item["name"] for item in inspector.get_indexes("application_build_versions")}
    for name, column in (
        ("ix_application_build_versions_application_id", "application_id"),
        ("ix_application_build_versions_project_id", "project_id"),
        ("ix_application_build_versions_status", "status"),
        ("ix_application_build_versions_pipeline_run_name", "pipeline_run_name"),
    ):
        if name not in existing_indexes:
            op.create_index(name, "application_build_versions", [column])
    for table in ("pipeline_executions", "release_records", "approval_records"):
        columns = {item["name"] for item in inspector.get_columns(table)}
        if "build_version_id" not in columns:
            op.add_column(table, sa.Column("build_version_id", sa.Integer(), nullable=True))
        existing_indexes = inspector.get_indexes(table)
        index_name = f"ix_{table[:18]}_build_ver"
        if not any(item.get("column_names") == ["build_version_id"] for item in existing_indexes):
            op.create_index(index_name, table, ["build_version_id"])
        foreign_keys = inspector.get_foreign_keys(table)
        already_bound = any(
            item.get("referred_table") == "application_build_versions"
            and item.get("constrained_columns") == ["build_version_id"]
            for item in foreign_keys
        )
        if not already_bound:
            with op.batch_alter_table(table) as batch_op:
                batch_op.create_foreign_key(
                    f"fk_{table[:18]}_build_ver",
                    "application_build_versions",
                    ["build_version_id"],
                    ["id"],
                )


def downgrade():
    for table in ("approval_records", "release_records", "pipeline_executions"):
        inspector = sa.inspect(op.get_bind())
        for foreign_key in inspector.get_foreign_keys(table):
            if foreign_key.get("referred_table") == "application_build_versions" and foreign_key.get("constrained_columns") == ["build_version_id"]:
                with op.batch_alter_table(table) as batch_op:
                    batch_op.drop_constraint(foreign_key["name"], type_="foreignkey")
        for index in inspector.get_indexes(table):
            if index.get("column_names") == ["build_version_id"]:
                op.drop_index(index["name"], table_name=table)
        if "build_version_id" in {column["name"] for column in inspector.get_columns(table)}:
            op.drop_column(table, "build_version_id")
    for index in (
        "ix_application_build_versions_pipeline_run_name",
        "ix_application_build_versions_status",
        "ix_application_build_versions_project_id",
        "ix_application_build_versions_application_id",
    ):
        op.drop_index(index, table_name="application_build_versions")
    op.drop_table("application_build_versions")
