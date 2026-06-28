"""Tests del fix de posts duplicados (URL share vs permalink).

El mismo post de Facebook subido con dos enlaces distintos (permalink vs
'.../share/p/XXXX') ya no debe guardarse dos veces (ingesta), y el script de
limpieza debe quitar SOLO las copias exactas sin tocar comentarios legitimos
(misma persona comentando en posts realmente distintos), conservando el 100%% de
los comentarios distintos.
"""
import sqlite3

from dashboard._generar_id import (
    firma_contenido,
    resolver_id_post,
    generar_id_comentario,
)
from dashboard.dedupe_posts import deduplicar, grupos_duplicados, elegir_canonico


def _datos(url, msg="Hoy gire instrucciones para Red Vial",
           page="Gustavo Acevedo", fecha="2026-06-22 00:00:00"):
    return {
        "plataforma": "facebook",
        "page_name": page,
        "created_time": fecha,
        "message": msg,
        "post_url": url,
    }


class TestFirmaContenido:
    def test_misma_firma_distinta_url(self):
        a = firma_contenido(_datos("https://fb.com/posts/123"))
        b = firma_contenido(_datos("https://fb.com/share/p/XXXX/"))
        assert a == b and a != ""

    def test_distinto_texto_distinta_firma(self):
        a = firma_contenido(_datos("u1", msg="Texto A"))
        b = firma_contenido(_datos("u1", msg="Texto B"))
        assert a != b

    def test_sin_texto_firma_vacia(self):
        assert firma_contenido(_datos("u1", msg="")) == ""

    def test_fecha_normalizada(self):
        a = firma_contenido(_datos("u1", fecha="2026-06-22 00:00:00.000000"))
        b = firma_contenido(_datos("u2", fecha="2026-06-22T00:00:00"))
        assert a == b


class TestResolverIdPost:
    def test_reusa_id_por_contenido_aunque_cambie_url(self):
        ids, firmas = set(), {}
        pid1 = resolver_id_post(_datos("https://fb.com/posts/123"), ids, firmas)
        ids.add(pid1)
        pid2 = resolver_id_post(_datos("https://fb.com/share/p/XXXX/"), ids, firmas)
        assert pid2 == pid1

    def test_posts_distintos_no_se_fusionan(self):
        ids, firmas = set(), {}
        pid1 = resolver_id_post(_datos("u1", msg="Post uno"), ids, firmas)
        ids.add(pid1)
        pid2 = resolver_id_post(_datos("u2", msg="Post dos"), ids, firmas)
        assert pid2 != pid1

    def test_sin_texto_cae_a_url(self):
        ids, firmas = set(), {}
        pid1 = resolver_id_post(_datos("u1", msg=""), ids, firmas)
        ids.add(pid1)
        pid_misma = resolver_id_post(_datos("u1", msg=""), ids, firmas)
        assert pid_misma == pid1


def _crear_db(tmp_path):
    db = str(tmp_path / "facebook.db")
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE fb_posts (post_id TEXT PRIMARY KEY, page_name TEXT, "
        "created_time TEXT, message TEXT, post_url TEXT)"
    )
    conn.execute(
        "CREATE TABLE fb_comments (comment_id TEXT PRIMARY KEY, post_id TEXT, "
        "message TEXT, author_name TEXT)"
    )
    conn.execute("CREATE TABLE tema_aprobaciones (comment_id TEXT PRIMARY KEY, tema TEXT)")
    return conn


def _post(conn, pid, url, page="Gustavo Acevedo",
          fecha="2026-06-22 00:00:00", msg="Hoy gire instrucciones"):
    conn.execute("INSERT INTO fb_posts VALUES (?,?,?,?,?)", (pid, page, fecha, msg, url))


def _com(conn, pid, idx, texto, autor):
    cid = generar_id_comentario(pid, texto, idx)
    conn.execute("INSERT INTO fb_comments VALUES (?,?,?,?)", (cid, pid, texto, autor))
    return cid


class TestDeduplicar:
    def test_fusiona_post_duplicado(self, tmp_path):
        conn = _crear_db(tmp_path)
        _post(conn, "MAN_0002_aaaa", "https://fb.com/posts/123")
        _post(conn, "MAN_0003_bbbb", "https://fb.com/share/p/XXXX/")
        for pid in ("MAN_0002_aaaa", "MAN_0003_bbbb"):
            _com(conn, pid, 0, "Mire por aqui en la colonia", "Carlos Lopez")
            _com(conn, pid, 1, "Gracias alcalde", "Ana")
        conn.commit()

        res = deduplicar(conn)
        assert res["posts_eliminados"] == 1
        assert conn.execute("SELECT COUNT(*) FROM fb_posts").fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM fb_comments WHERE message LIKE 'Mire por aqui%'"
        ).fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM fb_comments").fetchone()[0] == 2
        conn.close()

    def test_conserva_canonico_permalink(self, tmp_path):
        conn = _crear_db(tmp_path)
        # Mismo numero de comentarios -> el permalink desempata como canonico.
        _post(conn, "MAN_0002_aaaa", "https://fb.com/posts/123")
        _post(conn, "MAN_0003_bbbb", "https://fb.com/share/p/XXXX/")
        _com(conn, "MAN_0002_aaaa", 0, "Comentario comun", "Ana")
        _com(conn, "MAN_0003_bbbb", 0, "Comentario comun", "Ana")
        conn.commit()
        assert elegir_canonico(conn, ["MAN_0003_bbbb", "MAN_0002_aaaa"]) == "MAN_0002_aaaa"
        conn.close()

    def test_canonico_es_el_de_mas_comentarios(self, tmp_path):
        conn = _crear_db(tmp_path)
        # El post con MAS comentarios gana, aunque sea el enlace de compartir.
        _post(conn, "MAN_0002_aaaa", "https://fb.com/posts/123")
        _post(conn, "MAN_0003_bbbb", "https://fb.com/share/p/XXXX/")
        _com(conn, "MAN_0002_aaaa", 0, "Uno", "Ana")
        _com(conn, "MAN_0003_bbbb", 0, "Uno", "Ana")
        _com(conn, "MAN_0003_bbbb", 1, "Dos", "Beto")
        conn.commit()
        assert elegir_canonico(conn, ["MAN_0002_aaaa", "MAN_0003_bbbb"]) == "MAN_0003_bbbb"
        conn.close()

    def test_comentario_unico_del_duplicado_se_conserva(self, tmp_path):
        conn = _crear_db(tmp_path)
        # Igualamos conteos para que el permalink (MAN_0002) sea el canonico y
        # comprobar que el comentario unico del duplicado se mueve al canonico.
        _post(conn, "MAN_0002_aaaa", "https://fb.com/posts/123")
        _post(conn, "MAN_0003_bbbb", "https://fb.com/share/p/XXXX/")
        _com(conn, "MAN_0002_aaaa", 0, "Comentario comun", "Ana")
        _com(conn, "MAN_0002_aaaa", 1, "Otro comentario", "Beto")
        _com(conn, "MAN_0003_bbbb", 0, "Comentario comun", "Ana")
        _com(conn, "MAN_0003_bbbb", 1, "Solo en la copia", "Carlos")
        conn.commit()
        deduplicar(conn)
        row = conn.execute(
            "SELECT post_id FROM fb_comments WHERE message='Solo en la copia'"
        ).fetchone()
        assert row is not None and row[0] == "MAN_0002_aaaa"
        # 4 originales - 1 copia exacta eliminada = 3 comentarios distintos
        assert conn.execute("SELECT COUNT(*) FROM fb_comments").fetchone()[0] == 3
        conn.close()

    def test_no_toca_posts_distintos(self, tmp_path):
        conn = _crear_db(tmp_path)
        _post(conn, "MAN_0011_aaaa", "u1", msg="Post sobre agua potable")
        _post(conn, "MAN_0036_bbbb", "u2", msg="Post sobre calles y baches")
        _com(conn, "MAN_0011_aaaa", 0, "Excelente", "Yolanda")
        _com(conn, "MAN_0036_bbbb", 0, "Excelente", "Yolanda")
        conn.commit()
        res = deduplicar(conn)
        assert res["posts_eliminados"] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM fb_comments WHERE message='Excelente'"
        ).fetchone()[0] == 2
        conn.close()

    def test_remapea_aprobacion_del_duplicado(self, tmp_path):
        conn = _crear_db(tmp_path)
        _post(conn, "MAN_0002_aaaa", "https://fb.com/posts/123")
        _post(conn, "MAN_0003_bbbb", "https://fb.com/share/p/XXXX/")
        _com(conn, "MAN_0002_aaaa", 0, "Mire por aqui", "Carlos")
        cid_dup = _com(conn, "MAN_0003_bbbb", 0, "Mire por aqui", "Carlos")
        conn.execute("INSERT INTO tema_aprobaciones VALUES (?,?)", (cid_dup, "obras_servicios"))
        conn.commit()
        deduplicar(conn)
        fila = conn.execute("SELECT comment_id FROM tema_aprobaciones").fetchone()
        assert fila is not None
        existe = conn.execute(
            "SELECT 1 FROM fb_comments WHERE comment_id=?", (fila[0],)
        ).fetchone()
        assert existe is not None
        conn.close()

    def test_grupos_duplicados_detecta(self, tmp_path):
        conn = _crear_db(tmp_path)
        _post(conn, "MAN_0002_aaaa", "https://fb.com/posts/123")
        _post(conn, "MAN_0003_bbbb", "https://fb.com/share/p/XXXX/")
        _post(conn, "MAN_0009_cccc", "u9", msg="Otro post totalmente distinto")
        conn.commit()
        grupos = grupos_duplicados(conn)
        assert len(grupos) == 1
        assert set(grupos[0]) == {"MAN_0002_aaaa", "MAN_0003_bbbb"}
        conn.close()
