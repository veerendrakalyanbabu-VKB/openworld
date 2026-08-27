"""Query and export audit events as an operator.

Requires a running API in demo mode on http://localhost:8000
"""

from __future__ import annotations

from packages.sdk.openworld import OpenWorldClient


def main() -> None:
    with OpenWorldClient(base_url="http://localhost:8000") as client:
        operator = client.get_demo_token("agent-ops-bot")
        listing = client.audit.list(token=operator, limit=10)
        print(f"events={listing.total} demo_mode={listing.demo_mode}")
        export = client.audit.export(format="json", token=operator, limit=10)
        print(f"export_bytes={len(export)}")


if __name__ == "__main__":
    main()
