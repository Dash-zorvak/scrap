"""Bloque II - Segmentacion de audiencia: calculos puros (sin Streamlit ni IO).

Provee la logica del indice de Polarizacion entendido como consenso vs
confrontacion: si la conversacion se parte en dos bandos de tamano similar
(confrontacion) o si predomina un lado / la indiferencia (consenso).
"""

import pandas as pd


def calcular_polarizacion(scores):
    """Consenso vs confrontacion a partir de scores de sentimiento por comentario.

    scores: iterable de scores de sentimiento (-1..1). Clasifica cada comentario
    en a favor (> 0.1), en contra (< -0.1) o neutral. Devuelve:
      - pct_favor / pct_contra: reparto entre quienes tomaron postura.
      - balance: 0..1, que tan parejos son los dos bandos (1 = empate total).
      - intensidad: 0..1, proporcion que tomo postura (vs neutrales).
      - indice: balance * intensidad * 100 (0..100). Alto = confrontacion real.
      - nivel/estado/lado: lectura cualitativa.
    None si no hay datos.
    """
    if scores is None:
        return None
    s = pd.to_numeric(pd.Series(list(scores), dtype="float64"), errors="coerce").dropna()
    if s.empty:
        return None
    n_total = int(len(s))
    n_favor = int((s > 0.1).sum())
    n_contra = int((s < -0.1).sum())
    comprometidos = n_favor + n_contra
    if comprometidos == 0:
        return {
            "n_total": n_total, "n_favor": 0, "n_contra": 0,
            "pct_favor": 0.0, "pct_contra": 0.0,
            "balance": 0.0, "intensidad": 0.0, "indice": 0.0,
            "nivel": "consenso", "lado": "neutral",
            "estado": "Conversaci\u00f3n mayoritariamente neutral, sin confrontaci\u00f3n",
        }
    pct_favor = n_favor / comprometidos * 100
    pct_contra = n_contra / comprometidos * 100
    balance = 2 * min(n_favor, n_contra) / comprometidos
    intensidad = comprometidos / n_total
    indice = balance * intensidad * 100
    lado = "favor" if n_favor >= n_contra else "contra"
    lado_lbl = "favorable" if lado == "favor" else "cr\u00edtico"
    if balance >= 0.6:
        nivel = "confrontacion"
        estado = "Confrontaci\u00f3n: dos bandos enfrentados de tama\u00f1o similar"
    elif balance >= 0.35:
        nivel = "dividida"
        estado = f"Conversaci\u00f3n dividida con predominio {lado_lbl}"
    else:
        nivel = "consenso"
        estado = f"Consenso {lado_lbl}: un lado domina claramente"
    return {
        "n_total": n_total, "n_favor": n_favor, "n_contra": n_contra,
        "pct_favor": round(pct_favor, 1), "pct_contra": round(pct_contra, 1),
        "balance": round(balance, 2), "intensidad": round(intensidad, 2),
        "indice": round(indice, 1), "nivel": nivel, "lado": lado,
        "estado": estado,
    }
