"""Initial schema: users, orders, servers, transactions, support_tickets

Revision ID: 0001
Revises:
Create Date: 2026-07-13

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels = None
depends_on = None

provider_enum = sa.Enum("vultr", "hetzner", name="provider")
order_status_enum = sa.Enum(
    "pending", "paid", "provisioning", "completed", "failed", "cancelled",
    name="order_status",
)
server_status_enum = sa.Enum(
    "provisioning", "active", "stopped", "rebooting", "reinstalling",
    "expired", "deleted", "error",
    name="server_status",
)
transaction_type_enum = sa.Enum(
    "deposit", "purchase", "renewal", "refund", "referral_bonus", "admin_adjustment",
    name="transaction_type",
)
ticket_status_enum = sa.Enum("open", "answered", "closed", name="ticket_status")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(64)),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("balance", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_banned", sa.Boolean(), nullable=False),
        sa.Column("autorenew_enabled", sa.Boolean(), nullable=False),
        sa.Column("referrer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("referral_bonus_paid", sa.Boolean(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("status", order_status_enum, nullable=False),
        sa.Column("provider", provider_enum, nullable=False),
        sa.Column("region_id", sa.String(64), nullable=False),
        sa.Column("region_name", sa.String(128), nullable=False),
        sa.Column("plan_id", sa.String(64), nullable=False),
        sa.Column("plan_label", sa.String(255), nullable=False),
        sa.Column("image_id", sa.String(64), nullable=False),
        sa.Column("image_name", sa.String(128), nullable=False),
        sa.Column("hostname", sa.String(64), nullable=False),
        sa.Column("ssh_public_key", sa.Text()),
        sa.Column("months", sa.Integer(), nullable=False),
        sa.Column("provider_monthly_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_status", "orders", ["status"])

    op.create_table(
        "servers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="SET NULL")),
        sa.Column("provider", provider_enum, nullable=False),
        sa.Column("external_server_id", sa.String(64), nullable=False),
        sa.Column("status", server_status_enum, nullable=False),
        sa.Column("hostname", sa.String(64), nullable=False),
        sa.Column("main_ip", sa.String(45)),
        sa.Column("region_id", sa.String(64), nullable=False),
        sa.Column("region_name", sa.String(128), nullable=False),
        sa.Column("plan_id", sa.String(64), nullable=False),
        sa.Column("plan_label", sa.String(255), nullable=False),
        sa.Column("image_name", sa.String(128), nullable=False),
        sa.Column("vcpus", sa.Integer(), nullable=False),
        sa.Column("ram_mb", sa.Integer(), nullable=False),
        sa.Column("disk_gb", sa.Integer(), nullable=False),
        sa.Column("encrypted_password", sa.Text()),
        sa.Column("ssh_public_key", sa.Text()),
        sa.Column("monthly_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("provider_monthly_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("autorenew", sa.Boolean(), nullable=False),
        sa.Column("notified_7d", sa.Boolean(), nullable=False),
        sa.Column("notified_1d", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_servers_user_id", "servers", ["user_id"])
    op.create_index("ix_servers_external_server_id", "servers", ["external_server_id"])
    op.create_index("ix_servers_status", "servers", ["status"])
    op.create_index("ix_servers_expires_at", "servers", ["expires_at"])

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("type", transaction_type_enum, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("balance_after", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("external_payment_id", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    op.create_index("ix_transactions_type", "transactions", ["type"])

    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("status", ticket_status_enum, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_support_tickets_user_id", "support_tickets", ["user_id"])
    op.create_index("ix_support_tickets_status", "support_tickets", ["status"])


def downgrade() -> None:
    op.drop_table("support_tickets")
    op.drop_table("transactions")
    op.drop_table("servers")
    op.drop_table("orders")
    op.drop_table("users")
    for enum in (
        ticket_status_enum, transaction_type_enum,
        server_status_enum, order_status_enum, provider_enum,
    ):
        enum.drop(op.get_bind(), checkfirst=True)
