"""PostgreSQL governance persistence proof — Milestone 2.0B gate."""

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
ADMIN_ID = "agent-admin-bot"
POLICY_ID = "policy-email-limits"
TARGET_AGENT = "agent-email-bot"


def req(method: str, path: str, body=None, headers=None) -> dict:
    data = json.dumps(body).encode() if body else None
    h = {"Content-Type": "application/json", **(headers or {})}
    r = urllib.request.Request(f"{BASE}{path}", data=data, method=method, headers=h)
    with urllib.request.urlopen(r, timeout=30) as resp:
        return json.loads(resp.read().decode())


def auth_headers(agent_id: str) -> dict[str, str]:
    agents = req("GET", "/auth/demo-agents")["agents"]
    token = next(a["access_token"] for a in agents if a["agent_id"] == agent_id)
    return {"Authorization": f"Bearer {token}"}


def wait_health(timeout: int = 60) -> bool:
    for _ in range(timeout):
        try:
            if req("GET", "/health").get("status") == "healthy":
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
    env = os.environ.copy()
    env.setdefault("OPENWORLD_DATABASE_URL", DEFAULT_DB_URL)
    env.setdefault("OPENWORLD_SECRET_KEY", "dev-only-not-for-production-use-32b-minimum-key")
    env.setdefault("OPENWORLD_DEMO_MODE", "true")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "apps.api.main:app", "--port", "8000"],
        cwd=ROOT,
        env=env,
    )


def main() -> int:
    print("=== PostgreSQL Governance Persistence Proof ===\n")
    failures = 0
    proc: subprocess.Popen | None = None
    try:
        stop_port(8000)
        proc = start_api()
        if not wait_health():
            print("[FAIL] API did not become healthy")
            return 1

        admin = auth_headers(ADMIN_ID)
        before_roles = req("GET", f"/agents/{TARGET_AGENT}/roles", headers=admin)
        if "operator" in before_roles.get("stored_roles", []):
            req("DELETE", f"/agents/{TARGET_AGENT}/roles/operator", headers=admin)

        assign = req("POST", f"/agents/{TARGET_AGENT}/roles", {"role": "operator"}, admin)
        print(f"[{'PASS' if 'operator' in assign.get('new_roles', []) else 'FAIL'}] Role assign persisted in response")

        policy_before = req("GET", f"/policies/{POLICY_ID}")["policy"]["version"]
        update = req(
            "PUT",
            f"/policies/{POLICY_ID}",
            {"description": f"PG governance proof {uuid.uuid4().hex[:8]}"},
            admin,
        )
        policy_after = update["policy"]["version"]
        version_ok = policy_after != policy_before
        print(f"[{'PASS' if version_ok else 'FAIL'}] Policy version bump: {policy_before} -> {policy_after}")

        stop_port(8000)
        proc.kill()
        proc = None
        time.sleep(2)
        proc = start_api()
        if not wait_health():
            print("[FAIL] API restart failed")
            return 1

        admin = auth_headers(ADMIN_ID)
        roles_after = req("GET", f"/agents/{TARGET_AGENT}/roles", headers=admin)
        role_ok = "operator" in roles_after.get("stored_roles", [])
        print(f"[{'PASS' if role_ok else 'FAIL'}] Role mutation survived restart")

        policy_restart = req("GET", f"/policies/{POLICY_ID}")["policy"]["version"]
        policy_ok = policy_restart == policy_after
        print(f"[{'PASS' if policy_ok else 'FAIL'}] Policy version survived restart: {policy_restart}")

        versions = req("GET", f"/policies/{POLICY_ID}/versions")
        hist_ok = versions.get("total", 0) >= 1
        print(f"[{'PASS' if hist_ok else 'FAIL'}] Policy version history available: {versions.get('total')}")

        audit = req("GET", "/audit?event_type=role_assigned&limit=5", headers=admin)
        audit_ok = audit.get("total", 0) > 0
        print(f"[{'PASS' if audit_ok else 'FAIL'}] Governance audit events persisted: {audit.get('total')}")

        approve_check = req("GET", "/approvals", headers=admin)
        auth_ok = "approvals" in approve_check
        print(f"[{'PASS' if auth_ok else 'FAIL'}] Authorization still works after restart")

        if not all([role_ok, policy_ok, hist_ok, audit_ok, auth_ok, version_ok]):
            failures += 1

    finally:
        if proc:
            proc.kill()

    print(f"\n=== Result: {failures} failure(s) ===")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
