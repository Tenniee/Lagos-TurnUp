"""add first_name last_name role is_deactivated columns

Revision ID: 190db2dc1902
Revises: 
Create Date: 2025-08-11 22:34:09.951149

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '190db2dc1902'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('sub_admins', sa.Column('first_name', sa.String(100), nullable=True))
    op.add_column('sub_admins', sa.Column('last_name', sa.String(100), nullable=True))
    op.add_column('sub_admins', sa.Column('role', sa.String(50), nullable=False, server_default='sub-admin'))
    op.add_column('sub_admins', sa.Column('is_deactivated', sa.Boolean(), nullable=False, server_default=sa.text('false')))

def downgrade():
    op.drop_column('sub_admins', 'first_name')
    op.drop_column('sub_admins', 'last_name')
    op.drop_column('sub_admins', 'role')
    op.drop_column('sub_admins', 'is_deactivated')
