"""Ensure onboarding examples stay aligned with the real SDK."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_examples_import_real_sdk():
    for name in ("basic_action.py", "approval_flow.py", "audit_query.py"):
        source = (ROOT / "examples" / name).read_text(encoding="utf-8")
        assert "from packages.sdk.openworld import OpenWorldClient" in source
        assert "get_demo_token" in source or "authenticate" in source


def test_readme_uses_real_sdk_import():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "from packages.sdk.openworld import OpenWorldClient" in readme
    assert "client.actions.submit" in readme
