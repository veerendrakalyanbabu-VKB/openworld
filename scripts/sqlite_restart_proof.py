"""SQLite file-based API restart persistence proof (when PostgreSQL is unavailable).

Uses OPENWORLD_DATABASE_URL=sqlite:///./openworld_audit.db for durable storage.
For PostgreSQL proof, run with docker compose and scripts/restart_persistence_test.py.

Usage:
    python scripts/sqlite_restart_proof.py
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
DB_FILE = ROOT / "openworld_audit.db"
BASE = "http://localhost:8000/api/v1"
ENV = {
    **os.environ,
    "OPENWORLD_DATABASE_URL": f"sqlite:///{DB_FILE.as_posix()}",
    "OPENWORLD_SECRET_KEY": "dev-only-not-for-production-use-32b-minimum-key",
    "OPENWORLD_DEMO_MODE": "true",
}


def req(method: str, path: str, body=None, headers=None):
    data = json.dumps(body).encode() if body else None
    h = {"Content-Type": "application/json", **(headers or {})}
    r = urllib.request.Request(f"{BASE}{path}", data=data, method=method, headers=h)
    with urllib.request.urlopen(r, timeout=20) as resp:
        return json.loads(resp.read().decode())


def wait_health(timeout=30):
    for _ in range(timeout):
        try:
            req("GET", "/health")
            return True
        except (urllib.error.URLError, TimeoutError):
            time.sleep(1)
    return False


def stop_port_8000():
    subprocess.run(
        [
            "powershell",
            "-Command",
            "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | "
            "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }",
        ],
        check=False,
    )
    time.sleep(2)


def start_api() -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "apps.api.main:app", "--port", "8000"],
        cwd=str(ROOT),
        env=ENV,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def main() -> int:
    print("=== SQLite Restart Persistence Proof ===\n")
    if DB_FILE.exists():
        DB_FILE.unlink()

    stop_port_8000()
    proc = start_api()
    try:
        if not wait_health():
            print("FAIL: API did not start")
            return 1

        agents = req("GET", "/auth/demo-agents")["agents"]
        email = next(a for a in agents if a["agent_name"] == "EmailBot")
        finance = next(a for a in agents if a["agent_name"] == "FinanceBot")
        headers = {
            "Authorization": f"Bearer {email['access_token']}",
            "Idempotency-Key": str(uuid.uuid4()),
        }

        allow = req(
            "POST",
            "/actions",
            {"action": "email.send", "parameters": {"to": "restart@test.com"}, "auto_approve": True},
            headers,
        )["action"]
        allow_id = allow["id"]

        deny = req(
            "POST",
            "/actions",
            {"action": "payment.create", "parameters": {"amount": 600000}},
            {"Authorization": f"Bearer {finance['access_token']}", "Idempotency-Key": str(uuid.uuid4())},
        )["action"]
        deny_id = deny["id"]

        pending = req(
            "POST",
            "/actions",
            {"action": "payment.create", "parameters": {"amount": 75000}},
            {"Authorization": f"Bearer {finance['access_token']}", "Idempotency-Key": str(uuid.uuid4())},
        )["action"]
        pending_id = pending["id"]
        req("POST", f"/approvals/{pending_id}/approve", {"approver": "human"})

        idem_key = f"restart-idem-{uuid.uuid4()}"
        idem_body = {"action": "email.send", "parameters": {"to": "idem-restart@test.com"}, "auto_approve": True}
        idem_headers = {
            "Authorization": f"Bearer {email['access_token']}",
            "Idempotency-Key": idem_key,
        }
        idem_action = req("POST", "/actions", idem_body, idem_headers)["action"]
        idem_id = idem_action["id"]

        agent_ids = [a["id"] for a in req("GET", "/agents")["agents"]]
        policy_ids = [p["id"] for p in req("GET", "/policies")["policies"]]
        audit_before = req("GET", "/audit?limit=1")["total"]

        print("BEFORE restart:")
        print(f"  agents: {len(agent_ids)} (sample: {agent_ids[0]})")
        print(f"  policies: {len(policy_ids)} (sample: {policy_ids[0]})")
        print(f"  allow_action_id: {allow_id}")
        print(f"  deny_action_id: {deny_id}")
        print(f"  approved_action_id: {pending_id}")
        print(f"  idempotency_key: {idem_key}")
        print(f"  idempotency_action_id: {idem_id}")
        print(f"  audit_total: {audit_before}")

        print("\nStopping API...")
        proc.terminate()
        proc.wait(timeout=10)
        stop_port_8000()

        print("Starting API...")
        proc = start_api()
        if not wait_health():
            print("FAIL: API did not restart")
            return 1

        actions = req("GET", "/actions?limit=200")["actions"]
        by_id = {a["id"]: a for a in actions}
        checks = [
            ("allow survives", allow_id, "verified"),
            ("deny survives", deny_id, "blocked"),
            ("approval survives", pending_id, "verified"),
        ]
        ok = True
        for label, aid, expected_status in checks:
            found = by_id.get(aid)
            status = found.get("status") if found else None
            passed = status == expected_status
            print(f"[{'PASS' if passed else 'FAIL'}] {label}: {aid} status={status}")
            ok = ok and passed

        idem2 = req("POST", "/actions", idem_body, idem_headers)["action"]
        idem_durable = idem2["id"] == idem_id
        print(f"[{'PASS' if idem_durable else 'FAIL'}] Idempotency after restart: {idem_id} == {idem2['id']}")
        ok = ok and idem_durable

        agents_after = req("GET", "/agents")["agents"]
        policies_after = req("GET", "/policies")["policies"]
        audit_after = req("GET", "/audit?limit=1")["total"]
        print(f"[{'PASS' if len(agents_after) >= 5 else 'FAIL'}] agents after restart: {len(agents_after)}")
        print(f"[{'PASS' if len(policies_after) >= 4 else 'FAIL'}] policies after restart: {len(policies_after)}")
        print(f"[{'PASS' if audit_after >= audit_before else 'FAIL'}] audit after restart: {audit_after} (was {audit_before})")
        ok = ok and len(agents_after) >= 5 and len(policies_after) >= 4 and audit_after >= audit_before

        print(f"\n=== Result: {'PASS' if ok else 'FAIL'} ===")
        return 0 if ok else 1
    finally:
        if proc.poll() is None:
            proc.terminate()


if __name__ == "__main__":
    sys.exit(main())
