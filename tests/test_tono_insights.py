"""Regresion de tono en insights (dashboard/dash_metrics.py).

Blinda el fix de tono crudo / sin lenguaje de campana:
- generar_interpretacion(): sin "publicar mas obras", sin lenguaje electoral,
  con framing de percepcion ciudadana.
- generar_narrativa_ia(): persona de "analista de percepcion ciudadana",
  reglas obligatorias de salida (tono crudo, prohibicion de campana/propaganda,
  exigir cifras), sin la instruccion previa "orientado a decision de reeleccion".

No requiere red ni Groq: generar_interpretacion es deterministico y
generar_narrativa_ia se prueba mockeando chat_texto/groq_disponible.
"""
import pytest

import dashboard.dash_metrics as dm
from dashboard.dash_metrics import generar_interpretacion


# Palabras de campana/electorales que NO deben aparecer en el texto que se
# muestra al alcalde/ciudadano.
_PALABRAS_CAMPANA = [
    "campana",
    "campa\u00f1a",
    "reeleccion",
    "reelecci\u00f3n",
    "electoral",
    "propaganda",
]

# Cubre todas las ramas de generar_interpretacion con datos validos.
_CASOS_INTERPRETACION = [
    ("semaforo", {"score": 0.5, "pct_positivo": 72, "pct_negativo": 10, "indice_enojo": 0.05}),
    ("semaforo", {"score": 0.15, "pct_positivo": 50, "pct_negativo": 22, "indice_enojo": 0.10}),
    ("semaforo", {"score": 0.05, "pct_positivo": 40, "pct_negativo": 33, "indice_enojo": 0.20}),
    ("semaforo", {"score": -0.4, "pct_positivo": 20, "pct_negativo": 61, "indice_enojo": 0.45}),
    ("tema_critico", {"tema": "Baches", "reacciones": 1200, "pct_negativo": 44}),
    ("tema_positivo", {"tema": "Fiestas patronales", "pct_positivo": 81}),
    ("anomalia", {"fecha": "2026-06-01", "views": 5000, "tipo": "positivo"}),
    ("anomalia", {"fecha": "2026-06-08", "views": 1200, "tipo": "negativo"}),
    ("patron_rechazo", {"nombre": "Abandono", "count": 25, "tendencia": "Creciendo"}),
    ("patron_respaldo", {"nombre": "Reconocimiento", "count": 30}),
    ("microsegmentacion", {"tipo": "Video", "engagement": 1500, "patron": "ALTO IMPACTO"}),
    ("microsegmentacion", {"tipo": "Texto", "engagement": 120, "patron": "BAJO IMPACTO"}),
    ("microsegmentacion", {"tipo": "Foto", "engagement": 600, "patron": "MEDIO"}),
    ("contexto_externo", {"negativas": 10, "total": 40, "fuente_top": "Diario X"}),
]


class TestInterpretacionTono:
    @pytest.mark.parametrize("tipo,datos", _CASOS_INTERPRETACION)
    def test_sin_lenguaje_de_campana(self, tipo, datos):
        texto = generar_interpretacion(tipo, datos)
        assert isinstance(texto, str) and texto.strip()
        bajo = texto.lower()
        for palabra in _PALABRAS_CAMPANA:
            assert palabra not in bajo, (
                f"'{palabra}' aparecio en interpretacion '{tipo}': {texto}"
            )

    def test_semaforo_verde_no_pide_publicar_obras(self):
        texto = generar_interpretacion(
            "semaforo",
            {"score": 0.5, "pct_positivo": 72, "pct_negativo": 8, "indice_enojo": 0.04},
        )
        bajo = texto.lower()
        assert "publicar mas" not in bajo
        assert "publicar m\u00e1s" not in bajo
        assert "obras y logros" not in bajo
        assert "72%" in texto

    def test_semaforo_rojo_confianza_ciudadana_no_electoral(self):
        texto = generar_interpretacion(
            "semaforo",
            {"score": -0.5, "pct_positivo": 15, "pct_negativo": 65, "indice_enojo": 0.5},
        )
        bajo = texto.lower()
        assert "ALERTA" in texto or "enojo" in bajo
        assert "electoral" not in bajo

    def test_patron_rechazo_sin_oposicion_ni_campana(self):
        texto = generar_interpretacion(
            "patron_rechazo",
            {"nombre": "Abandono", "count": 40, "tendencia": "Creciendo"},
        )
        bajo = texto.lower()
        assert "oposici\u00f3n" not in bajo
        assert "oposicion" not in bajo
        assert "campa\u00f1a" not in bajo
        assert "ciudadan" in bajo

    def test_patron_respaldo_respaldo_ciudadano(self):
        texto = generar_interpretacion(
            "patron_respaldo", {"nombre": "Reconocimiento", "count": 30}
        )
        bajo = texto.lower()
        assert "respaldo ciudadano" in bajo
        assert "capital pol\u00edtico" not in bajo


_TIPOS_NARRATIVA = [
    "eco_historico",
    "leccion",
    "brecha",
    "contexto",
    "correlacion",
    "proyeccion",
    "recomendacion",
]


class TestNarrativaIAPrompt:
    """Verifica el PROMPT enviado a Groq (chat_texto mockeado)."""

    def _capturar_prompt(self, monkeypatch, tipo):
        capturado = {}

        def fake_chat_texto(prompt, *args, **kwargs):
            capturado["prompt"] = prompt
            return "respuesta simulada"

        monkeypatch.setattr(dm, "groq_disponible", lambda: True)
        monkeypatch.setattr(dm, "chat_texto", fake_chat_texto)
        # generar_narrativa_ia esta decorada con @st.cache_data; limpiamos la
        # cache para forzar la ejecucion real con el mock activo.
        dm.generar_narrativa_ia.clear()
        dm.generar_narrativa_ia(tipo, {"score": 0.1, "pct_negativo": 20})
        return capturado["prompt"]

    @pytest.mark.parametrize("tipo", _TIPOS_NARRATIVA)
    def test_reglas_y_persona(self, monkeypatch, tipo):
        prompt = self._capturar_prompt(monkeypatch, tipo)
        assert "REGLAS OBLIGATORIAS DE SALIDA" in prompt
        assert "PROHIBIDO" in prompt
        assert "analista de percepci\u00f3n ciudadana" in prompt
        assert "analista pol\u00edtico senior" not in prompt
        assert "orientado a decisi\u00f3n de reelecci\u00f3n" not in prompt

    def test_sin_groq_devuelve_aviso(self, monkeypatch):
        monkeypatch.setattr(dm, "groq_disponible", lambda: False)
        dm.generar_narrativa_ia.clear()
        out = dm.generar_narrativa_ia("recomendacion", {"score": 0.1})
        assert isinstance(out, str)
        assert "no disponible" in out.lower()
