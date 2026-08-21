"""Validate deployment artifacts without creating cloud resources."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def main() -> int:
    failures = 0
    api_docker = _read("docker/Dockerfile.api")
    if "USER appuser" not in api_docker:
        print("[FAIL] API image must run as non-root appuser")
        failures += 1
    if "--reload" in api_docker:
        print("[FAIL] production API image must not use --reload")
        failures += 1
    if "OPENWORLD_SECRET_KEY=" in api_docker:
        print("[FAIL] API Dockerfile must not embed OPENWORLD_SECRET_KEY")
        failures += 1

    prod_compose = _read("docker-compose.prod.example.yml")
    if "OPENWORLD_DEMO_MODE: \"false\"" not in prod_compose:
        print("[FAIL] prod compose must set DEMO_MODE false")
        failures += 1
    if "dev-only-not-for-production" in prod_compose:
        print("[FAIL] prod compose must not embed the default dev secret")
        failures += 1

    prod_env = _read(".env.production.example")
    if "OPENWORLD_DEMO_MODE=false" not in prod_env:
        print("[FAIL] production env example must disable demo mode")
        failures += 1

    if failures:
        print(f"\n=== Result: {failures} failure(s) ===")
        return 1
    print("[PASS] deployment artifacts look production-oriented")
    print("Status: READY FOR DEPLOYMENT (not ACTUALLY DEPLOYED)")
    print("=== Result: 0 failure(s) ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
