import pytest
from src.analyzer.sentiment import SentimentAnalyzer
import src.analyzer.sentiment as _s


@pytest.fixture(autouse=True)
def _disable_external():
    _s._PYSENTIMIENTO_TRIED = True
    _s.HAS_PYSENTIMIENTO = False
    _s._FALLBACK_TRIED = True
    _s.HAS_FALLBACK = False


@pytest.fixture
def analyzer():
    return SentimentAnalyzer()


class TestSentimentAnalyzer:
    def test_positive(self, analyzer):
        label, score = analyzer.analyze("Excelente trabajo, muchas gracias")
        assert label in ("muy_positivo", "positivo")
        assert score > 0.5

    def test_negative(self, analyzer):
        label, score = analyzer.analyze("Terrible servicio, una vergüenza")
        assert label in ("muy_negativo", "negativo")
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
        assert label in ("negativo", "muy_negativo")

    def test_strong_positive(self, analyzer):
        label, score = analyzer.analyze("Excelente, maravilloso, perfecto")
        assert label == "muy_positivo"
