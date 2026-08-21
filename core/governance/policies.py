"""Policy lifecycle business logic."""

import re
import uuid

from fastapi import HTTPException, status

from core.models.audit import AuditEventType
from core.models.policy import Policy, PolicyRule
from core.utils.time import utc_now


def bump_policy_version(current: str) -> str:
    match = re.match(r"^(\d+)\.(\d+)$", current.strip())
    if match:
        major, minor = match.groups()
        return f"{major}.{int(minor) + 1}"
    return f"{current}.1"


def snapshot_policy(
    policy: Policy,
    *,
    change_action: str,
    created_by: str,
) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "policy_id": policy.id,
        "version": policy.version,
        "name": policy.name,
        "description": policy.description,
        "rules": [r.model_dump() for r in policy.rules],
        "enabled": policy.enabled,
        "change_action": change_action,
        "created_by": created_by,
        "created_at": utc_now(),
    }


def validate_policy_rules(rules: list[PolicyRule]) -> None:
    for rule in rules:
        if rule.effect.value == "allow" and any(
            c.field.startswith("metadata.roles") or c.field.startswith("metadata.")
            for c in rule.conditions
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Policy rules cannot mutate authorization metadata",
            )


def apply_policy_update(
    policy: Policy,
    *,
    name: str | None,
    description: str | None,
    rules: list[PolicyRule] | None,
    actor_id: str,
    audit_logger,
    correlation_id: str = "",
) -> tuple[Policy, dict]:
    if rules is not None:
        validate_policy_rules(rules)

    old_version = policy.version
    snapshot = snapshot_policy(policy, change_action="updated", created_by=actor_id)

    if name is not None:
        policy.name = name
    if description is not None:
        policy.description = description
    if rules is not None:
        policy.rules = rules
    policy.version = bump_policy_version(old_version)
    policy.updated_at = utc_now()

    audit_logger.log(
        AuditEventType.POLICY_UPDATED,
        actor=actor_id,
        subject=policy.id,
        action="update",
        policy_id=policy.id,
        details={
            "old_version": old_version,
            "new_version": policy.version,
            "snapshot_id": snapshot["id"],
        },
        correlation_id=correlation_id,
    )
    return policy, snapshot


def apply_policy_enablement(
    policy: Policy,
    *,
    enabled: bool,
    actor_id: str,
    audit_logger,
    correlation_id: str = "",
) -> tuple[Policy, dict]:
    if policy.enabled == enabled:
        return policy, snapshot_policy(
            policy,
            change_action="enabled" if enabled else "disabled",
            created_by=actor_id,
        )

    old_version = policy.version
    snapshot = snapshot_policy(
        policy,
        change_action="enabled" if enabled else "disabled",
        created_by=actor_id,
    )
    policy.enabled = enabled
    policy.version = bump_policy_version(old_version)
    policy.updated_at = utc_now()

    event_type = AuditEventType.POLICY_ENABLED if enabled else AuditEventType.POLICY_DISABLED
    audit_logger.log(
        event_type,
        actor=actor_id,
        subject=policy.id,
        action="enable" if enabled else "disable",
        policy_id=policy.id,
        details={
            "old_version": old_version,
            "new_version": policy.version,
            "enabled": enabled,
            "snapshot_id": snapshot["id"],
        },
        correlation_id=correlation_id,
    )
    return policy, snapshot
