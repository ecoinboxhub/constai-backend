"""add phone_number to users

Revision ID: 0003_add_phone_number_to_users
Revises: 0002_add_project_fields
Create Date: 2026-05-22
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_add_phone_number_to_users"
down_revision = "0002_add_project_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone_number", sa.String(50), nullable=True))
    op.create_index("ix_users_phone_number", "users", ["phone_number"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_phone_number", table_name="users")
    op.drop_column("users", "phone_number")