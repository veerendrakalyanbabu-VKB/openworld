"""Add policy_versions table for policy lifecycle history."""

import sqlalchemy as sa

from alembic import op

revision = "002_policy_versions"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "policy_versions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("policy_id", sa.String(64), nullable=False, index=True),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("rules", sa.JSON(), server_default="[]"),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("change_action", sa.String(32), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("policy_versions")
