"""Tenant request labeling — not a security isolation boundary."""

from __future__ import annotations

import re

from fastapi import Request

DEFAULT_TENANT_ID = "default"
_TENANT_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


def parse_tenant_id(request: Request) -> str:
    """Read X-OpenWorld-Tenant for logs only.

    Data access is NOT filtered by this value. Do not treat it as isolation.
    """
    raw = request.headers.get("X-OpenWorld-Tenant", "").strip().lower()
    if raw and _TENANT_RE.fullmatch(raw):
        return raw
    return DEFAULT_TENANT_ID
