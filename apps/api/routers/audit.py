"""Audit endpoints."""

import csv
import io
import json

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from apps.api.auth.audit_access import audit_scope_agent_id, resolve_audit_subject
from apps.api.auth.dependencies import AuthenticatedActor, get_authenticated_actor
from apps.api.gateway import get_request_id
from apps.api.state import state
from core.db.repositories import AuditRepository
from core.db.session import session_scope
from core.models.audit import AuditEventType

router = APIRouter()

MAX_EXPORT_LIMIT = 1000


def _fetch_audit_events(
    *,
    limit: int,
    offset: int,
    agent: str | None,
    event_type: str | None,
    decision: str | None,
    risk_level: str | None,
    subject: str | None,
    correlation_id: str | None,
):
    if state._db_initialized:
        with session_scope() as session:
            events = AuditRepository(session).get_events(
                limit=limit,
                offset=offset,
                agent=agent,
                event_type=event_type,
                decision=decision,
                risk_level=risk_level,
                subject=subject,
                correlation_id=correlation_id,
            )
            total = AuditRepository(session).count()
        return events, total
    events = state.audit_logger.get_events(
        limit=limit,
        offset=offset,
        agent=agent,
        event_type=event_type,
        decision=decision,
        risk_level=risk_level,
        subject=subject,
        correlation_id=correlation_id,
    )
    return events, state.audit_logger.count()


@router.get("")
async def list_audit_events(
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    agent: str | None = Query(None),
    event_type: str | None = Query(None),
    decision: str | None = Query(None),
    risk_level: str | None = Query(None),
    subject: str | None = Query(None),
    correlation_id: str | None = Query(None),
    actor: AuthenticatedActor = Depends(get_authenticated_actor),
):
    subject = resolve_audit_subject(actor, subject)
    events, total = _fetch_audit_events(
        limit=limit,
        offset=offset,
        agent=agent,
        event_type=event_type,
        decision=decision,
        risk_level=risk_level,
        subject=subject,
        correlation_id=correlation_id,
    )
    return {
        "events": events,
        "total": total,
        "demo_mode": state.demo_mode,
        "label": "DEMO / SYNTHETIC DATA" if state.demo_mode else None,
        "scoped_to": audit_scope_agent_id(actor),
    }


@router.get("/export")
async def export_audit_events(
    request: Request,
    format: str = Query("json", pattern="^(json|csv)$"),
    limit: int = Query(500, le=MAX_EXPORT_LIMIT),
    offset: int = Query(0),
    subject: str | None = Query(None),
    correlation_id: str | None = Query(None),
    actor: AuthenticatedActor = Depends(get_authenticated_actor),
):
    subject = resolve_audit_subject(actor, subject)
    events, total = _fetch_audit_events(
        limit=limit,
        offset=offset,
        agent=None,
        event_type=None,
        decision=None,
        risk_level=None,
        subject=subject,
        correlation_id=correlation_id,
    )

    correlation = get_request_id(request)
    state.audit_logger.log(
        AuditEventType.AUDIT_EXPORTED,
        actor=actor.agent.id,
        subject=actor.agent.id,
        action=f"export:{format}",
        details={"count": len(events), "limit": limit, "offset": offset, "total_available": total},
        correlation_id=correlation,
    )

    if format == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            ["id", "event_type", "actor", "subject", "action", "decision", "timestamp", "correlation_id"]
        )
        for event in events:
            writer.writerow(
                [
                    event.id,
                    event.event_type.value,
                    event.actor,
                    event.subject,
                    event.action,
                    event.decision,
                    event.timestamp.isoformat(),
                    event.correlation_id,
                ]
            )
        return Response(
            content=buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit-export.csv"},
        )

    payload = {
        "events": [e.model_dump(mode="json") for e in events],
        "exported": len(events),
        "total_available": total,
        "limit": limit,
        "offset": offset,
        "demo_mode": state.demo_mode,
    }
    return Response(
        content=json.dumps(payload, default=str),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=audit-export.json"},
    )
