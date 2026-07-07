"""Tests: _get_groq_client y _get_text_client refrescan cuando cambia api_key/base_url."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))

import dashboard.llm_groq as lg


class TestGroqClientRefresh:

    def teardown_method(self):
        lg._cliente = None
        lg._cliente_api_key = None
        lg._cliente_base_url = None
        lg._cliente_texto = None
        lg._cliente_texto_api_key = None
        lg._cliente_texto_base_url = None

    def test_key_cambia_nuevo_cliente(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "key-a")
        monkeypatch.setenv("LLM_BASE_URL", "https://integrate.api.nvidia.com/v1")
        c1 = lg._get_groq_client()
        assert c1 is not None

        monkeypatch.setenv("LLM_API_KEY", "key-b")
        c2 = lg._get_groq_client()
        assert c2 is not None
        assert c2 is not c1

    def test_misma_key_mismo_cliente(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "key-a")
        monkeypatch.setenv("LLM_BASE_URL", "https://integrate.api.nvidia.com/v1")
        lg._cliente = None  # fresh start
        c1 = lg._get_groq_client()
        c2 = lg._get_groq_client()
        assert c2 is c1

    def test_text_key_cambia_nuevo_cliente(self, monkeypatch):
        monkeypatch.setenv("LLM_TEXT_API_KEY", "text-key-a")
        monkeypatch.setenv("LLM_TEXT_BASE_URL", "https://opencode.ai/zen/v1")
        c1 = lg._get_text_client()
        assert c1 is not None

        monkeypatch.setenv("LLM_TEXT_API_KEY", "text-key-b")
        c2 = lg._get_text_client()
        assert c2 is not None
        assert c2 is not c1

    def test_text_misma_key_mismo_cliente(self, monkeypatch):
        monkeypatch.setenv("LLM_TEXT_API_KEY", "text-key-a")
        monkeypatch.setenv("LLM_TEXT_BASE_URL", "https://opencode.ai/zen/v1")
        lg._cliente_texto = None
        c1 = lg._get_text_client()
        c2 = lg._get_text_client()
        assert c2 is c1
