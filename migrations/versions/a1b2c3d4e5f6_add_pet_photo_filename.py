"""add_pet_photo_filename

Revision ID: a1b2c3d4e5f6
Revises: 5e1b2c3d4f5a
Create Date: 2026-11-13 03:33:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '5e1b2c3d4f5a'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('pets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('photo_filename', sa.String(length=255), nullable=True))


def downgrade():
    with op.batch_alter_table('pets', schema=None) as batch_op:
        batch_op.drop_column('photo_filename')
