"""Tests: BERT retry cooldown — fallo → cooldown corto → recuperación tras cooldown."""
import time

from dashboard import sentimiento_engine as se


class TestBERTRetryCooldown:

    def teardown_method(self):
        se._BERT_FALLO = False
        se._BERT_FALLO_TS = 0.0
        se._bert_analyzer = None

    def test_fallo_activa_cooldown(self, monkeypatch):
        """Si BERT falla, _BERT_FALLO y _BERT_FALLO_TS se actualizan."""
        se._BERT_FALLO = False
        se._BERT_FALLO_TS = 0.0
        se._bert_analyzer = None

        def mock_cargar_bert():
            raise RuntimeError("carga falló")

        monkeypatch.setattr(se, "_cargar_bert", mock_cargar_bert)
        monkeypatch.setattr(se, "groq_disponible", lambda: False)

        se.clasificar_lote(["texto de prueba"])
        assert se._BERT_FALLO is True
        assert se._BERT_FALLO_TS > 0

    def test_cooldown_corto_luego_recuperacion(self, monkeypatch):
        """Después del cooldown, se intenta carga completa otra vez."""
        se._BERT_FALLO = True
        se._BERT_FALLO_TS = time.time() - se.BERT_RETRY_COOLDOWN_S - 10  # cooldown pasado

        carga_veces = [0]

        def mock_cargar_bert():
            carga_veces[0] += 1
            class MockAnalyzer:
                def predict(self, textos):
                    class MockOutput:
                        def __init__(self):
                            self.output = "POS"
                            self.probas = {"POS": 0.95}
                    return [MockOutput()]
            return MockAnalyzer()

        monkeypatch.setattr(se, "_cargar_bert", mock_cargar_bert)
        monkeypatch.setattr(se, "groq_disponible", lambda: False)

        _, motor = se.clasificar_lote(["buen texto"])
        assert motor == "bert", "Debe recuperarse tras el cooldown"
        assert carga_veces[0] >= 1  # _cargar_bert se llama al menos 1 vez

    def test_fallo_reciente_timeout_corto(self, monkeypatch):
        """Fallo reciente → timeout de 1s (no espera carga completa)."""
        se._BERT_FALLO = True
        se._BERT_FALLO_TS = time.time() - 60  # cooldown NO pasado (600s default)
        se._bert_analyzer = None

        carga_llamado = [False]

        def mock_cargar_lenta():
            carga_llamado[0] = True
            time.sleep(5)  # supera el timeout de 1s

        monkeypatch.setattr(se, "_cargar_bert", mock_cargar_lenta)
        monkeypatch.setattr(se, "groq_disponible", lambda: False)

        se.clasificar_lote(["otro texto"])
        # El thread se lanzó pero timeout de 1s lo abortó
        assert carga_llamado[0] is True
        assert se._BERT_FALLO is True
