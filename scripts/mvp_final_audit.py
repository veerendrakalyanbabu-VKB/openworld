"""Final MVP live audit — evidence collection against running API on :8000.

Usage:
    python scripts/mvp_final_audit.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

BASE = "http://localhost:8000/api/v1"
OPERATOR_AGENT_ID = "agent-ops-bot"
SECRET = "dev-only-not-for-production-use-32b-minimum-key"
ISSUER = "openworld"
AUDIENCE = "openworld-agents"


def req(
    method: str,
    path: str,
    body: dict | None = None,
    *,
    headers: dict | None = None,
) -> tuple[int, dict[str, Any]]:
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    h = {"Content-Type": "application/json", **(headers or {})}
    request = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            payload = json.loads(raw.decode()) if raw else {"detail": str(e)}
        except json.JSONDecodeError:
            payload = {"detail": raw.decode(errors="replace")[:200]}
        return e.code, payload


def demo_token(agent_id: str) -> str:
    _, data = req("GET", "/auth/demo-agents")
    for a in data.get("agents", []):
        if a["agent_id"] == agent_id:
            return a["access_token"]
    raise RuntimeError(f"No demo token for {agent_id}")


def auth_headers(agent_id: str, idem_key: str | None = None) -> dict[str, str]:
    h = {"Authorization": f"Bearer {demo_token(agent_id)}"}
    if idem_key:
        h["Idempotency-Key"] = idem_key
    return h


def operator_headers() -> dict[str, str]:
    return auth_headers(OPERATOR_AGENT_ID)


def make_token(sub: str, *, secret: str = SECRET, exp_delta: timedelta | None = None) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": sub,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + (exp_delta or timedelta(hours=1)),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def stage_names(action: dict) -> list[str]:
    return [s["stage"] for s in action.get("stages", [])]


def print_section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def main() -> int:
    failures = 0
    evidence: dict[str, Any] = {}

    print_section("JWT SECURITY")
    agents = req("GET", "/agents")[1].get("agents", [])
    email = next(a for a in agents if a["name"] == "EmailBot")
    finance = next(a for a in agents if a["name"] == "FinanceBot")

    cases = [
        ("valid JWT accepted", 200, auth_headers(email["id"]), {"action": "email.send", "parameters": {"to": "jwt@test.com"}}),
        ("missing JWT rejected", 401, {}, {"action": "email.send", "parameters": {}}),
        ("invalid signature rejected", 401, {"Authorization": "Bearer bad.token.here"}, {"action": "email.send", "parameters": {}}),
        ("expired JWT rejected", 401, {"Authorization": f"Bearer {make_token(email['id'], exp_delta=timedelta(hours=-1))}"}, {"action": "email.send", "parameters": {}}),
        ("unknown agent rejected", 401, {"Authorization": f"Bearer {make_token('agent-does-not-exist')}"}, {"action": "email.send", "parameters": {}}),
    ]
    for name, expected, headers, body in cases:
        status, _ = req("POST", "/actions", body, headers=headers)
        ok = status == expected
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: HTTP {status} (expected {expected})")
        if not ok:
            failures += 1

    status, data = req(
        "POST",
        "/actions",
        {
            "agent_id": finance["id"],
            "action": "email.send",
            "parameters": {"to": "impersonate@test.com"},
            "auto_approve": True,
        },
        headers=auth_headers(email["id"]),
    )
    impersonation_blocked = status == 200 and data.get("action", {}).get("agent_id") == email["id"]
    print(f"[{'PASS' if impersonation_blocked else 'FAIL'}] Agent A token cannot act as Agent B (agent_id={data.get('action', {}).get('agent_id')})")
    if not impersonation_blocked:
        failures += 1

    print_section("IDEMPOTENCY")
    idem_key = f"audit-idem-{uuid.uuid4()}"
    body = {"action": "email.send", "parameters": {"to": "idem-audit@test.com", "subject": "Idem"}, "auto_approve": True}
    headers = auth_headers(email["id"], idem_key)
    s1, d1 = req("POST", "/actions", body, headers=headers)
    s2, d2 = req("POST", "/actions", body, headers=headers)
    id1 = d1.get("action", {}).get("id")
    id2 = d2.get("action", {}).get("id")
    idem_ok = s1 == 200 and s2 == 200 and id1 and id1 == id2
    print(f"[{'PASS' if idem_ok else 'FAIL'}] Duplicate key same action_id: {id1} == {id2}")
    evidence["idempotency_key"] = idem_key
    evidence["idempotency_action_id"] = id1
    if not idem_ok:
        failures += 1

    s3, _ = req(
        "POST",
        "/actions",
        {"action": "email.send", "parameters": {"to": "conflict@test.com"}, "auto_approve": True},
        headers=auth_headers(email["id"], idem_key),
    )
    print(f"[{'PASS' if s3 == 409 else 'FAIL'}] Conflicting payload with same key: HTTP {s3}")
    if s3 != 409:
        failures += 1

    print_section("TRUST CORE — ALLOW / DENY / APPROVAL")
    s_allow, allow = req(
        "POST",
        "/actions",
        {"action": "email.send", "parameters": {"to": "allow-audit@test.com"}, "auto_approve": True},
        headers=auth_headers(email["id"]),
    )
    allow_action = allow.get("action", {})
    allow_stages = stage_names(allow_action)
    allow_ok = (
        s_allow == 200
        and allow_action.get("status") == "verified"
        and "execution" in allow_stages
        and "verification" in allow_stages
    )
    print(f"[{'PASS' if allow_ok else 'FAIL'}] ALLOW verified+execution: id={allow_action.get('id')} stages={allow_stages}")
    evidence["allow_action_id"] = allow_action.get("id")
    evidence["allow_correlation_id"] = allow_action.get("correlation_id")
    if not allow_ok:
        failures += 1

    s_deny, deny = req(
        "POST",
        "/actions",
        {"action": "payment.create", "parameters": {"amount": 600000}},
        headers=auth_headers(finance["id"]),
    )
    deny_action = deny.get("action", {})
    deny_stages = stage_names(deny_action)
    deny_ok = s_deny == 200 and deny_action.get("status") == "blocked" and "execution" not in deny_stages
    print(f"[{'PASS' if deny_ok else 'FAIL'}] DENY blocked, no execution: id={deny_action.get('id')} stages={deny_stages}")
    evidence["deny_action_id"] = deny_action.get("id")
    if not deny_ok:
        failures += 1

    s_pending, pending = req(
        "POST",
        "/actions",
        {"action": "payment.create", "parameters": {"amount": 75000, "recipient": "Audit Vendor"}},
        headers=auth_headers(finance["id"]),
    )
    pending_action = pending.get("action", {})
    pending_id = pending_action.get("id")
    pending_ok = s_pending == 200 and pending_action.get("status") == "pending_approval" and "execution" not in stage_names(pending_action)
    print(f"[{'PASS' if pending_ok else 'FAIL'}] REQUIRE_APPROVAL pending, no execution: id={pending_id}")
    if not pending_ok:
        failures += 1

    s_approve, approved = req(
        "POST",
        f"/approvals/{pending_id}/approve",
        {},
        headers=operator_headers(),
    )
    approved_action = approved.get("action", {})
    approve_ok = s_approve == 200 and approved_action.get("status") == "verified" and "execution" in stage_names(approved_action)
    print(f"[{'PASS' if approve_ok else 'FAIL'}] APPROVE verified+execution: id={pending_id}")
    if not approve_ok:
        failures += 1

    s_rej_pending, rej_pending = req(
        "POST",
        "/actions",
        {"action": "payment.create", "parameters": {"amount": 75000, "recipient": "Reject Audit"}},
        headers=auth_headers(finance["id"]),
    )
    reject_id = rej_pending.get("action", {}).get("id")
    s_reject, rejected = req(
        "POST",
        f"/approvals/{reject_id}/deny",
        {"reason": "audit reject"},
        headers=operator_headers(),
    )
    rejected_action = rejected.get("action", {})
    reject_ok = s_reject == 200 and rejected_action.get("status") == "denied" and "execution" not in stage_names(rejected_action)
    print(f"[{'PASS' if reject_ok else 'FAIL'}] REJECT denied, no execution: id={reject_id}")
    if not reject_ok:
        failures += 1

    print_section("AUDIT INTEGRITY")
    corr = evidence.get("allow_correlation_id")
    if corr:
        _, audit = req("GET", f"/audit?correlation_id={corr}&limit=50", headers=operator_headers())
        events = audit.get("events", [])
        types = [e["event_type"] for e in events]
        print(f"ALLOW correlation_id={corr} audit events ({len(events)}): {types}")
        evidence["allow_audit_types"] = types
        has_exec = "action_executed" in types
        print(f"[{'PASS' if has_exec else 'FAIL'}] ALLOW audit includes execution evidence")
        if not has_exec:
            failures += 1

    # Audit mutation attempt — no POST route should exist
    s_audit_post, _ = req("POST", "/audit", {"event_type": "fake"})
    print(f"[{'PASS' if s_audit_post in (404, 405, 422) else 'FAIL'}] Frontend cannot POST audit events: HTTP {s_audit_post}")
    if s_audit_post not in (404, 405, 422):
        failures += 1

    print_section("DEFAULT-DENY (demo_mode=true -> allow-unmatched documented)")
    _, stats = req("GET", "/stats")
    demo_mode = stats.get("demo_mode", True)
    print(f"demo_mode={demo_mode} (demo allows unmatched policies; production OPENWORLD_DEMO_MODE=false enforces deny)")

    print_section("SUMMARY")
    print(json.dumps(evidence, indent=2))
    print(f"\nAudit failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
