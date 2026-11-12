"""phase7_saas_subscription_and_limits

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-11-13 04:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('clinics', schema=None) as batch_op:
        batch_op.add_column(sa.Column('subscription_plan', sa.String(length=30), nullable=False, server_default='Trial'))
        batch_op.add_column(sa.Column('subscription_status', sa.String(length=30), nullable=False, server_default='trialing'))
        batch_op.add_column(sa.Column('trial_ends_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('subscription_ends_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('max_pets', sa.Integer(), nullable=False, server_default='100'))
        batch_op.add_column(sa.Column('max_users', sa.Integer(), nullable=False, server_default='3'))


def downgrade():
    with op.batch_alter_table('clinics', schema=None) as batch_op:
        batch_op.drop_column('max_users')
        batch_op.drop_column('max_pets')
        batch_op.drop_column('subscription_ends_at')
        batch_op.drop_column('trial_ends_at')
        batch_op.drop_column('subscription_status')
        batch_op.drop_column('subscription_plan')

