"""Permission/capability validation tests."""

from core.demo.seed import DEMO_AGENTS
from core.permissions.validator import PermissionValidator


class TestPermissionValidator:
    def setup_method(self):
        self.validator = PermissionValidator()
        self.finance_bot = next(a for a in DEMO_AGENTS if a.name == "FinanceBot")
        self.email_bot = next(a for a in DEMO_AGENTS if a.name == "EmailBot")
        self.data_bot = next(a for a in DEMO_AGENTS if a.name == "DataBot")

    def test_permitted_capability(self):
        result = self.validator.validate(self.finance_bot, "payment.create")
        assert result.permitted is True

    def test_permitted_email_capability(self):
        result = self.validator.validate(self.email_bot, "email.send")
        assert result.permitted is True

    def test_missing_capability(self):
        result = self.validator.validate(self.email_bot, "payment.create")
        assert result.permitted is False
        assert "payment.create" in result.missing_capabilities

    def test_databot_has_db_write_capability(self):
        result = self.validator.validate(self.data_bot, "database.write")
        assert result.permitted is True

    def test_databot_lacks_email_capability(self):
        result = self.validator.validate(self.data_bot, "email.send")
        assert result.permitted is False
