"""Regresión: clasificar_comentario no debe romper con valores nulos de pandas.

Bug original (dashboard): al renderizar el bloque de riesgo,
`df.apply(clasificar_comentario, axis=1)` lanzaba
"TypeError: boolean value of NA is ambiguous" porque clasificar_comentario
hacía `str(row.get("sentiment") or "")` y, cuando sentiment era pd.NA (columna
opcional rellenada con NA), `pd.NA or ""` invoca bool(pd.NA), cuyo valor de
verdad es ambiguo.

Estos tests fijan el comportamiento esperado y reproducen el escenario exacto
(apply sobre un DataFrame con dtypes nullable que contienen pd.NA).
"""

import pandas as pd

from dashboard.dash_fuente import clasificar_comentario


class TestClasificarComentarioNA:
    def test_sentiment_na_devuelve_neutral(self):
        row = pd.Series({"sentiment": pd.NA, "sentiment_score": pd.NA})
        assert clasificar_comentario(row) == "neutral"

    def test_sentiment_none_devuelve_neutral(self):
        row = pd.Series({"sentiment": None, "sentiment_score": None})
        assert clasificar_comentario(row) == "neutral"

    def test_sentiment_na_pero_score_favorable(self):
        row = pd.Series({"sentiment": pd.NA, "sentiment_score": 0.5})
        assert clasificar_comentario(row) == "favorable"

    def test_sentiment_na_pero_score_critico(self):
        row = pd.Series({"sentiment": pd.NA, "sentiment_score": -0.5})
        assert clasificar_comentario(row) == "critico"

    def test_sentiment_texto_positivo(self):
        row = pd.Series({"sentiment": "positivo", "sentiment_score": pd.NA})
        assert clasificar_comentario(row) == "favorable"

    def test_sentiment_texto_negativo(self):
        row = pd.Series({"sentiment": "NEGATIVO", "sentiment_score": pd.NA})
        assert clasificar_comentario(row) == "critico"


class TestApplyReproduceBug:
    """Escenario exacto que reventaba: apply sobre dtypes nullable con pd.NA."""

    def test_apply_con_na_no_rompe(self):
        df = pd.DataFrame(
            {
                "sentiment": pd.array([pd.NA, "negativo", "positivo"], dtype="string"),
                "sentiment_score": pd.array([pd.NA, pd.NA, pd.NA], dtype="Float64"),
            }
        )
        etiquetas = df.apply(clasificar_comentario, axis=1)
        assert list(etiquetas) == ["neutral", "critico", "favorable"]

    def test_apply_score_nullable_decide(self):
        df = pd.DataFrame(
            {
                "sentiment": pd.array([pd.NA, pd.NA], dtype="string"),
                "sentiment_score": pd.array([0.8, -0.8], dtype="Float64"),
            }
        )
        etiquetas = df.apply(clasificar_comentario, axis=1)
        assert list(etiquetas) == ["favorable", "critico"]
