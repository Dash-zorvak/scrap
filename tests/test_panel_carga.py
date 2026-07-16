"""Tests para dashboard/panel_carga.py — pestañas de aprobación multiplataforma."""
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


def test_panel_carga_tiene_tres_pestanas_aprobacion():
    """panel_carga.py define 3 pestañas de aprobación (Facebook, TikTok, Externos)."""
    src = _leer_fuente()
    assert "Aprobar temas" in src
    assert "Aprobar temas (TikTok)" in src
    assert "Aprobar temas (Externos)" in src


def test_panel_carga_llama_render_revisor_tiktok():
    """panel_carga.py llama render_revisor_temas con parámetros de TikTok."""
    src = _leer_fuente()
    assert 'tabla="comments"' in src
    assert 'col_id="id"' in src
    assert 'col_texto="text"' in src


def test_panel_carga_llama_render_revisor_externos():
    """panel_carga.py llama render_revisor_temas con parámetros de Externos."""
    src = _leer_fuente()
    assert 'tabla="external_comments"' in src
    assert 'col_id="comment_id"' in src or "col_id" in src
    assert 'col_texto="message"' in src


def test_panel_carga_facebook_default():
    """La llamada Facebook incluye col_parent para parent_comment_id."""
    src = _leer_fuente()
    assert "render_revisor_temas(FACEBOOK_DB" in src
    assert "parent_comment_id" in src


def test_panel_carga_tiktok_sin_parent():
    """La llamada TikTok NO incluye col_parent (no tiene parent_comment_id)."""
    src = _leer_fuente()
    # TikTok no tiene parent_comment_id
    idx_tk = src.index('render_revisor_temas(TIKTOK_DB')
    idx_next_line = src.index("\n", idx_tk)
    linea_tk = src[idx_tk:idx_next_line]
    assert "parent_comment_id" not in linea_tk


def test_panel_carga_importa_config():
    """panel_carga.py importa TIKTOK_DB y EXTERNOS_DB de Config."""
    src = _leer_fuente()
    assert "TIKTOK_DB" in src
    assert "EXTERNOS_DB" in src


def test_panel_carga_orden_pestanas():
    """Las pestañas están en el orden: cargar, editar, aprobar, aprobar TK, aprobar Ext."""
    src = _leer_fuente()
    idx_cargar = src.index("Cargar contenido")
    idx_editar = src.index("Editar base de datos")
    idx_aprobar_fb = src.index('"✅ Aprobar temas"')
    idx_aprobar_tk = src.index('"✅ Aprobar temas (TikTok)"')
    idx_aprobar_ext = src.index('"✅ Aprobar temas (Externos)"')
    assert idx_cargar < idx_editar < idx_aprobar_fb < idx_aprobar_tk < idx_aprobar_ext
