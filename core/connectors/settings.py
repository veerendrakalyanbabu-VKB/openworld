"""GitHub connector configuration from environment only — never from request bodies."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class GitHubConnectorConfig:
    enabled: bool = False
    token: str = ""
    owner: str = ""
    repo: str = ""
    timeout_seconds: float = 10.0

    @classmethod
    def from_env(cls) -> GitHubConnectorConfig:
        timeout_raw = os.environ.get("OPENWORLD_GITHUB_TIMEOUT_SECONDS", "10")
        try:
            timeout = float(timeout_raw)
        except ValueError:
            timeout = 10.0
        timeout = min(max(timeout, 1.0), 30.0)
        return cls(
            enabled=_env_bool("OPENWORLD_GITHUB_ENABLED", False),
            token=os.environ.get("OPENWORLD_GITHUB_TOKEN", "").strip(),
            owner=os.environ.get("OPENWORLD_GITHUB_OWNER", "").strip(),
            repo=os.environ.get("OPENWORLD_GITHUB_REPO", "").strip(),
            timeout_seconds=timeout,
        )

    @property
    def live_ready(self) -> bool:
        return bool(self.enabled and self.token and self.owner and self.repo)

    def redacted(self) -> dict[str, str | bool | float]:
        return {
            "enabled": self.enabled,
            "live_ready": self.live_ready,
            "owner": self.owner,
            "repo": self.repo,
            "timeout_seconds": self.timeout_seconds,
            "token_configured": bool(self.token),
        }
