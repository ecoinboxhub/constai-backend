"""Add client_uuid column to projects and project_documents

Revision ID: 0004_add_client_uuid
Revises: 0003_add_phone_number_to_users
Create Date: 2026-06-16 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0004_add_client_uuid'
down_revision = '0003_add_phone_number_to_users'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('client_uuid', sa.String(length=64), nullable=True, index=True))
    op.add_column('project_documents', sa.Column('client_uuid', sa.String(length=64), nullable=True, index=True))


def downgrade() -> None:
    op.drop_column('projects', 'client_uuid')
    op.drop_column('project_documents', 'client_uuid')
