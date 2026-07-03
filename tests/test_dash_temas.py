"""Tests de regresión para dash_temas.

Verifica que render_temas_emergentes ya no invoca controles de aprobación
(la funcionalidad se movió a panel_carga.py bajo la pestaña "✅ Aprobar temas").
"""

import sys
import os

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
        monkeypatch.setattr("dashboard.dash_temas.cargar_temas_aprobados", lambda db_path: [])
        monkeypatch.setattr("dashboard.dash_temas.resumen_revision", lambda db_path, total_comentarios: {
            "total_aprobaciones": 0, "aprobados": 0, "sin_tema": 0, "pendientes": 0
        })
        monkeypatch.setattr("dashboard.dash_temas._contar_comentarios", lambda db_path: 0)

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
        import inspect
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