"""scope application delivery

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa


revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    with op.batch_alter_table("pipeline_executions") as batch_op:
        batch_op.add_column(sa.Column("project_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column(
            "environment",
            sa.String(length=30),
            nullable=False,
            server_default="dev",
        ))
        batch_op.add_column(sa.Column(
            "kubernetes_cluster_id",
            sa.Integer(),
            nullable=True,
        ))
        batch_op.add_column(sa.Column(
            "deploy_namespace",
            sa.String(length=120),
            nullable=False,
            server_default="default",
        ))
        batch_op.create_foreign_key(
            "fk_pipeline_executions_project_id_projects",
            "projects",
            ["project_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_pipeline_executions_kubernetes_cluster_id_kubernetes_clusters",
            "kubernetes_clusters",
            ["kubernetes_cluster_id"],
            ["id"],
        )
        batch_op.create_index(
            batch_op.f("ix_pipeline_executions_project_id"),
            ["project_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_pipeline_executions_environment"),
            ["environment"],
            unique=False,
        )

    with op.batch_alter_table("release_records") as batch_op:
        batch_op.add_column(sa.Column(
            "kubernetes_cluster_id",
            sa.Integer(),
            nullable=True,
        ))
        batch_op.create_foreign_key(
            "fk_release_records_kubernetes_cluster_id_kubernetes_clusters",
            "kubernetes_clusters",
            ["kubernetes_cluster_id"],
            ["id"],
        )

    with op.batch_alter_table("approval_records") as batch_op:
        batch_op.add_column(sa.Column(
            "kubernetes_cluster_id",
            sa.Integer(),
            nullable=True,
        ))
        batch_op.create_foreign_key(
            "fk_approval_records_kubernetes_cluster_id_kubernetes_clusters",
            "kubernetes_clusters",
            ["kubernetes_cluster_id"],
            ["id"],
        )

    default_project_id = connection.execute(sa.text(
        "SELECT id FROM projects WHERE `key` = 'default' LIMIT 1"
    )).scalar()
    if default_project_id is None:
        raise RuntimeError("Default Project with key 'default' is required")

    connection.execute(
        sa.text(
            "UPDATE applications SET project_id = :project_id "
            "WHERE project_id IS NULL"
        ),
        {"project_id": default_project_id},
    )
    for table_name in (
        "pipeline_executions",
        "release_records",
        "approval_records",
    ):
        connection.execute(sa.text(
            f"UPDATE {table_name} SET project_id = ("
            "SELECT applications.project_id FROM applications "
            f"WHERE applications.id = {table_name}.application_id"
            ")"
        ))

    with op.batch_alter_table("applications") as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sa.Integer(),
            nullable=False,
        )

    with op.batch_alter_table("pipeline_executions") as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.alter_column(
            "environment",
            existing_type=sa.String(length=30),
            nullable=False,
            server_default=None,
        )
        batch_op.alter_column(
            "deploy_namespace",
            existing_type=sa.String(length=120),
            nullable=False,
            server_default=None,
        )

    with op.batch_alter_table("release_records") as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sa.Integer(),
            nullable=False,
        )

    with op.batch_alter_table("approval_records") as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sa.Integer(),
            nullable=False,
        )


def downgrade():
    with op.batch_alter_table("approval_records") as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.drop_constraint(
            "fk_approval_records_kubernetes_cluster_id_kubernetes_clusters",
            type_="foreignkey",
        )
        batch_op.drop_column("kubernetes_cluster_id")

    with op.batch_alter_table("release_records") as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.drop_constraint(
            "fk_release_records_kubernetes_cluster_id_kubernetes_clusters",
            type_="foreignkey",
        )
        batch_op.drop_column("kubernetes_cluster_id")

    with op.batch_alter_table("pipeline_executions") as batch_op:
        batch_op.drop_index(batch_op.f("ix_pipeline_executions_environment"))
        batch_op.drop_index(batch_op.f("ix_pipeline_executions_project_id"))
        batch_op.drop_constraint(
            "fk_pipeline_executions_kubernetes_cluster_id_kubernetes_clusters",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_pipeline_executions_project_id_projects",
            type_="foreignkey",
        )
        batch_op.drop_column("deploy_namespace")
        batch_op.drop_column("kubernetes_cluster_id")
        batch_op.drop_column("environment")
        batch_op.drop_column("project_id")

    with op.batch_alter_table("applications") as batch_op:
        batch_op.alter_column(
            "project_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
