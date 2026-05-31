"""initial production tables

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(120), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("budget_ngn", sa.Float, nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "supplier_quotes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("supplier", sa.String(120), nullable=False),
        sa.Column("material", sa.String(120), nullable=False),
        sa.Column("location", sa.String(120), nullable=False),
        sa.Column("price_ngn", sa.Float, nullable=False),
        sa.Column("unit", sa.String(80), nullable=False),
        sa.Column("reliability_score", sa.Float, nullable=True),
        sa.Column("forecast_price_ngn", sa.Float, nullable=True),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "weather_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("temperature_c", sa.Float, nullable=False),
        sa.Column("rainfall_mm", sa.Float, nullable=False),
        sa.Column("wind_speed_kmh", sa.Float, nullable=False),
        sa.Column("humidity_pct", sa.Float, nullable=False),
        sa.Column("condition", sa.String(120), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "delay_predictions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("features_json", sa.JSON, nullable=False),
        sa.Column("delay_risk", sa.Float, nullable=False),
        sa.Column("will_delay", sa.Boolean, nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "cost_estimates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("inputs_json", sa.JSON, nullable=False),
        sa.Column("estimate_ngn", sa.Float, nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("mape", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "equipment",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("equipment_type", sa.String(120), nullable=False),
        sa.Column("serial_number", sa.String(120), nullable=False),
        sa.Column("purchase_date", sa.Date, nullable=True),
        sa.Column("last_maintenance_date", sa.Date, nullable=True),
        sa.Column("runtime_hours", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "maintenance_predictions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("equipment_id", sa.Integer, sa.ForeignKey("equipment.id"), nullable=True),
        sa.Column("equipment_type", sa.String(120), nullable=False),
        sa.Column("inputs_json", sa.JSON, nullable=False),
        sa.Column("failure_risk", sa.Float, nullable=False),
        sa.Column("due_days", sa.Integer, nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "safety_findings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("log_text", sa.Text, nullable=False),
        sa.Column("findings_json", sa.JSON, nullable=False),
        sa.Column("overall_risk_level", sa.String(20), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.String(120), nullable=True),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("response_status", sa.Integer, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    for table in [
        "audit_logs",
        "safety_findings",
        "maintenance_predictions",
        "equipment",
        "cost_estimates",
        "delay_predictions",
        "weather_logs",
        "supplier_quotes",
        "projects",
        "users",
    ]:
        op.drop_table(table)
