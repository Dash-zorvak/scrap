"""Tests de regresión para dash_temas.

Verifica que render_temas_emergentes ya no invoca controles de aprobación
(la funcionalidad se movió a panel_carga.py bajo la pestaña "✅ Aprobar temas").

Verifica que render_revisor_temas envuelve la llamada a sugerir_temas_pendientes_cacheado
con st.spinner para mostrar feedback visual mientras la IA genera sugerencias.
"""

import sys
import os
import inspect

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))

from dashboard.dash_temas import render_temas_emergentes, render_revisor_temas


class TestRenderTemasEmergentesNoApproval:
    """Test que render_temas_emergentes no incluye controles de aprobación."""

    def test_render_temas_emergentes_no_llama_render_revisor_temas(self, monkeypatch):
        """render_temas_emergentes no debe invocar render_revisor_temas internamente."""
        calls = []

        def mock_render_revisor(db_path):
            calls.append(db_path)

        monkeypatch.setattr("dashboard.dash_temas.render_revisor_temas", mock_render_revisor)

        # Mockear las dependencias de BD en el MÓDULO donde se usan (dash_temas)
        monkeypatch.setattr("dashboard.dash_temas.cargar_temas_universo", lambda db_path, **kw: [])
        monkeypatch.setattr("dashboard.dash_temas.resumen_revision", lambda db_path, **kw: {
            "total_aprobaciones": 0, "aprobados": 0, "sin_tema": 0, "pendientes": 0
        })
        monkeypatch.setattr("dashboard.dash_temas.resumen_cobertura_universo", lambda db_path, total_comentarios, **kw: {
            "clasificados": 0, "total_comentarios": 0, "sin_clasificar": 0
        })
        monkeypatch.setattr("dashboard.dash_temas._contar_comentarios", lambda db_path, **kw: 0)

        # Llamar a la función
        render_temas_emergentes(":memory:")

        # Verificar que NO se llamó a render_revisor_temas
        assert calls == [], (
            "render_temas_emergentes invocó render_revisor_temas, "
            "pero debería haber movido esa funcionalidad a panel_carga.py"
        )

    def test_render_temas_emergentes_no_tiene_expander_aprobar(self):
        """Verifica que el código fuente de render_temas_emergentes no contiene
        referencias al expander de aprobación."""
        source = inspect.getsource(render_temas_emergentes)

        # No debe contener el expander de aprobación
        assert "Revisar y aprobar temas" not in source, (
            "render_temas_emergentes aún contiene el texto del expander de aprobación"
        )
        assert "st.expander" not in source, (
            "render_temas_emergentes no debería usar st.expander (ese código está en render_revisor_temas)"
        )
        # No debe llamar a render_revisor_temas
        assert "render_revisor_temas" not in source, (
            "render_temas_emergentes no debería referenciar render_revisor_temas"
        )


class TestRenderRevisorTemasExists:
    """Test que render_revisor_temas existe y es pública."""

    def test_render_revisor_temas_existe_y_es_publica(self):
        """render_revisor_temas debe ser una función pública importable."""
        assert callable(render_revisor_temas), "render_revisor_temas debe ser callable"
        assert render_revisor_temas.__name__ == "render_revisor_temas"
        # No empieza con _ (es pública)
        assert not render_revisor_temas.__name__.startswith("_"), (
            "render_revisor_temas debe ser pública (no empezar con _)"
        )


class TestContarComentariosPeriodo:
    """Tests de _contar_comentarios con y sin filtro de período.

    Usa DB SQLite temporal real (no mocks) para el camino sin período,
    y monkeypatch de cargar_comentarios_periodo para el camino con período.
    """

    def test_sin_ini_fin_cuenta_historicos(self):
        """Sin ini/fin debe contar todos los comentarios con mensaje no vacío."""
        import tempfile
        import sqlite3
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            conn = sqlite3.connect(path)
            conn.execute("CREATE TABLE fb_comments (comment_id TEXT, post_id TEXT, message TEXT)")
            conn.execute("INSERT INTO fb_comments VALUES ('c1', 'p1', 'hola')")
            conn.execute("INSERT INTO fb_comments VALUES ('c2', 'p2', '')")
            conn.execute("INSERT INTO fb_comments VALUES ('c3', 'p3', NULL)")
            conn.commit()
            conn.close()
            from dashboard.dash_temas import _contar_comentarios
            n = _contar_comentarios(path)
            assert n == 1, "solo c1 tiene mensaje no vacio"
        finally:
            os.unlink(path)

    def test_con_ini_fin_delega_a_cargar_comentarios_periodo(self, monkeypatch):
        """Con ini/fin debe delegar en cargar_comentarios_periodo y contar mensajes."""
        import pandas as pd
        df = pd.DataFrame({
            "comment_id": ["c1", "c2", "c3"],
            "message": ["hola", "", None],
            "post_id": ["p1", "p2", "p3"],
        })
        calls = []

        def mock_cargar_periodo(ini, fin, plataforma, db_path):
            calls.append((ini, fin, plataforma, db_path))
            return df

        monkeypatch.setattr("dashboard.dash_temas.cargar_comentarios_periodo", mock_cargar_periodo)
        from dashboard.dash_temas import _contar_comentarios
        n = _contar_comentarios("dummy.db", ini="2024-01-01", fin="2024-01-31")
        assert n == 1, "solo c1 tiene mensaje no vacio"
        assert len(calls) == 1
        assert calls[0] == ("2024-01-01", "2024-01-31", "Facebook", "dummy.db")


class TestRenderRevisorTemasSpinner:
    """Test que render_revisor_temas envuelve la llamada IA con st.spinner."""

    def test_render_revisor_temas_tiene_spinner_en_codigo_fuente(self):
        """Verifica que el código fuente de render_revisor_temas contiene
        st.spinner envolviendo la llamada a sugerir_temas_pendientes_cacheado."""
        source = inspect.getsource(render_revisor_temas)

        # Debe contener st.spinner con el mensaje apropiado
        assert "st.spinner" in source, (
            "render_revisor_temas debe usar st.spinner para mostrar feedback "
            "mientras la IA genera sugerencias"
        )
        assert "Generando sugerencias de tema y postura con IA" in source, (
            "st.spinner debe contener el mensaje 'Generando sugerencias de tema y postura con IA…'"
        )
        # La llamada a sugerir_temas_pendientes_cacheado debe estar dentro del bloque with st.spinner
        assert "sugerir_temas_pendientes_cacheado" in source, (
            "render_revisor_temas debe llamar a sugerir_temas_pendientes_cacheado"
        )