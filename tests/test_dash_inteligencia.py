import os
import sqlite3
import tempfile

import pytest

from dashboard.dash_inteligencia import (
    _construir_posts,
    cargar_alertas_cambridge,
    traducir_alerta,
    cargar_iq,
    cargar_zonas_resumen,
)


@pytest.fixture
def db_con_posts():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE fb_posts (
            post_id TEXT PRIMARY KEY,
            created_time TEXT,
            likes_count INTEGER DEFAULT 0,
            loves_count INTEGER DEFAULT 0,
            cares_count INTEGER DEFAULT 0,
            hahas_count INTEGER DEFAULT 0,
            wows_count INTEGER DEFAULT 0,
            sads_count INTEGER DEFAULT 0,
            angrys_count INTEGER DEFAULT 0,
            shares_count INTEGER DEFAULT 0,
            comments_count INTEGER DEFAULT 0,
            views_count INTEGER DEFAULT 0,
            topic_category TEXT,
            zona TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE fb_sentimiento (
            post_id TEXT PRIMARY KEY,
            pct_positivo REAL DEFAULT 0,
            pct_negativo REAL DEFAULT 0,
            total_comentarios INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE fb_comments (
            comment_id TEXT PRIMARY KEY,
            post_id TEXT,
            message TEXT,
            sentiment TEXT,
            zona TEXT
        )
    """)
    conn.commit()
    yield conn, db_path
    conn.close()
    os.close(db_fd)
    os.unlink(db_path)


def _insertar_post(conn, post_id, topic="", zona="", pct_pos=50, pct_neg=10,
                   created_time="2025-01-15", likes=10, loves=5, cares=2,
                   hahas=1, wows=1, sads=3, angrys=4, shares=2, comments=5,
                   views=200):
    conn.execute("""
        INSERT OR REPLACE INTO fb_posts
        (post_id, created_time, likes_count, loves_count, cares_count,
         hahas_count, wows_count, sads_count, angrys_count,
         shares_count, comments_count, views_count, topic_category, zona)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (post_id, created_time, likes, loves, cares, hahas, wows,
          sads, angrys, shares, comments, views, topic, zona))
    conn.execute("""
        INSERT OR REPLACE INTO fb_sentimiento
        (post_id, pct_positivo, pct_negativo, total_comentarios)
        VALUES (?, ?, ?, ?)
    """, (post_id, pct_pos, pct_neg, comments))


def _insertar_comentario(conn, comment_id, post_id, message, sentiment, zona):
    conn.execute("""
        INSERT OR REPLACE INTO fb_comments
        (comment_id, post_id, message, sentiment, zona)
        VALUES (?, ?, ?, ?, ?)
    """, (comment_id, post_id, message, sentiment, zona))


class TestConstruirPosts:
    def test_db_vacio(self):
        db_fd, db_path = tempfile.mkstemp(suffix=".db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE fb_posts (post_id TEXT)")
        conn.execute("CREATE TABLE fb_sentimiento (post_id TEXT)")
        conn.commit()
        conn.close()
        posts = _construir_posts(db_path)
        assert posts == []
        os.close(db_fd)
        os.unlink(db_path)

    def test_estructura_post(self, db_con_posts):
        conn, db_path = db_con_posts
        _insertar_post(conn, "post_1", topic="obras", zona="canton natividad",
                       pct_pos=80, pct_neg=20)
        conn.commit()
        posts = _construir_posts(db_path)
        assert len(posts) == 1
        p = posts[0]
        assert p["likes_count"] == 10
        assert p["topic_category"] == "obras"
        assert p["topic"] == "obras"
        assert p["zona"] == "canton natividad"
        assert p["zone"] == "canton natividad"
        assert p["sentiment"] == "positive"

    def test_sentiment_negativo(self, db_con_posts):
        conn, db_path = db_con_posts
        _insertar_post(conn, "post_1", pct_pos=20, pct_neg=80)
        conn.commit()
        posts = _construir_posts(db_path)
        assert posts[0]["sentiment"] == "negative"

    def test_sentiment_empate(self, db_con_posts):
        conn, db_path = db_con_posts
        _insertar_post(conn, "post_1", pct_pos=50, pct_neg=50)
        conn.commit()
        posts = _construir_posts(db_path)
        assert posts[0]["sentiment"] is None

    def test_sin_sentimiento(self, db_con_posts):
        conn, db_path = db_con_posts
        _insertar_post(conn, "post_1")
        conn.execute("DELETE FROM fb_sentimiento")
        conn.commit()
        posts = _construir_posts(db_path)
        assert len(posts) == 1
        assert posts[0]["sentiment"] is None


class TestCargarAlertasCambridge:
    def test_menos_de_5_posts(self, db_con_posts):
        conn, db_path = db_con_posts
        _insertar_post(conn, "post_1")
        conn.commit()
        alerts = cargar_alertas_cambridge(db_path)
        assert alerts == []

    def test_con_suficientes_posts(self, db_con_posts):
        conn, db_path = db_con_posts
        for i in range(6):
            _insertar_post(conn, f"post_{i}", pct_pos=60 - i * 10, pct_neg=10 + i * 10,
                           likes=20 - i * 2, sads=i, angrys=i)
        conn.commit()
        alerts = cargar_alertas_cambridge(db_path)
        assert isinstance(alerts, list)


class TestTraducirAlerta:
    def test_ici(self):
        alert = {"type": "ici", "severity": 3, "score": 2.5, "zona": "", "n_posts": 10}
        r = traducir_alerta(alert)
        assert "controversia" in r["titular"].lower() or "Sube" in r["titular"]
        assert r["color"] == "🔴"
        assert "Léelo así" in r["lectura"]

    def test_zdi_con_zona(self):
        alert = {"type": "zdi", "severity": 2, "score": 1.5,
                 "zona": "canton natividad", "n_posts": 8}
        r = traducir_alerta(alert)
        assert "canton natividad" in r["titular"]
        assert r["color"] == "🟡"
        assert "Léelo así" in r["lectura"]

    def test_sin_siglas(self):
        alert = {"type": "tai", "severity": 1, "score": 1.0,
                 "zona": "", "topic": "obras", "n_posts": 5}
        r = traducir_alerta(alert)
        assert "σ" not in r["titular"]
        assert "σ" not in r["lectura"]
        assert "TAI" not in r["titular"]

    def test_bajo(self):
        alert = {"type": "efi", "severity": 1, "score": 0.5, "zona": "", "n_posts": 3}
        r = traducir_alerta(alert)
        assert r["color"] == "🟢"

    def test_no_recomienda(self):
        alert = {"type": "ici", "severity": 3, "score": 2.0, "zona": "", "n_posts": 10}
        r = traducir_alerta(alert)
        assert "deberías" not in r["lectura"]
        assert "recomienda" not in r["lectura"]
        assert "qué hacer" not in r["lectura"]


class TestCargarIQ:
    def test_sin_posts(self, db_con_posts):
        conn, db_path = db_con_posts
        r = cargar_iq(db_path)
        assert r["iq"] is None
        assert r["cuadrante"] is None
        assert r["dimensiones"] == []

    def test_con_posts(self, db_con_posts):
        conn, db_path = db_con_posts
        for i in range(10):
            _insertar_post(conn, f"post_{i}", zona="zona_a",
                           pct_pos=70, pct_neg=30)
        conn.commit()
        r = cargar_iq(db_path)
        assert r["iq"] is not None
        assert isinstance(r["iq"], float)
        assert len(r["dimensiones"]) >= 5
        assert r["cuadrante"] is not None

    def test_dimensiones_ordenadas(self, db_con_posts):
        conn, db_path = db_con_posts
        for i in range(10):
            _insertar_post(conn, f"post_{i}", zona="zona_a",
                           pct_pos=70, pct_neg=30)
        conn.commit()
        r = cargar_iq(db_path)
        valores = [d["valor"] for d in r["dimensiones"]]
        assert valores == sorted(valores, reverse=True)


class TestCargarZonasResumen:
    def test_sin_zonas(self, db_con_posts):
        conn, db_path = db_con_posts
        r = cargar_zonas_resumen(db_path)
        assert r["apoyo"] == []
        assert r["enojo"] == []
        assert r["total_zonas"] == 0

    def test_agrupa_por_zona(self, db_con_posts):
        conn, db_path = db_con_posts
        _insertar_comentario(conn, "c1", "p1", "muy buena obra", "positivo", "colonia belen")
        _insertar_comentario(conn, "c2", "p1", "pésimo servicio", "negativo", "colonia belen")
        _insertar_comentario(conn, "c3", "p1", "pésimo", "negativo", "colonia belen")
        _insertar_comentario(conn, "c4", "p2", "todo bien", "positivo", "canton natividad")
        conn.commit()
        r = cargar_zonas_resumen(db_path)
        assert r["total_zonas"] == 2

    def test_enojo_alto(self, db_con_posts):
        conn, db_path = db_con_posts
        for i in range(5):
            _insertar_comentario(conn, f"c{i}", "p1", f"queja {i}", "negativo", "canton natividad")
        _insertar_comentario(conn, "c5", "p1", "ok", "positivo", "canton natividad")
        conn.commit()
        r = cargar_zonas_resumen(db_path)
        assert len(r["enojo"]) >= 1
        assert r["enojo"][0]["zona"] == "canton natividad"
        assert r["enojo"][0]["pct_negativos"] >= 50

    def test_apoyo_alto(self, db_con_posts):
        conn, db_path = db_con_posts
        for i in range(5):
            _insertar_comentario(conn, f"c{i}", "p1", f"feliz {i}", "positivo", "colonia belen")
        _insertar_comentario(conn, "c5", "p1", "mal", "negativo", "colonia belen")
        conn.commit()
        r = cargar_zonas_resumen(db_path)
        assert len(r["apoyo"]) >= 1
        assert r["apoyo"][0]["pct_negativos"] < 50

    def test_sin_columna_zona(self):
        db_fd, db_path = tempfile.mkstemp(suffix=".db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE fb_comments (comment_id TEXT, message TEXT)")
        conn.commit()
        conn.close()
        r = cargar_zonas_resumen(db_path)
        assert r["total_zonas"] == 0
        os.close(db_fd)
        os.unlink(db_path)
