"""Tests: distribucion_sentimiento redondeo derivado pf+pc → pn = 100.0 exacto.

Caso de bug: 2 favorables + 3 neutrales + 2 críticos (n=7) daba 100.1% porque pf,
pn y pc se redondeaban independientemente. Ahora pn = round(100 - pf - pc, 1).
"""
import pandas as pd
from dashboard.dash_fuente import distribucion_sentimiento


def _df_con_sentimientos(sentiments):
    """DataFrame sin columna plataforma → fuerza _dist_por_comentario."""
    return pd.DataFrame({"sentiment": sentiments, "sentiment_score": [None] * len(sentiments)})


class TestRedondeoSumaCien:

    def test_2f_3n_2c_suma_100(self):
        """Caso que antes daba 100.1%: ahora pf+pn+pc == 100.0."""
        df = _df_con_sentimientos(["POS", "POS", "NEU", "NEU", "NEU", "NEG", "NEG"])
        dist = distribucion_sentimiento(df)
        total = dist["pct_favorable"] + dist["pct_neutral"] + dist["pct_critico"]
        assert total == 100.0, f"Suma {total} != 100.0"
        assert dist["n_favorable"] + dist["n_neutral"] + dist["n_critico"] == 7

    def test_balanceado_suma_100(self):
        """Caso simple balanceado sigue sumando 100.0."""
        df = _df_con_sentimientos(["POS"] * 3 + ["NEU"] * 3 + ["NEG"] * 3)
        dist = distribucion_sentimiento(df)
        total = dist["pct_favorable"] + dist["pct_neutral"] + dist["pct_critico"]
        assert abs(total - 100.0) < 1e-9, f"Suma {total} != 100.0"
        assert dist["n_favorable"] + dist["n_neutral"] + dist["n_critico"] == 9

    def test_todos_favorable(self):
        """100% favorable."""
        df = _df_con_sentimientos(["POS"] * 10)
        dist = distribucion_sentimiento(df)
        assert dist == {
            "n_total": 10, "n_favorable": 10, "n_neutral": 0, "n_critico": 0,
            "pct_favorable": 100.0, "pct_neutral": 0.0, "pct_critico": 0.0,
        }

    def test_todos_critico(self):
        """100% crítico."""
        df = _df_con_sentimientos(["NEG"] * 5)
        dist = distribucion_sentimiento(df)
        assert dist["pct_favorable"] + dist["pct_neutral"] + dist["pct_critico"] == 100.0
        assert dist["n_favorable"] + dist["n_neutral"] + dist["n_critico"] == 5

    def test_un_solo_favorable(self):
        """Un único favorable, resto neutral."""
        df = _df_con_sentimientos(["POS"] + ["NEU"] * 99)
        dist = distribucion_sentimiento(df)
        assert abs(dist["pct_favorable"] + dist["pct_neutral"] + dist["pct_critico"] - 100.0) < 1e-9
        assert dist["n_favorable"] + dist["n_neutral"] + dist["n_critico"] == 100

    def test_nf_nn_nc_igual_n_varios_casos(self):
        """n_favorable + n_neutral + n_critico == n_total siempre."""
        casos = [
            (["POS"] * 3 + ["NEU"] * 4 + ["NEG"] * 5, 12),
            (["POS"] * 7 + ["NEG"] * 3, 10),
            (["POS", "NEG", "NEU"], 3),
            (["POS"] * 50 + ["NEU"] * 30 + ["NEG"] * 20, 100),
        ]
        for sentiments, n in casos:
            df = _df_con_sentimientos(sentiments)
            dist = distribucion_sentimiento(df)
            assert dist["n_favorable"] + dist["n_neutral"] + dist["n_critico"] == n, (
                f"Suma != {n} para n={n}"
            )
