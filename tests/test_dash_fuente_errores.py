"""Regresión D8: manejo de excepciones en lecturas de DB de dash_fuente.py.

Verifica que las 5 funciones públicas + sugerir_temas_pendientes_cacheado
capturen excepciones de DB, logueen con logger.exception (nivel ERROR),
NO propaguen la excepción y devuelvan su "vacío seguro" habitual.
"""

import sys
import os
import logging
import pandas as pd
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))

import dashboard.dash_fuente as df
import dashboard.dash_inteligencia as di


class TestDashFuenteErroresDB:
    """Tests de regresión D8: excepciones en lecturas de DB no crashean."""

    def _mock_streamlit_warning(self, monkeypatch):
        """Mockea st.warning para que no falle si Streamlit no está inicializado."""
        mock_warning = MagicMock()
        monkeypatch.setattr(df.st, "warning", mock_warning)
        return mock_warning

    def _mock_dash_inteligencia_warning(self, monkeypatch):
        """Mockea st.warning en dash_inteligencia."""
        mock_warning = MagicMock()
        monkeypatch.setattr(di.st, "warning", mock_warning)
        return mock_warning

    # ── _cargar_comentarios_fb ──────────────────────────────────────────────
    def test_cargar_comentarios_fb_excepcion_db_loguea_y_devuelve_df_vacio(self, monkeypatch, caplog):
        """Falla en sqlite3.connect → logger.exception + st.warning + df vacío."""
        mock_warning = self._mock_streamlit_warning(monkeypatch)

        def raise_connect(*args, **kwargs):
            raise Exception("db caida")

        monkeypatch.setattr("sqlite3.connect", raise_connect)

        with caplog.at_level(logging.ERROR, logger="dash_fuente"):
            result = df._cargar_comentarios_fb("2024-01-01", "2024-01-31")

        # No debe propagar la excepción
        assert isinstance(result, pd.DataFrame)
        assert result.empty
        assert list(result.columns) == df._COLUMNAS_COMENTARIOS

        # logger.exception → nivel ERROR
        assert any("Fallo leyendo fb_comments para _cargar_comentarios_fb" in r.message for r in caplog.records)
        assert any(r.levelno == logging.ERROR for r in caplog.records)

        # st.warning llamado
        mock_warning.assert_called_once()

    # ── _cargar_comentarios_tk ──────────────────────────────────────────────
    def test_cargar_comentarios_tk_excepcion_db_loguea_y_devuelve_df_vacio(self, monkeypatch, caplog):
        """Falla en sqlite3.connect → logger.exception + st.warning + df vacío."""
        mock_warning = self._mock_streamlit_warning(monkeypatch)

        def raise_connect(*args, **kwargs):
            raise Exception("db caida")

        monkeypatch.setattr("sqlite3.connect", raise_connect)

        with caplog.at_level(logging.ERROR, logger="dash_fuente"):
            result = df._cargar_comentarios_tk("2024-01-01", "2024-01-31")

        assert isinstance(result, pd.DataFrame)
        assert result.empty
        assert list(result.columns) == df._COLUMNAS_COMENTARIOS

        assert any("Fallo leyendo comments/videos de TikTok para _cargar_comentarios_tk" in r.message for r in caplog.records)
        assert any(r.levelno == logging.ERROR for r in caplog.records)
        mock_warning.assert_called_once()

    # ── _dist_desde_fb_sentimiento ──────────────────────────────────────────
    def test_dist_desde_fb_sentimiento_excepcion_db_loguea_y_devuelve_none(self, monkeypatch, caplog):
        """Falla en sqlite3.connect → logger.exception + st.warning + None."""
        mock_warning = self._mock_streamlit_warning(monkeypatch)

        def raise_connect(*args, **kwargs):
            raise Exception("db caida")

        monkeypatch.setattr("sqlite3.connect", raise_connect)

        with caplog.at_level(logging.ERROR, logger="dash_fuente"):
            result = df._dist_desde_fb_sentimiento(["post1", "post2"], "dummy.db")

        assert result is None

        assert any("Fallo leyendo fb_sentimiento para _dist_desde_fb_sentimiento" in r.message for r in caplog.records)
        assert any(r.levelno == logging.ERROR for r in caplog.records)
        mock_warning.assert_called_once()

    # ── _dist_desde_tiktok_sentimiento ──────────────────────────────────────
    def test_dist_desde_tiktok_sentimiento_excepcion_db_loguea_y_devuelve_none(self, monkeypatch, caplog):
        """Falla en sqlite3.connect → logger.exception + st.warning + None."""
        mock_warning = self._mock_streamlit_warning(monkeypatch)

        def raise_connect(*args, **kwargs):
            raise Exception("db caida")

        monkeypatch.setattr("sqlite3.connect", raise_connect)

        with caplog.at_level(logging.ERROR, logger="dash_fuente"):
            result = df._dist_desde_tiktok_sentimiento(["vid1", "vid2"], "dummy.db")

        assert result is None

        assert any("Fallo leyendo tiktok_sentimiento para _dist_desde_tiktok_sentimiento" in r.message for r in caplog.records)
        assert any(r.levelno == logging.ERROR for r in caplog.records)
        mock_warning.assert_called_once()

    # ── mapa_categoria_posts ────────────────────────────────────────────────
    def test_mapa_categoria_posts_excepcion_db_loguea_y_devuelve_dict_vacio(self, monkeypatch, caplog):
        """Falla en sqlite3.connect → logger.exception + st.warning + {}."""
        mock_warning = self._mock_streamlit_warning(monkeypatch)

        def raise_connect(*args, **kwargs):
            raise Exception("db caida")

        monkeypatch.setattr("sqlite3.connect", raise_connect)

        with caplog.at_level(logging.ERROR, logger="dash_fuente"):
            result = df.mapa_categoria_posts("dummy.db")

        assert result == {}

        assert any("Fallo leyendo post_categorias para mapa_categoria_posts" in r.message for r in caplog.records)
        assert any(r.levelno == logging.ERROR for r in caplog.records)
        mock_warning.assert_called_once()


class TestDashInteligenciaErrores:
    """Tests de regresión D8: sugerir_temas_pendientes_cacheado (PR #106)."""

    def _mock_dash_inteligencia_warning(self, monkeypatch):
        """Mockea st.warning en dash_inteligencia."""
        mock_warning = MagicMock()
        monkeypatch.setattr(di.st, "warning", mock_warning)
        return mock_warning

    def test_sugerir_temas_pendientes_excepcion_primer_except_loguea_y_devuelve_lista_vacia(self, monkeypatch, caplog):
        """Falla en la primera consulta (ordenar por fecha) → logger.warning + st.warning + []."""
        mock_warning = self._mock_dash_inteligencia_warning(monkeypatch)

        def raise_connect(*args, **kwargs):
            raise Exception("db caida")

        monkeypatch.setattr("sqlite3.connect", raise_connect)

        with caplog.at_level(logging.WARNING, logger="dash_inteligencia"):
            result = di.sugerir_temas_pendientes_cacheado("dummy.db")

        assert result == []

        # Primer except: logger.warning (no exception)
        assert any("No se pudo ordenar fb_comments por fecha" in r.message for r in caplog.records)
        assert any(r.levelno == logging.WARNING for r in caplog.records)

        # st.warning llamado en el segundo except (el que devuelve [])
        mock_warning.assert_called_once()

    def test_sugerir_temas_pendientes_excepcion_segundo_except_loguea_exception_y_devuelve_lista_vacia(self, monkeypatch, caplog):
        """Primera consulta OK, falla la segunda (sin orden) → logger.exception + st.warning + []."""
        mock_warning = self._mock_dash_inteligencia_warning(monkeypatch)

        call_count = {"n": 0}

        def mock_connect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                # Primera llamada: devuelve conn que falla en execute
                mock_conn = MagicMock()
                mock_conn.execute.side_effect = Exception("db caida en execute")
                mock_conn.close = MagicMock()
                return mock_conn
            # Segunda llamada: falla en connect
            raise Exception("db caida en connect 2")

        monkeypatch.setattr("sqlite3.connect", mock_connect)

        with caplog.at_level(logging.ERROR, logger="dash_inteligencia"):
            result = di.sugerir_temas_pendientes_cacheado("dummy.db")

        assert result == []

        # Segundo except: logger.exception (nivel ERROR)
        assert any("Fallo leyendo fb_comments para sugerir temas pendientes" in r.message for r in caplog.records)
        assert any(r.levelno == logging.ERROR for r in caplog.records)

        # st.warning llamado
        mock_warning.assert_called_once()