"""empty message

Revision ID: 7d62460c9be1
Revises: 19a7401bb0fc
Create Date: 2020-11-17 21:05:56.746979

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '7d62460c9be1'
down_revision = '19a7401bb0fc'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('stalked_page', sa.Column('user_id', sa.Integer(), nullable=True))
    op.drop_constraint('stalked_page_ibfk_1', 'stalked_page', type_='foreignkey')
    op.create_foreign_key(None, 'stalked_page', 'user', ['user_id'], ['id'])
    op.drop_column('stalked_page', 'user')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('stalked_page', sa.Column('user', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'stalked_page', type_='foreignkey')
    op.create_foreign_key('stalked_page_ibfk_1', 'stalked_page', 'user', ['user'], ['id'])
    op.drop_column('stalked_page', 'user_id')
    # ### end Alembic commands ###
