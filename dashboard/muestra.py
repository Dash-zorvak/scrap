import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from config import MIN_COMENTARIOS_MUESTRA


def evaluar_muestra(n_comentarios):
    n = int(n_comentarios or 0)
    suficiente = n >= MIN_COMENTARIOS_MUESTRA
    if suficiente:
        etiqueta = f"{n} comentarios analizados"
        emoji = "\u2705"
    else:
        etiqueta = f"{n} comentarios analizados \u00b7 muestra insuficiente (m\u00edn. {MIN_COMENTARIOS_MUESTRA})"
        emoji = "\u26a0\ufe0f"
    return {"n": n, "suficiente": suficiente, "emoji": emoji, "etiqueta": etiqueta}
