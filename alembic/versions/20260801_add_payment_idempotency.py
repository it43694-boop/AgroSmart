"""add payment_idempotency table

Revision ID: 20260801_add_payment_idempotency
Revises: 2f0cfc9fca85
Create Date: 2026-08-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260801_add_payment_idempotency'
down_revision = '2f0cfc9fca85'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'payment_idempotency',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('idempotency_key', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('result_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
    )
    op.create_index(op.f('ix_payment_idempotency_idempotency_key'), 'payment_idempotency', ['idempotency_key'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_payment_idempotency_idempotency_key'), table_name='payment_idempotency')
    op.drop_table('payment_idempotency')