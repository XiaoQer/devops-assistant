"""project centric platform model

Revision ID: f1a2b3c4d5e6
Revises: e7f42d9ac310
Create Date: 2026-07-02
"""
from alembic import op
import sqlalchemy as sa


revision = "f1a2b3c4d5e6"
down_revision = "e7f42d9ac310"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("key", sa.String(length=64), nullable=True))
        batch_op.create_index(batch_op.f("ix_projects_key"), ["key"], unique=True)

    connection.execute(sa.text("UPDATE projects SET `key` = CONCAT('project-', id) WHERE `key` IS NULL"))

    with op.batch_alter_table("projects") as batch_op:
        batch_op.alter_column("key", existing_type=sa.String(length=64), nullable=False)

    op.create_table(
        "project_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "email", name="uq_project_member_email"),
    )
    with op.batch_alter_table("project_members") as batch_op:
        batch_op.create_index(batch_op.f("ix_project_members_project_id"), ["project_id"], unique=False)

    op.create_table(
        "kubernetes_clusters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("kube_context", sa.String(length=200), nullable=False),
        sa.Column("namespace_prefix", sa.String(length=120), nullable=True),
        sa.Column("api_server", sa.String(length=300), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "name", name="uq_project_cluster_name"),
    )
    with op.batch_alter_table("kubernetes_clusters") as batch_op:
        batch_op.create_index(batch_op.f("ix_kubernetes_clusters_project_id"), ["project_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_kubernetes_clusters_is_default"), ["is_default"], unique=False)
        batch_op.create_index(batch_op.f("ix_kubernetes_clusters_is_active"), ["is_active"], unique=False)

    with op.batch_alter_table("applications") as batch_op:
        batch_op.drop_constraint("name", type_="unique")

    default_project = connection.execute(
        sa.text("SELECT id FROM projects WHERE `key` = 'default' LIMIT 1")
    ).scalar()
    if default_project is None:
        connection.execute(sa.text(
            "INSERT INTO projects (`key`, name, description, created_at, updated_at) "
            "VALUES ('default', 'Default Project', '系统默认项目', UTC_TIMESTAMP(), UTC_TIMESTAMP())"
        ))
        default_project = connection.execute(
            sa.text("SELECT id FROM projects WHERE `key` = 'default' LIMIT 1")
        ).scalar()
    connection.execute(
        sa.text("UPDATE applications SET project_id = :project_id WHERE project_id IS NULL"),
        {"project_id": default_project},
    )

    with op.batch_alter_table("container_registries") as batch_op:
        batch_op.add_column(sa.Column("project_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_container_registries_project_id_projects",
            "projects",
            ["project_id"],
            ["id"],
        )
        batch_op.create_index(batch_op.f("ix_container_registries_project_id"), ["project_id"], unique=False)
        batch_op.drop_constraint("name", type_="unique")

    with op.batch_alter_table("application_environments") as batch_op:
        batch_op.add_column(sa.Column("kubernetes_cluster_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_application_environments_kubernetes_cluster_id_kubernetes_clusters",
            "kubernetes_clusters",
            ["kubernetes_cluster_id"],
            ["id"],
        )
        batch_op.create_index(batch_op.f("ix_application_environments_kubernetes_cluster_id"), ["kubernetes_cluster_id"], unique=False)


def downgrade():
    with op.batch_alter_table("application_environments") as batch_op:
        batch_op.drop_index(batch_op.f("ix_application_environments_kubernetes_cluster_id"))
        batch_op.drop_constraint("fk_application_environments_kubernetes_cluster_id_kubernetes_clusters", type_="foreignkey")
        batch_op.drop_column("kubernetes_cluster_id")

    with op.batch_alter_table("container_registries") as batch_op:
        batch_op.create_unique_constraint(None, ["name"])
        batch_op.drop_index(batch_op.f("ix_container_registries_project_id"))
        batch_op.drop_constraint("fk_container_registries_project_id_projects", type_="foreignkey")
        batch_op.drop_column("project_id")

    with op.batch_alter_table("applications") as batch_op:
        batch_op.create_unique_constraint(None, ["name"])

    with op.batch_alter_table("kubernetes_clusters") as batch_op:
        batch_op.drop_index(batch_op.f("ix_kubernetes_clusters_is_active"))
        batch_op.drop_index(batch_op.f("ix_kubernetes_clusters_is_default"))
        batch_op.drop_index(batch_op.f("ix_kubernetes_clusters_project_id"))
    op.drop_table("kubernetes_clusters")

    with op.batch_alter_table("project_members") as batch_op:
        batch_op.drop_index(batch_op.f("ix_project_members_project_id"))
    op.drop_table("project_members")

    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_index(batch_op.f("ix_projects_key"))
        batch_op.drop_column("key")

