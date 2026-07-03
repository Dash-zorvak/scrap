"""Tests de regresión para panel_carga.

Verifica que la nueva pestaña "✅ Aprobar temas" invoca
render_revisor_temas(FACEBOOK_DB).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))

import dashboard.panel_carga as panel_carga


class TestPanelCargaAprobarTemasTab:
    """Test que la pestaña '✅ Aprobar temas' existe y llama a render_revisor_temas."""

    def test_panel_carga_tiene_tres_tabs_con_aprobar_temas(self):
        """panel_carga debe tener 3 tabs: Cargar, Editor, Aprobar temas."""
        # Verificar que el módulo importa correctamente las dependencias
        assert hasattr(panel_carga, "render_revisor_temas"), (
            "panel_carga debe importar render_revisor_temas de dash_temas"
        )
        assert hasattr(panel_carga, "FACEBOOK_DB"), (
            "panel_carga debe importar FACEBOOK_DB de config"
        )

    def test_render_revisor_temas_llamada_con_facebook_db_en_codigo_fuente(self):
        """Verifica que el código fuente de panel_carga llama a
        render_revisor_temas(FACEBOOK_DB) en la tercera pestaña."""
        import inspect
        source = inspect.getsource(panel_carga)

        # Verificar que existe la tercer pestaña con el nombre correcto
        assert "✅ Aprobar temas" in source, (
            "Falta la pestaña '✅ Aprobar temas' en panel_carga"
        )

        # Verificar que se llama render_revisor_temas con FACEBOOK_DB
        assert "render_revisor_temas(FACEBOOK_DB)" in source, (
            "panel_carga debe llamar render_revisor_temas(FACEBOOK_DB) "
            "en la pestaña '✅ Aprobar temas'"
        )

        # Verificar que NO se renombraron ni reordenaron las otras dos tabs
        assert "📥 Cargar contenido" in source, "Falta pestaña 'Cargar contenido'"
        assert "🛠️ Editar base de datos / Medalla" in source, "Falta pestaña 'Editar base de datos / Medalla'"

        # Verificar el orden: Cargar, Editor, Aprobar
        cargar_idx = source.index("📥 Cargar contenido")
        editor_idx = source.index("🛠️ Editar base de datos / Medalla")
        aprobar_idx = source.index("✅ Aprobar temas")
        assert cargar_idx < editor_idx < aprobar_idx, (
            "El orden de las pestañas debe ser: Cargar contenido, "
            "Editar base de datos / Medalla, Aprobar temas"
        )

    def test_imports_correctos_en_panel_carga(self):
        """Verifica que panel_carga importa lo necesario."""
        import inspect
        source = inspect.getsource(panel_carga)

        assert "from dashboard.dash_temas import render_revisor_temas" in source, (
            "Falta importar render_revisor_temas de dash_temas"
        )
        assert "from dashboard.config import FACEBOOK_DB" in source, (
            "Falta importar FACEBOOK_DB de config"
        )