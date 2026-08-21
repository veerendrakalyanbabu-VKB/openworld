"""Initial OpenWorld schema."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("owner", sa.String(255), server_default="system"),
        sa.Column("status", sa.String(32), server_default="active"),
        sa.Column("capabilities", sa.JSON(), server_default="[]"),
        sa.Column("trust_dimensions", sa.JSON(), server_default="{}"),
        sa.Column("metadata", sa.JSON(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_table(
        "policies",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("version", sa.String(32), server_default="1.0"),
        sa.Column("rules", sa.JSON(), server_default="[]"),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_table(
        "actions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("agent_id", sa.String(64), nullable=False, index=True),
        sa.Column("agent_name", sa.String(255), server_default=""),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("target", sa.String(512), server_default=""),
        sa.Column("parameters", sa.JSON(), server_default="{}"),
        sa.Column("context", sa.JSON(), server_default="{}"),
        sa.Column("requested_permissions", sa.JSON(), server_default="[]"),
        sa.Column("status", sa.String(32), server_default="requested", index=True),
        sa.Column("policy_decision", sa.JSON(), nullable=True),
        sa.Column("stages", sa.JSON(), server_default="[]"),
        sa.Column("correlation_id", sa.String(64), server_default="", index=True),
        sa.Column("execution_result", sa.JSON(), nullable=True),
        sa.Column("verification_id", sa.String(64), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("risk_level", sa.String(32), nullable=True),
        sa.Column("approval_status", sa.String(32), nullable=True),
        sa.Column("approval_actor", sa.String(255), nullable=True),
        sa.Column("approval_reason", sa.Text(), nullable=True),
        sa.Column("approval_decided_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False, index=True),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(64), nullable=False, index=True),
        sa.Column("action", sa.String(255), server_default=""),
        sa.Column("decision", sa.String(64), server_default=""),
        sa.Column("policy_id", sa.String(64), nullable=True),
        sa.Column("risk_level", sa.String(32), nullable=True),
        sa.Column("details", sa.JSON(), server_default="{}"),
        sa.Column("correlation_id", sa.String(64), server_default="", index=True),
        sa.Column("evidence", sa.JSON(), server_default="[]"),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
    )
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("agent_id", sa.String(64), nullable=False, index=True),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("action_id", sa.String(64), nullable=True),
        sa.Column("response_json", sa.JSON(), server_default="{}"),
        sa.Column("status_code", sa.Integer(), server_default="200"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("agent_id", "idempotency_key", name="uq_agent_idempotency_key"),
    )


def downgrade() -> None:
    op.drop_table("idempotency_records")
    op.drop_table("audit_events")
    op.drop_table("actions")
    op.drop_table("policies")
    op.drop_table("agents")
