"""Tests del cache de sugerencias de temas (mejora: revisión no bloqueante).

Verifican que aprobar un comentario no obligue a reclasificar a los demás con el
LLM: una vez cacheada la sugerencia de un comentario, no se vuelve a llamar al
modelo por él. El LLM se sustituye por un fake que cuenta sus invocaciones.
"""
import sqlite3

import dashboard.dash_inteligencia as di
import dashboard.topic_llm as tl


def _crear_db(tmp_path, comentarios):
    db = str(tmp_path / "fb.db")
    conn = sqlite3.connect(db)
    conn.execute(
        """
        CREATE TABLE fb_comments (
            comment_id TEXT PRIMARY KEY,
            post_id TEXT,
            message TEXT,
            created_time TEXT
        )
        """
    )
    for cid, msg in comentarios:
        conn.execute(
            "INSERT INTO fb_comments (comment_id, message, created_time) "
            "VALUES (?, ?, ?)",
            (cid, msg, "2026-06-01"),
        )
    conn.commit()
    conn.close()
    return db


def _fake_factory(registro):
    def fake_clasificar(textos, ejemplos=None):
        registro["llamadas"] += 1
        registro["textos"].append(list(textos))
        return [
            {"categoria": "no_aplica", "tono": "literal", "confianza": 0.5}
            for _ in textos
        ]
    return fake_clasificar


def test_cache_evita_reclasificar(tmp_path, monkeypatch):
    db = _crear_db(tmp_path, [
        ("c1", "la calle está en mal estado"),
        ("c2", "gracias por el parque nuevo"),
        ("c3", "cuándo arreglan el agua"),
    ])
    registro = {"llamadas": 0, "textos": []}
    monkeypatch.setattr(tl, "clasificar_temas_lote", _fake_factory(registro))

    cache = {}
    out1 = di.sugerir_temas_pendientes_cacheado(db, cache=cache)
    assert len(out1) == 3
    assert registro["llamadas"] == 1          # primera vez: clasifica los 3
    assert len(registro["textos"][0]) == 3

    # Segunda llamada con el MISMO cache: no debe reclasificar nada.
    out2 = di.sugerir_temas_pendientes_cacheado(db, cache=cache)
    assert len(out2) == 3
    assert registro["llamadas"] == 1          # sigue en 1: todo vino del cache


def test_cache_solo_clasifica_los_faltantes(tmp_path, monkeypatch):
    db = _crear_db(tmp_path, [("c1", "uno"), ("c2", "dos")])
    registro = {"llamadas": 0, "textos": []}
    monkeypatch.setattr(tl, "clasificar_temas_lote", _fake_factory(registro))

    # El cache ya trae c1 → solo debe clasificarse c2.
    cache = {
        "c1": {
            "comment_id": "c1", "texto": "uno", "sugerencia": "no_aplica",
            "sugerencia_label": "Sin tema", "tono": "literal", "confianza": 0.5,
        }
    }
    out = di.sugerir_temas_pendientes_cacheado(db, cache=cache)
    assert len(out) == 2
    assert registro["llamadas"] == 1
    assert registro["textos"] == [["dos"]]    # solo el faltante
