"""Tests para dashboard/dash_temas.py — parametrización y controles."""
import inspect
import os

import pytest


def _leer_fuente():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                        "dashboard", "dash_temas.py")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_render_revisor_temas_firma_parametros():
    """render_revisor_temas acepta tabla, col_id, col_texto, col_parent."""
    from dashboard.dash_temas import render_revisor_temas
    sig = inspect.signature(render_revisor_temas)
    params = list(sig.parameters.keys())
    assert "tabla" in params, f"Falta 'tabla' en firma: {params}"
    assert "col_id" in params, f"Falta 'col_id' en firma: {params}"
    assert "col_texto" in params, f"Falta 'col_texto' en firma: {params}"
    assert "col_parent" in params, f"Falta 'col_parent' en firma: {params}"


def test_render_revisor_temas_defaults_facebook():
    """Valores por defecto de tabla/col_id/col_texto coinciden con Facebook."""
    from dashboard.dash_temas import render_revisor_temas
    sig = inspect.signature(render_revisor_temas)
    assert sig.parameters["tabla"].default == "fb_comments"
    assert sig.parameters["col_id"].default == "comment_id"
    assert sig.parameters["col_texto"].default == "message"
    assert sig.parameters["col_parent"].default is None


def test_render_revisor_temas_fuente_contiene_parametros():
    """El código fuente usa los parámetros en el SQL, no literales de Facebook."""
    from dashboard.dash_temas import render_revisor_temas
    src = inspect.getsource(render_revisor_temas)
    assert "tabla" in src and "col_id" in src and "col_texto" in src
    assert "{col_id}" in src
    assert "{tabla}" in src
    assert "{col_texto}" in src


def test_render_revisor_temas_sql_usa_parametros():
    """El SQL dentro de render_revisor_temas usa f-strings con tabla/col_id/col_texto."""
    from dashboard.dash_temas import render_revisor_temas
    src = inspect.getsource(render_revisor_temas)
    assert "f\"SELECT" in src or "f'" in src
    assert "{col_id}" in src
    assert "{tabla}" in src
    assert "{col_texto}" in src


def test_dash_temas_solo_selector_tema():
    """El código solo incluye selector de tema, no controles manuales de postura/emoción."""
    src = _leer_fuente()
    assert "selectbox" in src
    assert "_OPCIONES" in src
    assert "guardar_aprobacion" in src


def test_dash_temas_no_tiene_entidad_control():
    """El código ya no incluye control de entidad/subtema específico."""
    src = _leer_fuente()
    assert "entidad" not in src.lower() or "ENTIDAD" not in src
    assert "subtema_especifico" not in src


def test_dash_temas_no_tiene_relevancia_control():
    """El código ya no incluye control de relevancia al post."""
    src = _leer_fuente()
    assert "relevancia_al_post" not in src
    assert "RELEVANCIAS_POST" not in src


def test_dash_temas_no_tiene_postura_selector():
    """El código ya no incluye selector manual de postura."""
    src = _leer_fuente()
    assert "_POSTURA_OPCIONES" not in src


def test_dash_temas_tiene_contexto_padre():
    """El código incluye lógica para mostrar comentario padre."""
    src = _leer_fuente()
    assert "padre" in src.lower() or "parent" in src.lower()
    assert "_obtener_texto_padre" in src
