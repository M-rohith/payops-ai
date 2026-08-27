"""Initial payment operations schema."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260826_01"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("merchants", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(200), nullable=False, unique=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("customers", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("merchant_id", sa.Integer(), sa.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(200), nullable=False), sa.Column("email", sa.String(320), nullable=False), sa.Column("phone", sa.String(30)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_customers_merchant_id", "customers", ["merchant_id"])
    op.create_table("orders", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("merchant_id", sa.Integer(), sa.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False), sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False), sa.Column("external_order_id", sa.String(100), nullable=False, unique=True), sa.Column("amount", sa.Integer(), nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_orders_merchant_id", "orders", ["merchant_id"]); op.create_index("ix_orders_customer_id", "orders", ["customer_id"]); op.create_index("ix_orders_status", "orders", ["status"])
    op.create_table("payments", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("merchant_id", sa.Integer(), sa.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False), sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False), sa.Column("external_payment_id", sa.String(100), nullable=False, unique=True), sa.Column("amount", sa.Integer(), nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("method", sa.String(30), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("error_code", sa.String(100)), sa.Column("error_description", sa.Text()), sa.Column("captured", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    for name, cols in [("ix_payments_merchant_id", ["merchant_id"]), ("ix_payments_order_id", ["order_id"]), ("ix_payments_method", ["method"]), ("ix_payments_status", ["status"]), ("ix_payments_merchant_created", ["merchant_id", "created_at"])]: op.create_index(name, "payments", cols)
    op.create_table("refunds", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("merchant_id", sa.Integer(), sa.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False), sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id"), nullable=False), sa.Column("external_refund_id", sa.String(100), nullable=False, unique=True), sa.Column("amount", sa.Integer(), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_refunds_merchant_id", "refunds", ["merchant_id"]); op.create_index("ix_refunds_payment_id", "refunds", ["payment_id"])
    op.create_table("settlements", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("merchant_id", sa.Integer(), sa.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False), sa.Column("external_settlement_id", sa.String(100), nullable=False, unique=True), sa.Column("expected_amount", sa.Integer(), nullable=False), sa.Column("actual_amount", sa.Integer(), nullable=False), sa.Column("fees", sa.Integer(), nullable=False), sa.Column("adjustments", sa.Integer(), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("settled_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_settlements_merchant_id", "settlements", ["merchant_id"]); op.create_index("ix_settlements_status", "settlements", ["status"])
    op.create_table("alerts", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("merchant_id", sa.Integer(), sa.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False), sa.Column("type", sa.String(60), nullable=False), sa.Column("severity", sa.String(20), nullable=False), sa.Column("title", sa.String(250), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("metric_value", sa.Float()), sa.Column("baseline_value", sa.Float()), sa.Column("status", sa.String(30), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_alerts_merchant_id", "alerts", ["merchant_id"]); op.create_index("ix_alerts_severity", "alerts", ["severity"]); op.create_index("ix_alerts_status", "alerts", ["status"])
    op.create_table("reconciliation_issues", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("merchant_id", sa.Integer(), sa.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False), sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id")), sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id")), sa.Column("issue_type", sa.String(80), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    for name, cols in [("ix_reconciliation_issues_merchant_id", ["merchant_id"]), ("ix_reconciliation_issues_order_id", ["order_id"]), ("ix_reconciliation_issues_payment_id", ["payment_id"]), ("ix_reconciliation_issues_status", ["status"])]: op.create_index(name, "reconciliation_issues", cols)


def downgrade() -> None:
    for table in ["reconciliation_issues", "alerts", "settlements", "refunds", "payments", "orders", "customers", "merchants"]:
        op.drop_table(table)
