"""Add missing company fields

Revision ID: add4bbea393e
Revises: 0002_add_project_fields
Create Date: 2026-05-09 20:53:20.413225

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add4bbea393e'
down_revision = '0002_add_project_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing company metadata columns and safe model-aligned columns.
    op.add_column('companies', sa.Column('industry', sa.String(length=120), nullable=True))
    op.add_column('companies', sa.Column('country', sa.String(length=120), nullable=True))
    op.add_column('companies', sa.Column('contact_email', sa.String(length=255), nullable=True))
    op.add_column('companies', sa.Column('subscription_tier', sa.String(length=50), nullable=False, server_default='free'))
    op.add_column('companies', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')))

    op.add_column('cost_estimates', sa.Column('company_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'cost_estimates', 'companies', ['company_id'], ['id'])
    op.add_column('delay_predictions', sa.Column('company_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'delay_predictions', 'companies', ['company_id'], ['id'])
    op.add_column('project_documents', sa.Column('company_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'project_documents', 'companies', ['company_id'], ['id'])

    op.drop_index(op.f('ix_projects_city'), table_name='projects')
    op.create_index(op.f('ix_projects_location'), 'projects', ['location'], unique=False)
    op.create_index(op.f('ix_projects_project_type'), 'projects', ['project_type'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # Revert added company metadata and related foreign keys.
    op.drop_index(op.f('ix_projects_project_type'), table_name='projects')
    op.drop_index(op.f('ix_projects_location'), table_name='projects')
    op.create_index(op.f('ix_projects_city'), 'projects', ['location'], unique=False)

    op.drop_constraint(None, 'project_documents', type_='foreignkey')
    op.drop_column('project_documents', 'company_id')
    op.drop_constraint(None, 'delay_predictions', type_='foreignkey')
    op.drop_column('delay_predictions', 'company_id')
    op.drop_constraint(None, 'cost_estimates', type_='foreignkey')
    op.drop_column('cost_estimates', 'company_id')

    op.drop_column('companies', 'updated_at')
    op.drop_column('companies', 'subscription_tier')
    op.drop_column('companies', 'contact_email')
    op.drop_column('companies', 'country')
    op.drop_column('companies', 'industry')
    # ### end Alembic commands ###
