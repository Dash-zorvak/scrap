import pytest
from src.analyzer.sentiment import SentimentAnalyzer


@pytest.fixture
def analyzer():
    return SentimentAnalyzer()


class TestSentimentAnalyzer:
    def test_positive(self, analyzer):
        label, score = analyzer.analyze("Excelente trabajo, muchas gracias")
        assert label == "positive"
        assert score > 0.5

    def test_negative(self, analyzer):
        label, score = analyzer.analyze("Terrible servicio, una vergüenza")
        assert label == "negative"
        assert score > 0.5

    def test_neutral(self, analyzer):
        label, score = analyzer.analyze("La reunión será el martes a las 10")
        assert label == "neutral"

    def test_empty(self, analyzer):
        label, score = analyzer.analyze("")
        assert label == "neutral"
        assert score == 0.0

    def test_none(self, analyzer):
        label, score = analyzer.analyze(None)
        assert label == "neutral"
        assert score == 0.0

    def test_negation_positive(self, analyzer):
        label, score = analyzer.analyze("No me gusta para nada este proyecto")
        assert label == "negative"
