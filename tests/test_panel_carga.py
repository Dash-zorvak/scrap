"""Tests para dashboard/panel_carga.py — pestañas (sin aprobación manual)."""
import inspect
import os
import re

import pytest


def _leer_fuente():
    """Lee el fuente de panel_carga.py como string."""
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                        "dashboard", "panel_carga.py")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_panel_carga_no_tiene_pestanas_aprobacion():
    """panel_carga.py ya NO define pestañas de aprobación manual."""
    src = _leer_fuente()
    assert "Aprobar temas" not in src


def test_panel_carga_no_importa_render_revisor():
    """panel_carga.py ya NO importa render_revisor_temas."""
    src = _leer_fuente()
    assert "render_revisor_temas" not in src


def test_panel_carga_tres_pestanas():
    """panel_carga.py define exactamente 3 pestañas: cargar, JSON, editor."""
    src = _leer_fuente()
    assert "Cargar contenido" in src
    assert "Importar JSON" in src
    assert "Editar base de datos" in src


def test_panel_carga_importa_config():
    """panel_carga.py importa TIKTOK_DB y EXTERNOS_DB de Config."""
    src = _leer_fuente()
    assert "TIKTOK_DB" in src
    assert "EXTERNOS_DB" in src


def test_panel_carga_orden_pestanas():
    """Las pestañas están en el orden: cargar, JSON, editor."""
    src = _leer_fuente()
    idx_cargar = src.index("Cargar contenido")
    idx_json = src.index("Importar JSON")
    idx_editar = src.index("Editar base de datos")
    assert idx_cargar < idx_json < idx_editar
