"""add payment oversight fields"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fb1c2d3e4f5g'
down_revision = 'fa0b1c2d3e4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('clinics', sa.Column('monthly_revenue_target_minor', sa.BigInteger(), nullable=False, server_default='0'))
    op.add_column('charge_catalog', sa.Column('category', sa.String(length=50), nullable=False, server_default='OTHER'))
    op.add_column('billing_ledger_entries', sa.Column('charge_code', sa.String(length=64), nullable=True))
    op.create_index('ix_billing_ledger_charge_code', 'billing_ledger_entries', ['charge_code'])


def downgrade():
    op.drop_index('ix_billing_ledger_charge_code', table_name='billing_ledger_entries')
    op.drop_column('billing_ledger_entries', 'charge_code')
    op.drop_column('charge_catalog', 'category')
    op.drop_column('clinics', 'monthly_revenue_target_minor')
