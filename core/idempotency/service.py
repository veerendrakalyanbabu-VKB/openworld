"""Durable idempotency for action requests."""

import hashlib
import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from core.db.models import IdempotencyRow
from core.db.repositories import IdempotencyRepository


class IdempotencyConflictError(Exception):
    """Same key with different request payload."""

    def __init__(self, message: str = "Idempotency key reused with different request"):
        self.message = message
        super().__init__(message)


def hash_request(agent_id: str, action: str, parameters: dict, target: str = "") -> str:
    payload = json.dumps(
        {"agent_id": agent_id, "action": action, "parameters": parameters, "target": target},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


class IdempotencyService:
    def __init__(self, session: Session):
        self.repo = IdempotencyRepository(session)

    def check(self, agent_id: str, idempotency_key: str, request_hash: str) -> dict | None:
        """Return cached response if key exists with same hash, else None."""
        record = self.repo.get(agent_id, idempotency_key)
        if not record:
            return None
        if record.request_hash != request_hash:
            raise IdempotencyConflictError()
        return record.response_json

    def store(
        self,
        agent_id: str,
        idempotency_key: str,
        request_hash: str,
        action_id: str,
        response: dict[str, Any],
        status_code: int = 200,
    ) -> None:
        record = IdempotencyRow(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            action_id=action_id,
            response_json=response,
            status_code=status_code,
        )
        self.repo.save(record)
