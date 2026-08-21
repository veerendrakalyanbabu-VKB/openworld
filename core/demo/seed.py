"""Demo data seed for OpenWorld MVP."""

from datetime import timedelta

from core.models.agent import Agent, AgentStatus, TrustDimensions
from core.models.policy import (
    ConditionOperator,
    Policy,
    PolicyCondition,
    PolicyEffect,
    PolicyRule,
)
from core.utils.time import utc_now

DEMO_AGENTS = [
    Agent(
        id="agent-finance-bot",
        name="FinanceBot",
        description="Handles financial operations, payments, and invoicing",
        owner="finance-team",
        status=AgentStatus.ACTIVE,
        capabilities=["payment.create", "payment.send", "invoice.create", "invoice.read"],
        trust_dimensions=TrustDimensions(
            identity=100, policy=99, reliability=97, verification=98, violations=100
        ),
        created_at=utc_now() - timedelta(days=90),
    ),
    Agent(
        id="agent-invoice-bot",
        name="InvoiceBot",
        description="Creates and sends invoices to clients",
        owner="billing-team",
        status=AgentStatus.ACTIVE,
        capabilities=["invoice.create", "invoice.send", "invoice.read", "email.send"],
        trust_dimensions=TrustDimensions(
            identity=100, policy=98, reliability=96, verification=99, violations=100
        ),
        created_at=utc_now() - timedelta(days=60),
    ),
    Agent(
        id="agent-email-bot",
        name="EmailBot",
        description="Sends transactional and notification emails",
        owner="comms-team",
        status=AgentStatus.ACTIVE,
        capabilities=["email.send"],
        trust_dimensions=TrustDimensions(
            identity=100, policy=100, reliability=99, verification=100, violations=100
        ),
        created_at=utc_now() - timedelta(days=45),
    ),
    Agent(
        id="agent-api-bot",
        name="ApiBot",
        description="Reads and writes data via external APIs",
        owner="engineering",
        status=AgentStatus.ACTIVE,
        capabilities=["api.read", "api.write", "webhook.send"],
        trust_dimensions=TrustDimensions(
            identity=98, policy=95, reliability=92, verification=94, violations=97
        ),
        metadata={"roles": ["agent", "policy_admin"]},
        created_at=utc_now() - timedelta(days=30),
    ),
    Agent(
        id="agent-ops-bot",
        name="OpsBot",
        description="Human operator proxy for approval decisions (demo)",
        owner="operations",
        status=AgentStatus.ACTIVE,
        capabilities=["approval.review"],
        trust_dimensions=TrustDimensions(
            identity=100, policy=100, reliability=100, verification=100, violations=100
        ),
        metadata={"roles": ["agent", "operator"]},
        created_at=utc_now() - timedelta(days=20),
    ),
    Agent(
        id="agent-admin-bot",
        name="AdminBot",
        description="System administrator for governance operations (demo)",
        owner="platform",
        status=AgentStatus.ACTIVE,
        capabilities=["governance.admin"],
        trust_dimensions=TrustDimensions(
            identity=100, policy=100, reliability=100, verification=100, violations=100
        ),
        metadata={"roles": ["agent", "system_admin"]},
        created_at=utc_now() - timedelta(days=15),
    ),
    Agent(
        id="agent-data-bot",
        name="DataBot",
        description="Database read/write operations for analytics",
        owner="data-team",
        status=AgentStatus.SUSPENDED,
        capabilities=["database.read", "database.write"],
        trust_dimensions=TrustDimensions(
            identity=100, policy=85, reliability=78, verification=80, violations=70
        ),
        created_at=utc_now() - timedelta(days=120),
    ),
]

DEMO_POLICIES = [
    Policy(
        id="policy-finance-payment",
        name="finance-payment-v2",
        description="Requires human approval for large payments",
        version="2.0",
        rules=[
            PolicyRule(
                id="rule-large-payment",
                name="Large Payment Approval",
                agent_match="FinanceBot",
                action_match="payment.*",
                conditions=[
                    PolicyCondition(field="parameters.amount", operator=ConditionOperator.GT, value=50000),
                ],
                effect=PolicyEffect.REQUIRE_APPROVAL,
                priority=10,
                description="Payments over ₹50,000 require human approval",
            ),
            PolicyRule(
                id="rule-block-huge-payment",
                name="Block Critical Payments",
                agent_match="*",
                action_match="payment.*",
                conditions=[
                    PolicyCondition(field="parameters.amount", operator=ConditionOperator.GT, value=500000),
                ],
                effect=PolicyEffect.DENY,
                priority=5,
                description="Payments over ₹500,000 are blocked",
            ),
        ],
    ),
    Policy(
        id="policy-email-limits",
        name="email-rate-limit",
        description="Controls email sending permissions",
        version="1.0",
        rules=[
            PolicyRule(
                id="rule-email-allow",
                name="Allow Email",
                agent_match="*",
                action_match="email.send",
                effect=PolicyEffect.ALLOW,
                priority=50,
            ),
        ],
    ),
    Policy(
        id="policy-data-restrict",
        name="data-access-restrict",
        description="Restricts database write access for suspended agents",
        version="1.0",
        rules=[
            PolicyRule(
                id="rule-block-db-write",
                name="Block DB Write for DataBot",
                agent_match="DataBot",
                action_match="database.write",
                effect=PolicyEffect.DENY,
                priority=10,
                description="DataBot database writes are denied while suspended",
            ),
        ],
    ),
    Policy(
        id="policy-invoice-approval",
        name="invoice-approval",
        description="Large invoices require approval",
        version="1.0",
        rules=[
            PolicyRule(
                id="rule-large-invoice",
                name="Large Invoice Approval",
                agent_match="InvoiceBot",
                action_match="invoice.send",
                conditions=[
                    PolicyCondition(field="parameters.amount", operator=ConditionOperator.GT, value=100000),
                ],
                effect=PolicyEffect.REQUIRE_APPROVAL,
                priority=20,
            ),
        ],
    ),
]

DEMO_CAPABILITIES = [
    {"id": "cap-email-send", "name": "email.send", "description": "Send emails", "category": "communication", "sensitivity": "medium"},
    {"id": "cap-payment-create", "name": "payment.create", "description": "Create payments", "category": "financial", "sensitivity": "critical"},
    {"id": "cap-payment-send", "name": "payment.send", "description": "Send payments", "category": "financial", "sensitivity": "critical"},
    {"id": "cap-invoice-create", "name": "invoice.create", "description": "Create invoices", "category": "financial", "sensitivity": "high"},
    {"id": "cap-invoice-read", "name": "invoice.read", "description": "Read invoices", "category": "financial", "sensitivity": "low"},
    {"id": "cap-invoice-send", "name": "invoice.send", "description": "Send invoices", "category": "financial", "sensitivity": "high"},
    {"id": "cap-api-read", "name": "api.read", "description": "Read API data", "category": "integration", "sensitivity": "medium"},
    {"id": "cap-api-write", "name": "api.write", "description": "Write API data", "category": "integration", "sensitivity": "high"},
    {"id": "cap-db-read", "name": "database.read", "description": "Read database", "category": "data", "sensitivity": "medium"},
    {"id": "cap-db-write", "name": "database.write", "description": "Write database", "category": "data", "sensitivity": "critical"},
    {"id": "cap-webhook", "name": "webhook.send", "description": "Send webhooks", "category": "integration", "sensitivity": "medium"},
]
