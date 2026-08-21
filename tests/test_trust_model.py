"""Trust model tests."""

from core.models.agent import TrustDimensions


class TestTrustModel:
    def test_trust_score_calculation(self):
        dims = TrustDimensions(
            identity=100, policy=99, reliability=98, verification=99, violations=100
        )
        score = dims.overall
        assert 95 <= score <= 100

    def test_low_violations_reduce_score(self):
        good = TrustDimensions(identity=100, policy=100, reliability=100, verification=100, violations=100)
        bad = TrustDimensions(identity=100, policy=100, reliability=100, verification=100, violations=50)
        assert good.overall > bad.overall

    def test_trust_dimensions_bounded(self):
        dims = TrustDimensions(identity=0, policy=0, reliability=0, verification=0, violations=0)
        assert dims.overall == 0
