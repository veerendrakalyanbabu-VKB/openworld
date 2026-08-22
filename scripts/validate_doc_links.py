"""Validate Markdown documentation links (local files only)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
SCAN_PATHS = [
    ROOT / "README.md",
    ROOT / "CHANGELOG.md",
    ROOT / "SECURITY.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "CODE_OF_CONDUCT.md",
    *sorted((ROOT / "docs").glob("*.md")),
]
LOCALHOST_LINK_RE = re.compile(r"^https?://(localhost|127\.0\.0\.1)", re.I)


def _resolve_target(source: Path, target: str) -> Path | None:
    target = target.split("#", 1)[0].strip()
    if not target or target.startswith(("http://", "https://", "mailto:")):
        return None
    if target.startswith("/"):
        return ROOT / target.lstrip("/")
    return (source.parent / target).resolve()


def validate() -> list[str]:
    errors: list[str] = []
    for path in SCAN_PATHS:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT).as_posix()
        for _label, target in LINK_RE.findall(text):
            if LOCALHOST_LINK_RE.match(target.strip()):
                if rel == "README.md":
                    errors.append(f"{rel}: clickable localhost link not allowed: ({target})")
                continue
            resolved = _resolve_target(path, target)
            if resolved is None:
                continue
            if not resolved.exists():
                errors.append(f"{rel}: broken link target missing: {target}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Documentation link validation failed:")
        for err in errors:
            print(f"  - {err}")
        print(f"\n=== Result: {len(errors)} failure(s) ===")
        return 1
    print("[PASS] documentation links look valid")
    print("=== Result: 0 failure(s) ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
