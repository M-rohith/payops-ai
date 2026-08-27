"""Document minor-unit monetary columns.

Revision ID: 20260826_02
Revises: 20260826_01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260826_02"
down_revision: str | Sequence[str] | None = "20260826_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("orders", "payments", "refunds"):
        op.alter_column(table, "amount", comment="Amount in minor currency units")


def downgrade() -> None:
    for table in ("orders", "payments", "refunds"):
        op.alter_column(table, "amount", existing_comment="Amount in minor currency units", comment=None)
