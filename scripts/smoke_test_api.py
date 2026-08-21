"""Live API smoke tests — run against a running backend on localhost:8000.

Usage:
    python scripts/smoke_test_api.py
"""

import json
import sys
import urllib.error
import urllib.request
import uuid

BASE = "http://localhost:8000/api/v1"
OPERATOR_AGENT_ID = "agent-ops-bot"


def request(
    method: str,
    path: str,
    body: dict | None = None,
    *,
    headers: dict | None = None,
) -> tuple[int, dict]:
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req_headers = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=data, method=method, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_bytes = e.read()
        try:
            payload = json.loads(body_bytes.decode()) if body_bytes else {"error": str(e)}
        except json.JSONDecodeError:
            payload = {"error": str(e), "body": body_bytes.decode(errors="replace")[:200]}
        return e.code, payload


def get_demo_token(agent_id: str) -> str:
    status, data = request("GET", "/auth/demo-agents")
    if status != 200:
        raise RuntimeError(f"Failed to get demo tokens: {status} {data}")
    for agent in data.get("agents", []):
        if agent["agent_id"] == agent_id:
            return agent["access_token"]
    raise RuntimeError(f"No demo token for agent {agent_id}")


def auth_headers(agent_id: str, idempotency_key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {get_demo_token(agent_id)}"}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def operator_headers() -> dict[str, str]:
    return auth_headers(OPERATOR_AGENT_ID)


def main() -> int:
    print("=== OpenWorld API Smoke Test ===\n")
    failures = 0

    status, data = request("GET", "/health")
    print(f"[{'PASS' if status == 200 else 'FAIL'}] GET /health -> {status} {data.get('status')}")
    if status != 200:
        failures += 1
        print("\nAPI not reachable. Start with: python scripts/start-api.py")
        return 1

    status, auth_data = request("GET", "/auth/demo-agents")
    ok = status == 200 and "DEMO AUTHENTICATION" in auth_data.get("label", "")
    print(f"[{'PASS' if ok else 'FAIL'}] GET /auth/demo-agents -> {status}")
    if not ok:
        failures += 1

    for endpoint in ["/stats", "/agents", "/actions", "/policies", "/verifications"]:
        status, _ = request("GET", endpoint)
        ok = status == 200
        print(f"[{'PASS' if ok else 'FAIL'}] GET {endpoint} -> {status}")
        if not ok:
            failures += 1

    status, _ = request("GET", "/approvals")
    print(f"[{'PASS' if status == 401 else 'FAIL'}] GET /approvals without auth -> {status}")
    if status != 401:
        failures += 1

    status, _ = request("GET", "/approvals", headers=operator_headers())
    print(f"[{'PASS' if status == 200 else 'FAIL'}] GET /approvals with operator -> {status}")
    if status != 200:
        failures += 1

    status, _ = request("GET", "/audit")
    print(f"[{'PASS' if status == 401 else 'FAIL'}] GET /audit without auth -> {status}")
    if status != 401:
        failures += 1

    status, _ = request("GET", "/audit?limit=5", headers=operator_headers())
    print(f"[{'PASS' if status == 200 else 'FAIL'}] GET /audit with operator -> {status}")
    if status != 200:
        failures += 1

    status, _ = request("GET", "/scenarios")
    print(f"[{'PASS' if status == 200 else 'WARN'}] GET /scenarios -> {status}")

    status, _ = request("POST", "/actions", {"action": "email.send", "parameters": {}})
    print(f"[{'PASS' if status == 401 else 'FAIL'}] POST /actions without auth -> {status}")
    if status != 401:
        failures += 1

    _, agents_data = request("GET", "/agents")
    agents = agents_data.get("agents", [])
    email_bot = next((a for a in agents if a["name"] == "EmailBot"), None)
    finance_bot = next((a for a in agents if a["name"] == "FinanceBot"), None)

    if not email_bot or not finance_bot:
        print("[FAIL] Demo agents not found")
        return 1

    print("\n--- ALLOW scenario ---")
    status, allow_data = request(
        "POST",
        "/actions",
        {
            "action": "email.send",
            "parameters": {"to": "smoke@example.com", "subject": "Smoke Test"},
            "auto_approve": True,
        },
        headers=auth_headers(email_bot["id"]),
    )
    allow_action = allow_data.get("action", {})
    ok = status == 200 and allow_action.get("status") == "verified"
    print(f"[{'PASS' if ok else 'FAIL'}] ALLOW -> status={allow_action.get('status')}")
    if not ok:
        failures += 1
    else:
        _, audit = request(
            "GET",
            f"/audit?correlation_id={allow_action.get('correlation_id', '')}",
            headers=operator_headers(),
        )
        exec_events = [e for e in audit.get("events", []) if e["event_type"] == "action_executed"]
        print(f"  audit events: {len(audit.get('events', []))}, executed: {len(exec_events)}")

    print("\n--- DENY scenario ---")
    status, deny_data = request(
        "POST",
        "/actions",
        {"action": "payment.create", "parameters": {"amount": 600000}},
        headers=auth_headers(finance_bot["id"]),
    )
    deny_action = deny_data.get("action", {})
    stages = [s["stage"] for s in deny_action.get("stages", [])]
    ok = status == 200 and deny_action.get("status") == "blocked" and "execution" not in stages
    print(f"[{'PASS' if ok else 'FAIL'}] DENY -> status={deny_action.get('status')}")
    if not ok:
        failures += 1

    print("\n--- REQUIRE_APPROVAL -> APPROVE ---")
    status, pending_data = request(
        "POST",
        "/actions",
        {"action": "payment.create", "parameters": {"amount": 75000, "recipient": "Smoke Vendor"}},
        headers=auth_headers(finance_bot["id"]),
    )
    pending_action = pending_data.get("action", {})
    action_id = pending_action.get("id")
    ok = status == 200 and pending_action.get("status") == "pending_approval"
    print(f"[{'PASS' if ok else 'FAIL'}] REQUIRE_APPROVAL -> status={pending_action.get('status')}")
    if not ok:
        failures += 1
    else:
        status, approve_data = request(
            "POST",
            f"/approvals/{action_id}/approve",
            {},
            headers=operator_headers(),
        )
        approved = approve_data.get("action", {})
        ok = status == 200 and approved.get("status") == "verified"
        print(f"[{'PASS' if ok else 'FAIL'}] APPROVE -> status={approved.get('status')}")
        if not ok:
            failures += 1

    print("\n--- REQUIRE_APPROVAL -> REJECT ---")
    status, pending_data = request(
        "POST",
        "/actions",
        {"action": "payment.create", "parameters": {"amount": 75000, "recipient": "Reject Vendor"}},
        headers=auth_headers(finance_bot["id"]),
    )
    action_id = pending_data.get("action", {}).get("id")
    status, reject_data = request(
        "POST",
        f"/approvals/{action_id}/deny",
        {"reason": "Smoke test rejection"},
        headers=operator_headers(),
    )
    rejected = reject_data.get("action", {})
    stages = [s["stage"] for s in rejected.get("stages", [])]
    ok = status == 200 and rejected.get("status") == "denied" and "execution" not in stages
    print(f"[{'PASS' if ok else 'FAIL'}] REJECT -> status={rejected.get('status')}")
    if not ok:
        failures += 1

    print("\n--- Authorization ---")
    status, auth_pending_data = request(
        "POST",
        "/actions",
        {
            "action": "payment.create",
            "parameters": {"amount": 75000, "recipient": "Auth Check Vendor"},
        },
        headers=auth_headers(finance_bot["id"]),
    )
    auth_pending_id = auth_pending_data.get("action", {}).get("id")
    status, _ = request(
        "POST",
        f"/approvals/{auth_pending_id}/approve",
        {},
        headers=auth_headers(finance_bot["id"]),
    )
    print(f"[{'PASS' if status == 403 else 'FAIL'}] Agent cannot approve -> {status}")
    if status != 403:
        failures += 1

    print("\n--- Idempotency ---")
    idem_key = str(uuid.uuid4())
    body = {
        "action": "email.send",
        "parameters": {"to": "idem@smoke.com", "subject": "Idem"},
        "auto_approve": True,
    }
    status1, data1 = request("POST", "/actions", body, headers=auth_headers(email_bot["id"], idem_key))
    status2, data2 = request("POST", "/actions", body, headers=auth_headers(email_bot["id"], idem_key))
    ok = (
        status1 == 200
        and status2 == 200
        and data1.get("action", {}).get("id") == data2.get("action", {}).get("id")
    )
    print(f"[{'PASS' if ok else 'FAIL'}] Duplicate idempotency key returns same action")
    if not ok:
        failures += 1

    status3, _ = request(
        "POST",
        "/actions",
        {"action": "email.send", "parameters": {"to": "conflict@smoke.com"}, "auto_approve": True},
        headers=auth_headers(email_bot["id"], idem_key),
    )
    ok = status3 == 409
    print(f"[{'PASS' if ok else 'FAIL'}] Conflicting idempotency key -> {status3}")
    if not ok:
        failures += 1

    print("\n--- Audit persistence ---")
    _, audit_data = request("GET", "/audit?limit=5", headers=operator_headers())
    ok = audit_data.get("total", 0) > 0
    print(f"[{'PASS' if ok else 'FAIL'}] Audit events persisted: total={audit_data.get('total', 0)}")
    if not ok:
        failures += 1

    print(f"\n=== Result: {failures} failure(s) ===")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
