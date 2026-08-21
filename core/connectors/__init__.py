"""Bounded external connectors — executed only after Trust Core gates."""

from core.connectors.base import Connector, ConnectorResult, ConnectorValidationError
from core.connectors.github_issues import GitHubIssuesConnector
from core.connectors.settings import GitHubConnectorConfig

__all__ = [
    "Connector",
    "ConnectorResult",
    "ConnectorValidationError",
    "GitHubConnectorConfig",
    "GitHubIssuesConnector",
]
