"""Bounded GitHub issue-creation connector.

Allowlisted operation: POST /repos/{owner}/{repo}/issues on api.github.com only.
Owner and repo come from environment configuration, never from the action payload.
Disabled by default. Live calls require OPENWORLD_GITHUB_ENABLED plus token/owner/repo.
"""

from __future__ import annotations

import re
from typing import Any

import httpx

from core.connectors.base import (
    Connector,
    ConnectorResult,
    ConnectorTimeoutError,
    ConnectorValidationError,
)
from core.connectors.settings import GitHubConnectorConfig
from core.models.action import ActionRequest

GITHUB_API_BASE = "https://api.github.com"
MAX_TITLE_LEN = 256
MAX_BODY_LEN = 65536
MAX_LABELS = 5
MAX_LABEL_LEN = 50
ALLOWED_FIELDS = {"title", "body", "labels"}
LABEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,49}$")
OWNER_REPO_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$")


class GitHubIssuesConnector(Connector):
    def __init__(
        self,
        config: GitHubConnectorConfig | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.config = config or GitHubConnectorConfig.from_env()
        self._transport = transport

    @property
    def name(self) -> str:
        return "github_issues"

    @property
    def action(self) -> str:
        return "github.issue.create"

    def validate_parameters(self, parameters: dict[str, Any]) -> dict[str, Any]:
        extra = set(parameters) - ALLOWED_FIELDS
        if extra:
            raise ConnectorValidationError(
                f"Unsupported fields for github.issue.create: {sorted(extra)}"
            )
        title = parameters.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ConnectorValidationError("title is required")
        title = title.strip()
        if len(title) > MAX_TITLE_LEN:
            raise ConnectorValidationError(f"title exceeds {MAX_TITLE_LEN} characters")

        body = parameters.get("body", "")
        if body is None:
            body = ""
        if not isinstance(body, str):
            raise ConnectorValidationError("body must be a string")
        if len(body) > MAX_BODY_LEN:
            raise ConnectorValidationError(f"body exceeds {MAX_BODY_LEN} characters")

        labels = parameters.get("labels", [])
        if labels is None:
            labels = []
        if not isinstance(labels, list):
            raise ConnectorValidationError("labels must be a list")
        if len(labels) > MAX_LABELS:
            raise ConnectorValidationError(f"at most {MAX_LABELS} labels allowed")
        clean_labels: list[str] = []
        for label in labels:
            if not isinstance(label, str) or not LABEL_PATTERN.fullmatch(label):
                raise ConnectorValidationError("invalid label")
            if len(label) > MAX_LABEL_LEN:
                raise ConnectorValidationError("invalid label")
            clean_labels.append(label)
        return {"title": title, "body": body, "labels": clean_labels}

    async def run(self, action: ActionRequest) -> ConnectorResult:
        try:
            payload = self.validate_parameters(action.parameters)
        except ConnectorValidationError as exc:
            return ConnectorResult(success=False, error=str(exc), live=False, dry_run=not self.config.live_ready)

        if not self.config.live_ready:
            return ConnectorResult(
                success=True,
                live=False,
                dry_run=True,
                output={
                    "status": "created",
                    "live": False,
                    "dry_run": True,
                    "live_verified": False,
                    "reason": "GitHub connector disabled or credentials not configured",
                    "owner": self.config.owner,
                    "repo": self.config.repo,
                    "title": payload["title"],
                    "issue_number": None,
                    "html_url": None,
                },
            )

        if not OWNER_REPO_PATTERN.fullmatch(self.config.owner) or not OWNER_REPO_PATTERN.fullmatch(self.config.repo):
            return ConnectorResult(
                success=False,
                error="Invalid GitHub owner or repo configuration",
                live=False,
            )

        try:
            return await self._create_issue(payload)
        except ConnectorTimeoutError as exc:
            return ConnectorResult(success=False, error=str(exc), live=True)

    async def _create_issue(self, payload: dict[str, Any]) -> ConnectorResult:
        url = f"{GITHUB_API_BASE}/repos/{self.config.owner}/{self.config.repo}/issues"
        headers = {
            "Authorization": f"Bearer {self.config.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "OpenWorld-Connector",
        }
        body = {"title": payload["title"], "body": payload["body"]}
        if payload["labels"]:
            body["labels"] = payload["labels"]

        last_error = "GitHub request failed"
        async with httpx.AsyncClient(
            timeout=self.config.timeout_seconds,
            transport=self._transport,
            follow_redirects=False,
        ) as client:
            for attempt in range(2):
                try:
                    response = await client.post(url, json=body, headers=headers)
                except httpx.TimeoutException as exc:
                    raise ConnectorTimeoutError("GitHub request timed out") from exc
                except httpx.RequestError:
                    last_error = "GitHub request failed"
                    if attempt == 0:
                        continue
                    return ConnectorResult(success=False, error=last_error, live=True)

                if response.status_code in {502, 503, 429} and attempt == 0:
                    continue
                if response.status_code == 201:
                    data = response.json()
                    return ConnectorResult(
                        success=True,
                        live=True,
                        dry_run=False,
                        output={
                            "status": "created",
                            "live": True,
                            "dry_run": False,
                            "live_verified": False,
                            "owner": self.config.owner,
                            "repo": self.config.repo,
                            "title": payload["title"],
                            "issue_number": data.get("number"),
                            "html_url": data.get("html_url"),
                        },
                    )
                last_error = f"GitHub rejected issue creation ({response.status_code})"
                return ConnectorResult(success=False, error=last_error, live=True)

        return ConnectorResult(success=False, error=last_error, live=True)
