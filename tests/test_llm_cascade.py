"""Tests de la cascada de verificacion cruzada (dashboard/llm_cascade.py).

Todo es puro: no se toca la red. La funcion clasificadora se inyecta como un
fake que responde por texto, lo que permite verificar el enrutamiento
(primario -> verificador) y la reconciliacion.
"""
import pytest

from dashboard.llm_cascade import (
    debe_verificar,
    reconciliar,
    clasificar_con_cascada,
    CONFIANZA_DESACUERDO,
)


def _res(cat, tono="literal", conf=0.9, motor="llm"):
    return {"categoria": cat, "tono": tono, "confianza": conf, "motor": motor}


class TestDebeVerificar:
    def test_baja_confianza_se_verifica(self):
        assert debe_verificar(_res("seguridad", conf=0.4)) is True

    def test_alta_confianza_literal_no_se_verifica(self):
        assert debe_verificar(_res("seguridad", conf=0.95)) is False

    def test_sarcasmo_siempre_se_verifica(self):
        # Aun con confianza alta, el sarcasmo se re-verifica.
        assert debe_verificar(_res("apoyo_generico", tono="sarcastico", conf=0.98)) is True

    def test_umbral_personalizado(self):
        assert debe_verificar(_res("empleo", conf=0.6), umbral=0.5) is False
        assert debe_verificar(_res("empleo", conf=0.6), umbral=0.7) is True

    def test_no_dict_no_se_verifica(self):
        assert debe_verificar("x") is False


class TestReconciliar:
    def test_acuerdo_refuerza_confianza(self):
        p = _res("seguridad", conf=0.5)
        v = _res("seguridad", conf=0.7)
        out = reconciliar(p, v)
        assert out["categoria"] == "seguridad"
        assert out["acuerdo"] is True
        assert out["verificado"] is True
        assert out["confianza"] > 0.7

    def test_desacuerdo_degrada_a_dudoso(self):
        p = _res("seguridad", conf=0.6)
        v = _res("no_aplica", conf=0.8)
        out = reconciliar(p, v)
        # La categoria efectiva sigue siendo la del primario...
        assert out["categoria"] == "seguridad"
        # ...pero se conserva la referencia del verificador y baja la confianza.
        assert out["categoria_verificador"] == "no_aplica"
        assert out["acuerdo"] is False
        assert out["confianza"] <= CONFIANZA_DESACUERDO

    def test_sarcasmo_gana_en_reconciliacion(self):
        p = _res("no_aplica", tono="literal", conf=0.5)
        v = _res("no_aplica", tono="sarcastico", conf=0.5)
        out = reconciliar(p, v)
        assert out["tono"] == "sarcastico"

    def test_verificador_invalido_devuelve_primario(self):
        p = _res("empleo", conf=0.5)
        assert reconciliar(p, None) == p


class TestClasificarConCascada:
    def _fake_fn(self, mapa_primario, mapa_verif, registro):
        def fn(textos, model=None):
            registro.setdefault("primario", 0)
            registro.setdefault("verif", 0)
            if model is None:
                registro["primario"] += 1
                return [dict(mapa_primario[t]) for t in textos]
            registro["verif"] += 1
            registro["verif_model"] = model
            return [dict(mapa_verif[t]) for t in textos]
        return fn

    def test_solo_verifica_los_dudosos(self):
        registro = {}
        primario = {
            "a": _res("seguridad", conf=0.95),   # no se verifica
            "b": _res("empleo", conf=0.3),        # se verifica
        }
        verif = {"b": _res("empleo", conf=0.8)}
        fn = self._fake_fn(primario, verif, registro)
        out = clasificar_con_cascada(["a", "b"], fn, verificador_model="glm")
        assert registro["primario"] == 1
        assert registro["verif"] == 1
        assert registro["verif_model"] == "glm"
        # 'a' queda intacto (sin campo verificado); 'b' reconciliado en acuerdo.
        assert "verificado" not in out[0]
        assert out[1]["acuerdo"] is True

    def test_sin_verificador_no_reverifica(self):
        registro = {}
        primario = {"a": _res("seguridad", conf=0.1)}
        fn = self._fake_fn(primario, {}, registro)
        out = clasificar_con_cascada(["a"], fn, verificador_model=None)
        assert registro["primario"] == 1
        assert registro.get("verif", 0) == 0
        assert out[0]["categoria"] == "seguridad"

    def test_ninguno_dudoso_no_llama_verificador(self):
        registro = {}
        primario = {"a": _res("seguridad", conf=0.95), "b": _res("salud", conf=0.9)}
        fn = self._fake_fn(primario, {}, registro)
        out = clasificar_con_cascada(["a", "b"], fn, verificador_model="glm")
        assert registro.get("verif", 0) == 0
        assert len(out) == 2

    def test_verificador_falla_conserva_primario(self):
        def fn(textos, model=None):
            if model is not None:
                raise RuntimeError("verificador caido")
            return [_res("empleo", conf=0.2) for _ in textos]
        out = clasificar_con_cascada(["a"], fn, verificador_model="glm")
        assert out[0]["categoria"] == "empleo"
        assert "verificado" not in out[0]

    def test_lista_vacia(self):
        out = clasificar_con_cascada([], lambda textos, model=None: [], verificador_model="glm")
        assert out == []


class TestWiringTopicLlm:
    """Verifica que clasificar_temas_lote use la cascada cuando esta activa."""

    def test_topic_llm_usa_cascada(self, monkeypatch):
        import dashboard.topic_llm as tl
        import dashboard.llm_groq as lg

        monkeypatch.setattr(lg, "groq_disponible", lambda: True)
        monkeypatch.setattr(tl, "CASCADA_ACTIVA", True)
        monkeypatch.setattr(tl, "_verifier_model", lambda: "glm-test")

        registro = {"primario": 0, "verif": 0}

        def fake_block(textos, model=None):
            if model is None:
                registro["primario"] += 1
                return [
                    {"categoria": "seguridad", "tono": "literal",
                     "confianza": 0.2, "motor": "llm"}
                    for _ in textos
                ]
            registro["verif"] += 1
            return [
                {"categoria": "seguridad", "tono": "literal",
                 "confianza": 0.9, "motor": "llm"}
                for _ in textos
            ]

        monkeypatch.setattr(tl, "_clasificar_bloque_llm", fake_block)

        out = tl.clasificar_temas_lote(["hola", "mundo"])
        assert len(out) == 2
        assert registro["primario"] == 1
        assert registro["verif"] == 1
        assert out[0]["verificado"] is True
        assert out[0]["acuerdo"] is True
