"""Add missing project fields and rename legacy project columns

Revision ID: 0002_add_project_fields
Revises: 0001_initial
Create Date: 2026-05-08
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_add_project_fields"
down_revision = "f703e89c847e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.alter_column(
            "city",
            new_column_name="location",
            existing_type=sa.String(120),
            nullable=False,
        )
        batch_op.alter_column(
            "end_date",
            new_column_name="expected_end_date",
            existing_type=sa.Date,
            nullable=True,
        )
        batch_op.alter_column(
            "status",
            new_column_name="project_status",
            existing_type=sa.String(50),
            nullable=False,
        )
        batch_op.alter_column(
            "budget_ngn",
            new_column_name="budget_allocated",
            existing_type=sa.Float,
            nullable=True,
        )
        batch_op.add_column(
            sa.Column(
                "contractor_name",
                sa.String(255),
                nullable=False,
                server_default=sa.text("'Unknown'"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "project_type",
                sa.String(120),
                nullable=False,
                server_default=sa.text("'General'"),
            )
        )
        batch_op.add_column(sa.Column("actual_end_date", sa.Date, nullable=True))
        batch_op.add_column(sa.Column("budget_spent", sa.Float, nullable=True))
        batch_op.add_column(sa.Column("workforce_count", sa.Integer, nullable=True))
        batch_op.add_column(sa.Column("equipment_count", sa.Integer, nullable=True))
        batch_op.add_column(sa.Column("material_cost", sa.Float, nullable=True))
        batch_op.add_column(sa.Column("completion_percentage", sa.Float, nullable=True))
        batch_op.add_column(sa.Column("weather_delay_days", sa.Integer, nullable=True))
        batch_op.add_column(sa.Column("safety_incidents", sa.Integer, nullable=True))
        batch_op.add_column(sa.Column("inspection_score", sa.Float, nullable=True))
        batch_op.add_column(sa.Column("task_completion_rate", sa.Float, nullable=True))
        batch_op.add_column(sa.Column("daily_progress_rate", sa.Float, nullable=True))
        batch_op.add_column(
            sa.Column(
                "delay_status",
                sa.String(50),
                nullable=False,
                server_default=sa.text("'on_time'"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "risk_level",
                sa.String(20),
                nullable=False,
                server_default=sa.text("'medium'"),
            )
        )

    # Remove temporary server defaults once existing rows have values
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.alter_column("contractor_name", server_default=None)
        batch_op.alter_column("project_type", server_default=None)
        batch_op.alter_column("delay_status", server_default=None)
        batch_op.alter_column("risk_level", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.drop_column("risk_level")
        batch_op.drop_column("delay_status")
        batch_op.drop_column("daily_progress_rate")
        batch_op.drop_column("task_completion_rate")
        batch_op.drop_column("inspection_score")
        batch_op.drop_column("safety_incidents")
        batch_op.drop_column("weather_delay_days")
        batch_op.drop_column("completion_percentage")
        batch_op.drop_column("material_cost")
        batch_op.drop_column("equipment_count")
        batch_op.drop_column("workforce_count")
        batch_op.drop_column("budget_spent")
        batch_op.drop_column("actual_end_date")
        batch_op.drop_column("project_type")
        batch_op.drop_column("contractor_name")
        batch_op.alter_column(
            "location",
            new_column_name="city",
            existing_type=sa.String(120),
            nullable=False,
        )
        batch_op.alter_column(
            "expected_end_date",
            new_column_name="end_date",
            existing_type=sa.Date,
            nullable=True,
        )
        batch_op.alter_column(
            "project_status",
            new_column_name="status",
            existing_type=sa.String(50),
            nullable=False,
        )
        batch_op.alter_column(
            "budget_allocated",
            new_column_name="budget_ngn",
            existing_type=sa.Float,
            nullable=True,
        )
