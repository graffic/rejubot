"""First version

Revision ID: a6503305e193
Revises: 
Create Date: 2023-12-30 22:12:03.913733+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6503305e193'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('video_entries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('content_type', sa.String(length=255), nullable=False),
    sa.Column('width', sa.Integer(), nullable=False),
    sa.Column('height', sa.Integer(), nullable=False),
    sa.Column('url', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('url_entries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('channel_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('who', sa.String(length=255), nullable=False),
    sa.Column('who_id', sa.BigInteger(), nullable=False),
    sa.Column('url', sa.Text(), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('og_site', sa.Text(), nullable=True),
    sa.Column('og_title', sa.Text(), nullable=True),
    sa.Column('og_image', sa.Text(), nullable=True),
    sa.Column('og_description', sa.Text(), nullable=True),
    sa.Column('video_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['video_id'], ['video_entries.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_url_entries_channel_id'), 'url_entries', ['channel_id'], unique=False)
    op.create_index(op.f('ix_url_entries_created_at'), 'url_entries', ['created_at'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_url_entries_created_at'), table_name='url_entries')
    op.drop_index(op.f('ix_url_entries_channel_id'), table_name='url_entries')
    op.drop_table('url_entries')
    op.drop_table('video_entries')
    # ### end Alembic commands ###