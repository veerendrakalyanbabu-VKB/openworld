"""Immutable audit logging system."""

import uuid

from core.models.audit import AuditEvent, AuditEventType
from core.utils.time import utc_now


class AuditLogger:
    """Creates and stores immutable audit records."""

    def __init__(self):
        self._events: list[AuditEvent] = []

    def log(
        self,
        event_type: AuditEventType,
        actor: str,
        subject: str,
        action: str = "",
        decision: str = "",
        policy_id: str | None = None,
        risk_level: str | None = None,
        details: dict | None = None,
        correlation_id: str = "",
        evidence: list[str] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            actor=actor,
            subject=subject,
            action=action,
            decision=decision,
            policy_id=policy_id,
            risk_level=risk_level,
            details=details or {},
            correlation_id=correlation_id,
            evidence=evidence or [],
            timestamp=utc_now(),
        )
        self._events.append(event)
        return event

    def get_events(
        self,
        limit: int = 100,
        offset: int = 0,
        agent: str | None = None,
        event_type: str | None = None,
        decision: str | None = None,
        risk_level: str | None = None,
        subject: str | None = None,
        correlation_id: str | None = None,
    ) -> list[AuditEvent]:
        events = self._events

        if agent:
            events = [e for e in events if agent.lower() in e.actor.lower() or agent.lower() in e.subject.lower()]
        if event_type:
            events = [e for e in events if e.event_type.value == event_type]
        if decision:
            events = [e for e in events if e.decision == decision]
        if risk_level:
            events = [e for e in events if e.risk_level == risk_level]
        if subject:
            events = [e for e in events if e.subject == subject]
        if correlation_id:
            events = [e for e in events if e.correlation_id == correlation_id]

        events = sorted(events, key=lambda e: e.timestamp, reverse=True)
        return events[offset : offset + limit]

    def count(self) -> int:
        return len(self._events)

    def load_events(self, events: list[AuditEvent]) -> None:
        self._events = events
