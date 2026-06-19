"""Persistencia de paginas externas y guardado de posts externos.

Modulo independiente (no toca modulo5_externos.py) para:
  - Recordar nombres de paginas externas y reusarlos en futuras cargas.
  - Insertar posts y comentarios externos reales en externos.db.

Las tablas externas (external_posts, external_comments, external_sentimiento)
usan el MISMO esquema que dashboard/modulo5_externos.py para que el dashboard
(cargar_externos en app.py) las lea sin cambios. external_pages es la lista
persistente de paginas externas que el operador reutiliza al cargar contenido.
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import EXTERNOS_DB  # noqa: E402


def _resolver_db(db_path=None):
    """Permite override por argumento o env var (modo prueba usa externos_test.db)."""
    return db_path or os.getenv("EXTERNOS_DB", EXTERNOS_DB)


def asegurar_tablas_externas(db_path=None):
    """Crea las tablas externas si no existen (idempotente)."""
    db = _resolver_db(db_path)
    conn = sqlite3.connect(db)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS external_posts (
                post_id TEXT PRIMARY KEY,
                page_name TEXT,
                page_url TEXT,
                message TEXT,
                created_time DATETIME,
                total_reactions INTEGER DEFAULT 0,
                comments_count INTEGER DEFAULT 0,
                post_url TEXT,
                source TEXT DEFAULT 'manual_externo',
                scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS external_comments (
                comment_id TEXT PRIMARY KEY,
                post_id TEXT,
                message TEXT,
                author_name TEXT DEFAULT 'Anonymous',
                created_time DATETIME,
                scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS external_sentimiento (
                post_id TEXT PRIMARY KEY,
                total_comentarios INTEGER,
                pct_positivo REAL,
                pct_negativo REAL,
                pct_neutral REAL,
                score_sentimiento REAL,
                comentario_mas_negativo TEXT,
                comentario_mas_positivo TEXT
            );

            CREATE TABLE IF NOT EXISTS external_pages (
                name TEXT PRIMARY KEY,
                added_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
    finally:
        conn.close()


def listar_paginas_externas(db_path=None):
    """Devuelve la lista de nombres de paginas externas guardadas (orden alfabetico)."""
    db = _resolver_db(db_path)
    try:
        asegurar_tablas_externas(db)
        conn = sqlite3.connect(db)
        try:
            rows = conn.execute(
                "SELECT name FROM external_pages ORDER BY name COLLATE NOCASE"
            ).fetchall()
        finally:
            conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []


def agregar_pagina_externa(nombre, db_path=None):
    """Guarda un nombre de pagina externa para reusarlo despues. Idempotente."""
    nombre = (nombre or "").strip()
    if not nombre:
        return False
    db = _resolver_db(db_path)
    try:
        asegurar_tablas_externas(db)
        conn = sqlite3.connect(db)
        try:
            conn.execute(
                "INSERT OR IGNORE INTO external_pages (name) VALUES (?)", (nombre,)
            )
            conn.commit()
        finally:
            conn.close()
        return True
    except Exception:
        return False


def obtener_ids_posts_externos(conn):
    """IDs de posts externos ya guardados (para deduplicar al generar nuevos IDs)."""
    try:
        rows = conn.execute("SELECT post_id FROM external_posts").fetchall()
        return {r[0] for r in rows}
    except Exception:
        return set()


def insertar_post_externo(conn, datos, post_id):
    """Inserta un post externo en external_posts."""
    comentarios = datos.get("comentarios") or []
    conn.execute(
        """INSERT OR REPLACE INTO external_posts
            (post_id, page_name, page_url, message, created_time,
             total_reactions, comments_count, post_url, source)
            VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            post_id,
            datos.get("page_name", "") or "",
            datos.get("page_url", "") or "",
            datos.get("message", "") or "",
            datos.get("created_time"),
            int(datos.get("total_reactions", 0) or 0),
            int(datos.get("comments_count", 0) or len(comentarios)),
            datos.get("post_url", "") or "",
            "manual_externo",
        ),
    )
    return True


def insertar_comentario_externo(conn, comment_id, post_id, texto, autor=None):
    """Inserta un comentario externo en external_comments."""
    conn.execute(
        """INSERT OR REPLACE INTO external_comments
            (comment_id, post_id, message, author_name, created_time)
            VALUES (?,?,?,?,?)""",
        (comment_id, post_id, texto, (autor or "Anonymous"), None),
    )
    return True
