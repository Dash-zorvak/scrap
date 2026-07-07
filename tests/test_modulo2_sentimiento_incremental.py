import os
import sqlite3
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dashboard import modulo2_sentimiento as m2


def _crear_db_facebook(path, comentarios):
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE fb_comments (comment_id TEXT PRIMARY KEY, post_id TEXT, message TEXT)"
    )
    conn.executemany(
        "INSERT INTO fb_comments (comment_id, post_id, message) VALUES (?, ?, ?)",
        comentarios,
    )
    conn.commit()
    conn.close()


def _crear_db_tiktok(path, comentarios):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE comments (id TEXT PRIMARY KEY, video_id TEXT, text TEXT)")
    conn.executemany(
        "INSERT INTO comments (id, video_id, text) VALUES (?, ?, ?)",
        comentarios,
    )
    conn.commit()
    conn.close()


def _fake_clasificar_lote(textos):
    return [("POS", 0.9) for _ in textos], "reglas"


def test_fb_incremental_omite_solo_comentarios_ya_clasificados(tmp_path):
    db = str(tmp_path / "facebook.db")
    _crear_db_facebook(db, [("c1", "p1", "este es un comentario positivo lindo")])

    with patch.object(m2, "clasificar_lote", side_effect=_fake_clasificar_lote) as mock_clf:
        m2.analizar_sentimiento_facebook(db_path=db)

    assert mock_clf.call_count == 1
    assert len(mock_clf.call_args[0][0]) == 1

    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO fb_comments (comment_id, post_id, message) VALUES (?, ?, ?)",
        ("c2", "p1", "otro comentario nuevo tambien positivo"),
    )
    conn.commit()
    conn.close()

    with patch.object(m2, "clasificar_lote", side_effect=_fake_clasificar_lote) as mock_clf:
        m2.analizar_sentimiento_facebook(db_path=db)

    assert mock_clf.call_count == 1
    assert len(mock_clf.call_args[0][0]) == 1

    conn = sqlite3.connect(db)
    fila = conn.execute(
        "SELECT total_comentarios FROM fb_sentimiento WHERE post_id = 'p1'"
    ).fetchall()
    conn.close()
    assert len(fila) == 1
    assert fila[0][0] == 2


def test_fb_comments_columna_sentiment_se_llena_para_ambos_comentarios(tmp_path):
    db = str(tmp_path / "facebook.db")
    _crear_db_facebook(db, [
        ("c1", "p1", "comentario uno bastante largo para pasar el filtro"),
        ("c2", "p1", "comentario dos bastante largo para pasar el filtro"),
    ])

    with patch.object(m2, "clasificar_lote", side_effect=_fake_clasificar_lote):
        m2.analizar_sentimiento_facebook(db_path=db)

    conn = sqlite3.connect(db)
    filas = conn.execute("SELECT comment_id, sentiment FROM fb_comments").fetchall()
    conn.close()

    assert all(sentiment == "positivo" for _, sentiment in filas)


def test_tiktok_incremental_omite_solo_comentarios_ya_clasificados(tmp_path):
    db = str(tmp_path / "tiktok.db")
    _crear_db_tiktok(db, [("t1", "v1", "comentario de tiktok bastante largo y positivo")])

    with patch.object(m2, "clasificar_lote", side_effect=_fake_clasificar_lote) as mock_clf:
        m2.analizar_sentimiento_tiktok(db_path=db)

    assert mock_clf.call_count == 1
    assert len(mock_clf.call_args[0][0]) == 1

    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO comments (id, video_id, text) VALUES (?, ?, ?)",
        ("t2", "v1", "otro comentario de tiktok nuevo y tambien positivo"),
    )
    conn.commit()
    conn.close()

    with patch.object(m2, "clasificar_lote", side_effect=_fake_clasificar_lote) as mock_clf:
        m2.analizar_sentimiento_tiktok(db_path=db)

    assert mock_clf.call_count == 1
    assert len(mock_clf.call_args[0][0]) == 1

    conn = sqlite3.connect(db)
    fila = conn.execute(
        "SELECT total_comentarios FROM tiktok_sentimiento WHERE video_id = 'v1'"
    ).fetchall()
    conn.close()
    assert len(fila) == 1
    assert fila[0][0] == 2


def test_fb_sin_comentarios_nuevos_no_toca_agregado_existente(tmp_path):
    db = str(tmp_path / "facebook.db")
    _crear_db_facebook(db, [("c1", "p1", "comentario unico bastante largo para pasar el filtro")])

    with patch.object(m2, "clasificar_lote", side_effect=_fake_clasificar_lote):
        m2.analizar_sentimiento_facebook(db_path=db)

    with patch.object(m2, "clasificar_lote", side_effect=_fake_clasificar_lote) as mock_clf:
        resultado, motor = m2.analizar_sentimiento_facebook(db_path=db)

    assert mock_clf.call_count == 0
    assert resultado.empty
