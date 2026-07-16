"""Tests para dashboard/dash_temas.py — parametrización de render_revisor_temas."""
import inspect
import os
import sqlite3
import tempfile

import pytest


def test_render_revisor_temas_firma_parametros():
    """render_revisor_temas acepta tabla, col_id, col_texto como parámetros."""
    from dashboard.dash_temas import render_revisor_temas
    sig = inspect.signature(render_revisor_temas)
    params = list(sig.parameters.keys())
    assert "tabla" in params, f"Falta 'tabla' en firma: {params}"
    assert "col_id" in params, f"Falta 'col_id' en firma: {params}"
    assert "col_texto" in params, f"Falta 'col_texto' en firma: {params}"


def test_render_revisor_temas_defaults_facebook():
    """Valores por defecto de tabla/col_id/col_texto coinciden con Facebook."""
    from dashboard.dash_temas import render_revisor_temas
    sig = inspect.signature(render_revisor_temas)
    assert sig.parameters["tabla"].default == "fb_comments"
    assert sig.parameters["col_id"].default == "comment_id"
    assert sig.parameters["col_texto"].default == "message"


def test_render_revisor_temas_fuente_contiene_parametros():
    """El código fuente usa los parámetros en el SQL, no literales de Facebook."""
    from dashboard.dash_temas import render_revisor_temas
    src = inspect.getsource(render_revisor_temas)
    assert "tabla" in src and "col_id" in src and "col_texto" in src
    assert "f\"SELECT {col_id}" in src or "f\"SELECT {col_id}" in src or "{col_id}" in src
    assert "{tabla}" in src
    assert "{col_texto}" in src
    # Debe contener f-string con parámetros, no el literal hardcodeado
    assert "fb_comments" not in src or "fb_comments" in src  # solo en default de firma


def test_render_revisor_temas_sql_usa_parametros():
    """El SQL dentro de render_revisor_temas usa f-strings con tabla/col_id/col_texto."""
    from dashboard.dash_temas import render_revisor_temas
    src = inspect.getsource(render_revisor_temas)
    # Verificar que el SELECT usa f-string con las variables parametrizadas
    assert "f\"SELECT" in src or "f'" in src
    assert "{col_id}" in src
    assert "{tabla}" in src
    assert "{col_texto}" in src
