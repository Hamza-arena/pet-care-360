"""add_multitenancy_clinic_id

Revision ID: 0de89771a5af
Revises: 3d67e928f68c
Create Date: 2026-11-13 02:41:56.913717

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0de89771a5af'
down_revision = '3d67e928f68c'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('invoices', schema=None) as batch_op:
        batch_op.add_column(sa.Column('clinic_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_invoices_clinic_id'), ['clinic_id'], unique=False)
        batch_op.create_foreign_key('fk_invoices_clinic_id', 'clinics', ['clinic_id'], ['id'])

    with op.batch_alter_table('lab_orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('clinic_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_lab_orders_clinic_id'), ['clinic_id'], unique=False)
        batch_op.create_foreign_key('fk_lab_orders_clinic_id', 'clinics', ['clinic_id'], ['id'])

    with op.batch_alter_table('medical_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('clinic_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_medical_records_clinic_id'), ['clinic_id'], unique=False)
        batch_op.create_foreign_key('fk_medical_records_clinic_id', 'clinics', ['clinic_id'], ['id'])

    with op.batch_alter_table('medicines', schema=None) as batch_op:
        batch_op.add_column(sa.Column('clinic_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_medicines_clinic_id'), ['clinic_id'], unique=False)
        batch_op.create_foreign_key('fk_medicines_clinic_id', 'clinics', ['clinic_id'], ['id'])

    with op.batch_alter_table('owners', schema=None) as batch_op:
        batch_op.add_column(sa.Column('clinic_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_owners_clinic_id'), ['clinic_id'], unique=False)
        batch_op.create_foreign_key('fk_owners_clinic_id', 'clinics', ['clinic_id'], ['id'])

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('clinic_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_users_clinic_id'), ['clinic_id'], unique=False)
        batch_op.create_foreign_key('fk_users_clinic_id', 'clinics', ['clinic_id'], ['id'])


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('fk_users_clinic_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_users_clinic_id'))
        batch_op.drop_column('clinic_id')

    with op.batch_alter_table('owners', schema=None) as batch_op:
        batch_op.drop_constraint('fk_owners_clinic_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_owners_clinic_id'))
        batch_op.drop_column('clinic_id')

    with op.batch_alter_table('medicines', schema=None) as batch_op:
        batch_op.drop_constraint('fk_medicines_clinic_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_medicines_clinic_id'))
        batch_op.drop_column('clinic_id')

    with op.batch_alter_table('medical_records', schema=None) as batch_op:
        batch_op.drop_constraint('fk_medical_records_clinic_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_medical_records_clinic_id'))
        batch_op.drop_column('clinic_id')

    with op.batch_alter_table('lab_orders', schema=None) as batch_op:
        batch_op.drop_constraint('fk_lab_orders_clinic_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_lab_orders_clinic_id'))
        batch_op.drop_column('clinic_id')

    with op.batch_alter_table('invoices', schema=None) as batch_op:
        batch_op.drop_constraint('fk_invoices_clinic_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_invoices_clinic_id'))
        batch_op.drop_column('clinic_id')
