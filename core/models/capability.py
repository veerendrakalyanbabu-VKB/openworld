"""Capability domain model and canonical action catalog."""

from pydantic import BaseModel, Field

# Developer-facing aliases → registered executor/capability ids.
ACTION_ALIASES: dict[str, str] = {
    "send_email": "email.send",
    "create_ticket": "github.issue.create",
    "write_record": "api.write",
    "update_record": "api.write",
    "read_document": "api.read",
}

CAPABILITY_CATALOG: list[dict[str, str]] = [
    {
        "id": "email.send",
        "name": "Send email",
        "description": "Deliver a sandbox email message",
        "category": "communication",
        "sensitivity": "low",
    },
    {
        "id": "invoice.create",
        "name": "Create invoice",
        "description": "Create an invoice record",
        "category": "billing",
        "sensitivity": "medium",
    },
    {
        "id": "invoice.send",
        "name": "Send invoice",
        "description": "Send an invoice to a recipient",
        "category": "billing",
        "sensitivity": "medium",
    },
    {
        "id": "invoice.read",
        "name": "Read invoice",
        "description": "Read invoice records",
        "category": "billing",
        "sensitivity": "low",
    },
    {
        "id": "payment.create",
        "name": "Create payment",
        "description": "Create a sandbox payment (simulated)",
        "category": "finance",
        "sensitivity": "high",
    },
    {
        "id": "payment.send",
        "name": "Send payment",
        "description": "Send a sandbox payment (simulated)",
        "category": "finance",
        "sensitivity": "critical",
    },
    {
        "id": "api.read",
        "name": "Read record",
        "description": "Read via registered API executor",
        "category": "data",
        "sensitivity": "low",
    },
    {
        "id": "api.write",
        "name": "Write record",
        "description": "Write via registered API executor",
        "category": "data",
        "sensitivity": "medium",
    },
    {
        "id": "webhook.send",
        "name": "Send webhook",
        "description": "Deliver a sandbox webhook",
        "category": "integration",
        "sensitivity": "medium",
    },
    {
        "id": "github.issue.create",
        "name": "Create ticket",
        "description": "Create a GitHub issue or sandbox ticket",
        "category": "tickets",
        "sensitivity": "medium",
    },
    {
        "id": "approval.review",
        "name": "Review approvals",
        "description": "Human operator approval capability",
        "category": "governance",
        "sensitivity": "high",
    },
    {
        "id": "database.read",
        "name": "Read database",
        "description": "Declared capability only. Unrestricted SQL execution is not provided.",
        "category": "data",
        "sensitivity": "medium",
    },
    {
        "id": "database.write",
        "name": "Write database",
        "description": "Declared capability only. Unrestricted SQL execution is not provided.",
        "category": "data",
        "sensitivity": "high",
    },
]

KNOWN_CAPABILITY_IDS = {item["id"] for item in CAPABILITY_CATALOG}
UNRESTRICTED_WILDCARDS = {"*", "*.*", "all", "any"}


class Capability(BaseModel):
    """A discrete capability an agent can possess."""

    id: str
    name: str
    description: str = ""
    category: str = "general"
    sensitivity: str = "low"  # low, medium, high, critical
    metadata: dict = Field(default_factory=dict)


def canonicalize_action(action: str) -> str:
    """Map public aliases to registered capability/action ids."""
    if not action:
        return action
    key = action.strip()
    return ACTION_ALIASES.get(key, ACTION_ALIASES.get(key.lower(), key))


def is_unrestricted_wildcard(capability: str) -> bool:
    normalized = capability.strip().lower()
    return normalized in UNRESTRICTED_WILDCARDS or normalized.endswith(".**")


def catalog_capabilities() -> list[Capability]:
    return [Capability(**item) for item in CAPABILITY_CATALOG]
