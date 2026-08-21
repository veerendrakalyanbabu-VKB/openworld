"""Live PostgreSQL persistence proof — Milestone 1.3 gate.

Requires:
  - PostgreSQL running on localhost:5432
  - database/user openworld configured
  - OPENWORLD_DATABASE_URL in environment or .env

Usage:
    python scripts/postgres_restart_proof.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DB_URL = "postgresql://openworld:openworld_dev_local_only@localhost:5432/openworld"
BASE = "http://localhost:8000/api/v1"
OPERATOR_AGENT_ID = "agent-ops-bot"


def api_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("OPENWORLD_DATABASE_URL", DEFAULT_DB_URL)
    env.setdefault("OPENWORLD_SECRET_KEY", "dev-only-not-for-production-use-32b-minimum-key")
    env.setdefault("OPENWORLD_DEMO_MODE", "true")
    return env


def req(method: str, path: str, body=None, headers=None) -> dict:
    data = json.dumps(body).encode() if body else None
    h = {"Content-Type": "application/json", **(headers or {})}
    r = urllib.request.Request(f"{BASE}{path}", data=data, method=method, headers=h)
    with urllib.request.urlopen(r, timeout=30) as resp:
        return json.loads(resp.read().decode())


def req_status(method: str, path: str, body=None, headers=None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body else None
    h = {"Content-Type": "application/json", **(headers or {})}
    r = urllib.request.Request(f"{BASE}{path}", data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            payload = json.loads(raw.decode()) if raw else {"detail": str(e)}
        except json.JSONDecodeError:
            payload = {"detail": raw.decode(errors="replace")[:200]}
        return e.code, payload


def wait_health(timeout: int = 60) -> bool:
    for _ in range(timeout):
        try:
            h = req("GET", "/health")
            if h.get("status") == "healthy":
                return True
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(1)
    return False


def stop_port(port: int) -> None:
    subprocess.run(
        [
            "powershell",
            "-Command",
            f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
            "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }",
        ],
        check=False,
    )
    time.sleep(2)


def start_api() -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "apps.api.main:app", "--port", "8000"],
        cwd=str(ROOT),
        env=api_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def auth_headers(agent_id: str, idem_key: str | None = None) -> dict[str, str]:
    agents = req("GET", "/auth/demo-agents")["agents"]
    token = next(a["access_token"] for a in agents if a["agent_id"] == agent_id)
    h = {"Authorization": f"Bearer {token}"}
    if idem_key:
        h["Idempotency-Key"] = idem_key
    return h


def operator_headers() -> dict[str, str]:
    return auth_headers(OPERATOR_AGENT_ID)


def stage_names(action: dict) -> list[str]:
    return [s["stage"] for s in action.get("stages", [])]


def verify_postgres_connection() -> str:
    import psycopg2

    url = api_env()["OPENWORLD_DATABASE_URL"]
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SELECT version()")
    version = cur.fetchone()[0]
    cur.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    )
    tables = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    required = {"agents", "policies", "actions", "audit_events", "idempotency_records"}
    missing = required - set(tables)
    if missing:
        raise RuntimeError(f"Missing tables after migration: {missing}")
    return version


def populate_and_record() -> dict:
    email = next(a for a in req("GET", "/agents")["agents"] if a["name"] == "EmailBot")
    finance = next(a for a in req("GET", "/agents")["agents"] if a["name"] == "FinanceBot")

    allow = req(
        "POST",
        "/actions",
        {"action": "email.send", "parameters": {"to": "pg-restart@test.com"}, "auto_approve": True},
        auth_headers(email["id"]),
    )["action"]

    deny = req(
        "POST",
        "/actions",
        {"action": "payment.create", "parameters": {"amount": 600000}},
        auth_headers(finance["id"]),
    )["action"]

    pending = req(
        "POST",
        "/actions",
        {"action": "payment.create", "parameters": {"amount": 75000, "recipient": "PG Vendor"}},
        auth_headers(finance["id"]),
    )["action"]
    approved = req("POST", f"/approvals/{pending['id']}/approve", {}, operator_headers())["action"]

    idem_key = f"pg-idem-{uuid.uuid4()}"
    idem_body = {
        "action": "email.send",
        "parameters": {"to": "pg-idem@test.com", "subject": "PG Idem"},
        "auto_approve": True,
    }
    idem_action = req("POST", "/actions", idem_body, auth_headers(email["id"], idem_key))["action"]

    agents = req("GET", "/agents")["agents"]
    policies = req("GET", "/policies")["policies"]
    audit_total = req("GET", "/audit?limit=1", headers=operator_headers())["total"]

    return {
        "allow_id": allow["id"],
        "deny_id": deny["id"],
        "approved_id": approved["id"],
        "idem_key": idem_key,
        "idem_action_id": idem_action["id"],
        "idem_body": idem_body,
        "email_agent_id": email["id"],
        "finance_agent_id": finance["id"],
        "agent_count": len(agents),
        "sample_agent_id": agents[0]["id"],
        "policy_count": len(policies),
        "sample_policy_id": policies[0]["id"],
        "audit_total": audit_total,
        "allow_correlation": allow.get("correlation_id"),
    }


def verify_after_restart(before: dict) -> tuple[bool, list[str]]:
    lines: list[str] = []
    ok = True

    actions = req("GET", "/actions?limit=200")["actions"]
    by_id = {a["id"]: a for a in actions}

    checks = [
        ("ALLOW", before["allow_id"], "verified"),
        ("DENY", before["deny_id"], "blocked"),
        ("APPROVED", before["approved_id"], "verified"),
    ]
    for label, aid, expected in checks:
        found = by_id.get(aid)
        status = found.get("status") if found else None
        passed = status == expected
        lines.append(f"[{'PASS' if passed else 'FAIL'}] {label}: {aid} status={status} (expected {expected})")
        ok = ok and passed

    idem2 = req(
        "POST",
        "/actions",
        before["idem_body"],
        auth_headers(before["email_agent_id"], before["idem_key"]),
    )["action"]
    idem_ok = idem2["id"] == before["idem_action_id"]
    lines.append(
        f"[{'PASS' if idem_ok else 'FAIL'}] IDEMPOTENCY after restart: "
        f"{before['idem_key']} -> {idem2['id']} (was {before['idem_action_id']})"
    )
    ok = ok and idem_ok

    s409, _ = req_status(
        "POST",
        "/actions",
        {"action": "email.send", "parameters": {"to": "conflict@test.com"}, "auto_approve": True},
        auth_headers(before["email_agent_id"], before["idem_key"]),
    )
    conflict_ok = s409 == 409
    lines.append(f"[{'PASS' if conflict_ok else 'FAIL'}] Idempotency conflict HTTP {s409} (expected 409)")
    ok = ok and conflict_ok

    agents_after = req("GET", "/agents")["agents"]
    policies_after = req("GET", "/policies")["policies"]
    audit_after = req("GET", "/audit?limit=1", headers=operator_headers())["total"]

    agent_ok = len(agents_after) >= before["agent_count"] and any(
        a["id"] == before["sample_agent_id"] for a in agents_after
    )
    policy_ok = len(policies_after) >= before["policy_count"] and any(
        p["id"] == before["sample_policy_id"] for p in policies_after
    )
    audit_ok = audit_after >= before["audit_total"]

    lines.append(f"[{'PASS' if agent_ok else 'FAIL'}] AGENTS: {len(agents_after)} (sample {before['sample_agent_id']})")
    lines.append(f"[{'PASS' if policy_ok else 'FAIL'}] POLICIES: {len(policies_after)} (sample {before['sample_policy_id']})")
    lines.append(f"[{'PASS' if audit_ok else 'FAIL'}] AUDIT: {audit_after} (was {before['audit_total']})")
    ok = ok and agent_ok and policy_ok and audit_ok

    return ok, lines


def run_trust_scenarios(before: dict) -> tuple[bool, list[str]]:
    lines: list[str] = []
    ok = True
    email_id = before["email_agent_id"]
    finance_id = before["finance_agent_id"]

    allow = req(
        "POST",
        "/actions",
        {"action": "email.send", "parameters": {"to": "pg-trust-allow@test.com"}, "auto_approve": True},
        auth_headers(email_id),
    )["action"]
    allow_ok = allow["status"] == "verified" and "execution" in stage_names(allow)
    lines.append(f"[{'PASS' if allow_ok else 'FAIL'}] ALLOW trust flow: {allow['id']}")
    ok = ok and allow_ok

    deny = req(
        "POST",
        "/actions",
        {"action": "payment.create", "parameters": {"amount": 600000}},
        auth_headers(finance_id),
    )["action"]
    deny_ok = deny["status"] == "blocked" and "execution" not in stage_names(deny)
    lines.append(f"[{'PASS' if deny_ok else 'FAIL'}] DENY trust flow: {deny['id']}")
    ok = ok and deny_ok

    pending = req(
        "POST",
        "/actions",
        {"action": "payment.create", "parameters": {"amount": 75000}},
        auth_headers(finance_id),
    )["action"]
    pending_ok = pending["status"] == "pending_approval" and "execution" not in stage_names(pending)
    lines.append(f"[{'PASS' if pending_ok else 'FAIL'}] REQUIRE_APPROVAL pending: {pending['id']}")
    ok = ok and pending_ok

    approved = req("POST", f"/approvals/{pending['id']}/approve", {}, operator_headers())["action"]
    approve_ok = approved["status"] == "verified" and "execution" in stage_names(approved)
    lines.append(f"[{'PASS' if approve_ok else 'FAIL'}] APPROVE flow: {pending['id']}")
    ok = ok and approve_ok

    rej_pending = req(
        "POST",
        "/actions",
        {"action": "payment.create", "parameters": {"amount": 75000, "recipient": "Reject"}},
        auth_headers(finance_id),
    )["action"]
    rejected = req(
        "POST",
        f"/approvals/{rej_pending['id']}/deny",
        {"reason": "PG reject test"},
        operator_headers(),
    )["action"]
    reject_ok = rejected["status"] == "denied" and "execution" not in stage_names(rejected)
    lines.append(f"[{'PASS' if reject_ok else 'FAIL'}] REJECT flow: {rej_pending['id']}")
    ok = ok and reject_ok

    return ok, lines


def main() -> int:
    print("=== PostgreSQL Live Persistence Proof ===\n")
    proc: subprocess.Popen | None = None
    failures = 0

    try:
        print("--- Phase 1: PostgreSQL connectivity ---")
        try:
            version = verify_postgres_connection()
            print(f"PostgreSQL connected: {version[:80]}...")
            print("Tables: agents, policies, actions, audit_events, idempotency_records (pre-migration check)")
        except Exception as e:
            print(f"Pre-check note: {e} (migrations run on API startup)")

        stop_port(8000)
        print("\n--- Phase 2: Start API against PostgreSQL ---")
        proc = start_api()
        if not wait_health():
            print("FAIL: API did not become healthy")
            return 1

        version = verify_postgres_connection()
        print(f"PostgreSQL version: {version}")
        print("Schema tables verified via pg_tables")

        print("\n--- Phase 3: BEFORE RESTART ---")
        before = populate_and_record()
        print(json.dumps(before, indent=2))

        print("\n--- Phase 4: STOP API ---")
        proc.terminate()
        proc.wait(timeout=15)
        proc = None
        stop_port(8000)
        time.sleep(2)

        print("\n--- Phase 5: START API (same PostgreSQL) ---")
        proc = start_api()
        if not wait_health():
            print("FAIL: API did not restart healthy")
            return 1

        print("\n--- Phase 6: AFTER RESTART ---")
        ok, lines = verify_after_restart(before)
        for line in lines:
            print(line)
        if not ok:
            failures += 1

        print("\n--- Phase 7: Trust scenarios on PostgreSQL ---")
        trust_ok, trust_lines = run_trust_scenarios(before)
        for line in trust_lines:
            print(line)
        if not trust_ok:
            failures += 1

        print(f"\n=== RESULT: {'PASS' if failures == 0 else 'FAIL'} ({failures} failure groups) ===")
        return 0 if failures == 0 else 1
    finally:
        if proc and proc.poll() is None:
            proc.terminate()


if __name__ == "__main__":
    sys.exit(main())
