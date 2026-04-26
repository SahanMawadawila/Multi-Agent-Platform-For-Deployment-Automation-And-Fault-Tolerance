"""add deployment vitals table

Revision ID: z9y8x7w6v5u4
Revises: h2i3j4k5l6m7
Create Date: 2026-04-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "z9y8x7w6v5u4"
down_revision = "h2i3j4k5l6m7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deployment_vitals",
        sa.Column("vital_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("namespace", sa.String(), nullable=False),
        sa.Column("pod_name", sa.String(), nullable=False),
        sa.Column("pod_phase", sa.String(), nullable=True),
        sa.Column("cpu_millicores", sa.Integer(), nullable=False),
        sa.Column("memory_mebibytes", sa.Integer(), nullable=False),
        sa.Column("probe_status", sa.String(), nullable=True),
        sa.Column("probe_latency_ms", sa.Integer(), nullable=True),
        sa.Column("sampled_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["user_projects.project_id"]),
        sa.PrimaryKeyConstraint("vital_id"),
    )
    op.create_index(op.f("ix_deployment_vitals_project_id"), "deployment_vitals", ["project_id"], unique=False)
    op.create_index(op.f("ix_deployment_vitals_namespace"), "deployment_vitals", ["namespace"], unique=False)
    op.create_index(op.f("ix_deployment_vitals_pod_name"), "deployment_vitals", ["pod_name"], unique=False)
    op.create_index(op.f("ix_deployment_vitals_sampled_at"), "deployment_vitals", ["sampled_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_deployment_vitals_sampled_at"), table_name="deployment_vitals")
    op.drop_index(op.f("ix_deployment_vitals_pod_name"), table_name="deployment_vitals")
    op.drop_index(op.f("ix_deployment_vitals_namespace"), table_name="deployment_vitals")
    op.drop_index(op.f("ix_deployment_vitals_project_id"), table_name="deployment_vitals")
    op.drop_table("deployment_vitals")