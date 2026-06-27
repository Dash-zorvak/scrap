"""Tests de la cascada de visión (dashboard/llm_groq.py).

Puro/offline: se inyecta un cliente OpenAI falso vía monkeypatch sobre
_get_groq_client, de modo que se verifica el enrutamiento primario -> respaldo
sin tocar la red. Refleja el estilo de tests/test_llm_cascade.py.
"""
import pytest

import dashboard.llm_groq as lg


class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Message(content)


class _Resp:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _Completions:
    def __init__(self, parent):
        self._parent = parent

    def create(self, **kwargs):
        modelo = kwargs.get("model")
        self._parent.llamadas.append(modelo)
        if modelo in self._parent.rotos:
            raise RuntimeError(
                self._parent.errores.get(
                    modelo, "Error code: 500 - internal server error"
                )
            )
        return _Resp(f"ok:{modelo}")


class _Chat:
    def __init__(self, parent):
        self.completions = _Completions(parent)


class FakeClient:
    """Cliente OpenAI falso. `rotos` = modelos que lanzan; `errores` = mensaje
    por modelo. Registra el orden de modelos invocados en `llamadas`."""

    def __init__(self, rotos=(), errores=None):
        self.rotos = set(rotos)
        self.errores = errores or {}
        self.llamadas = []
        self.chat = _Chat(self)


@pytest.fixture
def fake_vision(monkeypatch):
    """Fija primario/respaldo deterministas e instala un FakeClient."""
    monkeypatch.setattr(lg, "VISION_MODEL", "primario/phi")
    monkeypatch.setattr(lg, "VISION_FALLBACKS", ["respaldo/llama"])

    def _instalar(client):
        monkeypatch.setattr(lg, "_get_groq_client", lambda: client)
        return client

    return _instalar


class TestEsErrorModelo:
    @pytest.mark.parametrize("msg", [
        "Error code: 500 - internal server error",
        "502 Bad Gateway",
        "503 Service Unavailable",
        "Error code: 404 - model not found",
        "the model does not exist",
        "model_not_found",
    ])
    def test_detecta_errores_de_modelo(self, msg):
        assert lg._es_error_modelo(RuntimeError(msg)) is True

    @pytest.mark.parametrize("msg", [
        "Error code: 401 - unauthorized",
        "invalid api key",
        "Error code: 400 - bad request: malformed input",
    ])
    def test_ignora_otros_errores(self, msg):
        assert lg._es_error_modelo(RuntimeError(msg)) is False


class TestModelosVision:
    def test_modelo_explicito_sin_cascada(self):
        assert lg._modelos_vision("forzado/x") == ["forzado/x"]


class TestChatVisionCascada:
    def test_usa_primario_si_funciona(self, fake_vision):
        client = fake_vision(FakeClient())
        out = lg.chat_vision("prompt", [])
        assert out == "ok:primario/phi"
        assert client.llamadas == ["primario/phi"]

    def test_cae_a_respaldo_en_500(self, fake_vision):
        client = fake_vision(FakeClient(rotos=["primario/phi"]))
        out = lg.chat_vision("prompt", [])
        assert out == "ok:respaldo/llama"
        assert client.llamadas == ["primario/phi", "respaldo/llama"]

    def test_error_no_modelo_no_usa_respaldo(self, fake_vision):
        client = fake_vision(FakeClient(
            rotos=["primario/phi"],
            errores={"primario/phi": "Error code: 401 - unauthorized"},
        ))
        with pytest.raises(Exception):
            lg.chat_vision("prompt", [])
        assert client.llamadas == ["primario/phi"]

    def test_modelo_explicito_ignora_cascada(self, fake_vision):
        client = fake_vision(FakeClient(rotos=["forzado/x"]))
        with pytest.raises(Exception):
            lg.chat_vision("prompt", [], model="forzado/x")
        assert client.llamadas == ["forzado/x"]

    def test_todos_fallan_propaga(self, fake_vision):
        client = fake_vision(FakeClient(rotos=["primario/phi", "respaldo/llama"]))
        with pytest.raises(Exception):
            lg.chat_vision("prompt", [])
        assert client.llamadas == ["primario/phi", "respaldo/llama"]
