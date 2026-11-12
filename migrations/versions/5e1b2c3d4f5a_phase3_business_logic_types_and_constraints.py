"""phase3_business_logic_types_and_constraints

Revision ID: 5e1b2c3d4f5a
Revises: 0de89771a5af
Create Date: 2026-11-13 03:25:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5e1b2c3d4f5a'
down_revision = '0de89771a5af'
branch_labels = None
depends_on = None


def upgrade():
    # 1. clinics
    with op.batch_alter_table('clinics', schema=None) as batch_op:
        batch_op.add_column(sa.Column('currency', sa.String(length=10), server_default='PKR', nullable=False))
        batch_op.add_column(sa.Column('tax_rate', sa.Numeric(precision=5, scale=2), server_default='16.00', nullable=False))
        batch_op.add_column(sa.Column('invoice_sequence', sa.Integer(), server_default='0', nullable=False))

    # 2. appointments
    with op.batch_alter_table('appointments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('room_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_appointments_room_id', 'rooms', ['room_id'], ['id'])

    # 3. appointment_types
    with op.batch_alter_table('appointment_types', schema=None) as batch_op:
        batch_op.alter_column('base_fee',
                              existing_type=sa.Float(),
                              type_=sa.Numeric(precision=12, scale=2),
                              existing_nullable=True)

    # 4. invoices
    with op.batch_alter_table('invoices', schema=None) as batch_op:
        batch_op.alter_column('subtotal',
                              existing_type=sa.Float(),
                              type_=sa.Numeric(precision=12, scale=2),
                              existing_nullable=True)
        batch_op.alter_column('tax_amount',
                              existing_type=sa.Float(),
                              type_=sa.Numeric(precision=12, scale=2),
                              existing_nullable=True)
        batch_op.alter_column('discount_amount',
                              existing_type=sa.Float(),
                              type_=sa.Numeric(precision=12, scale=2),
                              existing_nullable=True)
        batch_op.alter_column('total_amount',
                              existing_type=sa.Float(),
                              type_=sa.Numeric(precision=12, scale=2),
                              existing_nullable=True)
        batch_op.alter_column('paid_amount',
                              existing_type=sa.Float(),
                              type_=sa.Numeric(precision=12, scale=2),
                              existing_nullable=True)
        batch_op.create_unique_constraint('uq_invoice_clinic_number', ['clinic_id', 'invoice_number'])

    # 5. invoice_items
    with op.batch_alter_table('invoice_items', schema=None) as batch_op:
        batch_op.alter_column('unit_price',
                              existing_type=sa.Float(),
                              type_=sa.Numeric(precision=12, scale=2),
                              existing_nullable=False)
        batch_op.alter_column('discount',
                              existing_type=sa.Float(),
                              type_=sa.Numeric(precision=12, scale=2),
                              existing_nullable=True)
        batch_op.alter_column('total_price',
                              existing_type=sa.Float(),
                              type_=sa.Numeric(precision=12, scale=2),
                              existing_nullable=False)

    # 6. payments
    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.alter_column('amount',
                              existing_type=sa.Float(),
                              type_=sa.Numeric(precision=12, scale=2),
                              existing_nullable=False)

    # 7. medicines
    with op.batch_alter_table('medicines', schema=None) as batch_op:
        batch_op.alter_column('base_price',
                              existing_type=sa.Float(),
                              type_=sa.Numeric(precision=12, scale=2),
                              existing_nullable=True)

    # 8. medicine_batches
    with op.batch_alter_table('medicine_batches', schema=None) as batch_op:
        batch_op.alter_column('purchase_price',
                              existing_type=sa.Float(),
                              type_=sa.Numeric(precision=12, scale=2),
                              existing_nullable=True)
        batch_op.alter_column('selling_price',
                              existing_type=sa.Float(),
                              type_=sa.Numeric(precision=12, scale=2),
                              existing_nullable=True)

    # 9. lab_tests
    with op.batch_alter_table('lab_tests', schema=None) as batch_op:
        batch_op.alter_column('base_price',
                              existing_type=sa.Float(),
                              type_=sa.Numeric(precision=12, scale=2),
                              existing_nullable=True)


def downgrade():
    with op.batch_alter_table('lab_tests', schema=None) as batch_op:
        batch_op.alter_column('base_price',
                              existing_type=sa.Numeric(precision=12, scale=2),
                              type_=sa.Float(),
                              existing_nullable=True)

    with op.batch_alter_table('medicine_batches', schema=None) as batch_op:
        batch_op.alter_column('selling_price',
                              existing_type=sa.Numeric(precision=12, scale=2),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('purchase_price',
                              existing_type=sa.Numeric(precision=12, scale=2),
                              type_=sa.Float(),
                              existing_nullable=True)

    with op.batch_alter_table('medicines', schema=None) as batch_op:
        batch_op.alter_column('base_price',
                              existing_type=sa.Numeric(precision=12, scale=2),
                              type_=sa.Float(),
                              existing_nullable=True)

    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.alter_column('amount',
                              existing_type=sa.Numeric(precision=12, scale=2),
                              type_=sa.Float(),
                              existing_nullable=False)

    with op.batch_alter_table('invoice_items', schema=None) as batch_op:
        batch_op.alter_column('total_price',
                              existing_type=sa.Numeric(precision=12, scale=2),
                              type_=sa.Float(),
                              existing_nullable=False)
        batch_op.alter_column('discount',
                              existing_type=sa.Numeric(precision=12, scale=2),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('unit_price',
                              existing_type=sa.Numeric(precision=12, scale=2),
                              type_=sa.Float(),
                              existing_nullable=False)

    with op.batch_alter_table('invoices', schema=None) as batch_op:
        batch_op.drop_constraint('uq_invoice_clinic_number', type_='unique')
        batch_op.alter_column('paid_amount',
                              existing_type=sa.Numeric(precision=12, scale=2),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('total_amount',
                              existing_type=sa.Numeric(precision=12, scale=2),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('discount_amount',
                              existing_type=sa.Numeric(precision=12, scale=2),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('tax_amount',
                              existing_type=sa.Numeric(precision=12, scale=2),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('subtotal',
                              existing_type=sa.Numeric(precision=12, scale=2),
                              type_=sa.Float(),
                              existing_nullable=True)

    with op.batch_alter_table('appointment_types', schema=None) as batch_op:
        batch_op.alter_column('base_fee',
                              existing_type=sa.Numeric(precision=12, scale=2),
                              type_=sa.Float(),
                              existing_nullable=True)

    with op.batch_alter_table('appointments', schema=None) as batch_op:
        batch_op.drop_constraint('fk_appointments_room_id', type_='foreignkey')
        batch_op.drop_column('room_id')

    with op.batch_alter_table('clinics', schema=None) as batch_op:
        batch_op.drop_column('invoice_sequence')
        batch_op.drop_column('tax_rate')
        batch_op.drop_column('currency')

