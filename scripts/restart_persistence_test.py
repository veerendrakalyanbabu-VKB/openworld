"""Quick restart persistence verification."""

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = "http://localhost:8000/api/v1"


def req(method: str, path: str, body=None, headers=None):
    data = json.dumps(body).encode() if body else None
    h = {"Content-Type": "application/json", **(headers or {})}
    r = urllib.request.Request(f"{BASE}{path}", data=data, method=method, headers=h)
    with urllib.request.urlopen(r, timeout=15) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    agents = req("GET", "/auth/demo-agents")["agents"]
    email = next(a for a in agents if a["agent_name"] == "EmailBot")
    headers = {
        "Authorization": f"Bearer {email['access_token']}",
        "Idempotency-Key": str(uuid.uuid4()),
    }
    action = req(
        "POST",
        "/actions",
        {"action": "email.send", "parameters": {"to": "restart@test.com"}, "auto_approve": True},
        headers,
    )["action"]
    action_id = action["id"]
    print(f"Created action {action_id}")

    audit_before = req("GET", "/audit?limit=1")["total"]
    print(f"Audit events before restart: {audit_before}")

    print("Restarting API process...")
    subprocess.run(
        ["powershell", "-Command", "Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force"],
        check=False,
    )
    time.sleep(2)
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "apps.api.main:app", "--port", "8000"],
        cwd=str(__import__("pathlib").Path(__file__).resolve().parents[1]),
    )
    for _ in range(30):
        try:
            req("GET", "/health")
            break
        except (urllib.error.URLError, TimeoutError):
            time.sleep(1)
    else:
        print("FAIL: API did not restart")
        proc.kill()
        return 1

    actions = req("GET", "/actions?limit=200")["actions"]
    restored = next((a for a in actions if a["id"] == action_id), None)
    if not restored:
        print("FAIL: Action not found after restart")
        proc.kill()
        return 1
    print(f"Action after restart: status={restored['status']} PASS")

    audit_after = req("GET", "/audit?limit=1")["total"]
    if audit_after < audit_before:
        print("FAIL: Audit events lost after restart")
        proc.kill()
        return 1
    print(f"Audit events after restart: {audit_after} PASS")

    agents_after = req("GET", "/agents")["agents"]
    if not any(a["name"] == "EmailBot" for a in agents_after):
        print("FAIL: Agents lost after restart")
        proc.kill()
        return 1
    print("Agents persisted: PASS")
    print("Restart persistence test: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
