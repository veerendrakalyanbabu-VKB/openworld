"""Add billing_accounts, usage_counters, and usage_dedup."""

import sqlalchemy as sa

from alembic import op

revision = "003_billing"
down_revision = "002_policy_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_accounts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("plan_id", sa.String(32), nullable=False, server_default="free"),
        sa.Column("entitlements", sa.JSON(), nullable=False),
        sa.Column("subscription_status", sa.String(32), nullable=False, server_default="none"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "usage_counters",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("metric", sa.String(64), nullable=False),
        sa.Column("period_key", sa.String(16), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("account_id", "metric", "period_key", name="uq_usage_period"),
    )
    op.create_index("ix_usage_counters_account_id", "usage_counters", ["account_id"])
    op.create_table(
        "usage_dedup",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("metric", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("account_id", "source_id", name="uq_usage_source"),
    )


def downgrade() -> None:
    op.drop_table("usage_dedup")
    op.drop_index("ix_usage_counters_account_id", table_name="usage_counters")
    op.drop_table("usage_counters")
    op.drop_table("billing_accounts")
