"""Tests para Bloque 8 (8.1-8.5): correcciones estructurales.

Requiere:
  - test_guardar_aprobacion_emocion_varia: 8.2 / 8.5
  - test_esquema_tiktok_tema_aprobaciones: 8.3 / 8.5
  - test_esquema_tiktok_comments_computed: 8.3 / 8.5
  - test_esquema_externos_comments_computed: 8.3 / 8.5
"""

import os
import sqlite3
import tempfile

import pytest


# ── Helpers ──────────────────────────────────────────────


def _crear_bd_vacia(schema_sql=None):
    """Crea una BD temporal vacía y devuelve la ruta."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    if schema_sql:
        conn = sqlite3.connect(path)
        conn.executescript(schema_sql)
        conn.close()
    return path


_FB_TEMA_APROBACIONES_SCHEMA = """
CREATE TABLE IF NOT EXISTS tema_aprobaciones (
    comment_id TEXT PRIMARY KEY,
    tema TEXT NOT NULL,
    tema_sugerido TEXT,
    tono TEXT,
    postura TEXT DEFAULT 'neutral',
    confianza REAL,
    texto TEXT,
    estado TEXT DEFAULT 'aprobado',
    fecha TEXT,
    emocion TEXT DEFAULT 'calma'
);
"""

_TIKTOK_COMMENTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY,
    video_id TEXT,
    username TEXT,
    text TEXT,
    likes INTEGER DEFAULT 0,
    replies_count INTEGER DEFAULT 0,
    created_at TEXT
);
"""

_EXTERNAL_COMMENTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS external_comments (
    comment_id TEXT PRIMARY KEY,
    post_id TEXT,
    message TEXT,
    author_name TEXT DEFAULT 'Anonymous',
    created_time DATETIME,
    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


# ════════════════════════════════════════════════════════════
# Test 1: guardar_aprobacion produce emocion/tono distintos
# de "calma"/"literal" para comentarios reales (8.2 / 8.5)
# ════════════════════════════════════════════════════════════


def test_guardar_aprobacion_emocion_varia():
    """La funcion real que llena tono/emocion en tema_aprobaciones
    produce valores distintos a 'calma'/'literal' para varios de
    los 98 comentarios reales citados en 8.2."""
    from dashboard.tema_aprobaciones import guardar_aprobacion, obtener_aprobaciones

    db = _crear_bd_vacia(_FB_TEMA_APROBACIONES_SCHEMA)

    # Comentarios reales extraidos de la BD de produccion
    casos = [
        ("💯👏👏👏Gracias🌹", "apoyo_generico", "apoyo"),
        ("Excelente trabajo sr alcalde", "apoyo_generico", "apoyo"),
        ("Muchas felicidades al Licenciado Ismael Quijjada... y a todos los", "apoyo_generico", "apoyo"),
        ("Enojado con la corrupcion en el municipio", "gobernanza", "critica"),
        ("Los baches en la calle estan terrible", "obras_servicios", "critica"),
    ]

    for i, (texto, tema, postura) in enumerate(casos):
        cid = f"test_{i:04d}"
        ok = guardar_aprobacion(db, cid, tema, texto=texto, postura=postura,
                                tono=None, emocion=None)
        assert ok, f"Fallo guardar_aprobacion para '{texto[:40]}'"

    aprobaciones = obtener_aprobaciones(db)
    assert len(aprobaciones) == len(casos)

    # Verificar que al menos 3 de los 5 tienen emocion distinta de "calma"
    no_calma = sum(
        1 for a in aprobaciones.values() if a["emocion"] != "calma"
    )
    assert no_calma >= 3, (
        f"Solo {no_calma}/5 tienen emocion != 'calma'. "
        f"Distribucion: {[(a['emocion'], a['tono']) for a in aprobaciones.values()]}"
    )

    # Verificar que al menos 3 de los 5 tienen tono distinto de "literal"
    no_literal = sum(
        1 for a in aprobaciones.values() if a["tono"] != "literal"
    )
    assert no_literal >= 3, (
        f"Solo {no_literal}/5 tienen tono != 'literal'"
    )

    # Caso especifico: el comentario con emoji deberia clasificar como reconocimiento
    r0 = aprobaciones.get("test_0000", {})
    assert r0.get("emocion") in ("reconocimiento", "civica_nueva"), (
        f"'💯👏👏👏Gracias🌹' -> emocion={r0.get('emocion')}, se esperaba reconocimiento o civica_nueva"
    )


# ════════════════════════════════════════════════════════════
# Test 2: tiktok.db tiene tema_aprobaciones con las mismas
# columnas que facebook.db (8.3 / 8.5)
# ════════════════════════════════════════════════════════════


def test_esquema_tiktok_tema_aprobaciones():
    """tiktok.db::tema_aprobaciones tiene las mismas columnas
    que facebook.db despues de asegurar_tabla_en_tiktok()."""
    from dashboard.tema_aprobaciones import asegurar_tabla_en_tiktok

    db = _crear_bd_vacia()
    asegurar_tabla_en_tiktok(db)

    conn = sqlite3.connect(db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(tema_aprobaciones)").fetchall()}
    conn.close()

    esperadas = {
        "comment_id", "tema", "tema_sugerido", "tono",
        "postura", "confianza", "texto", "estado", "fecha", "emocion",
    }
    assert cols == esperadas, (
        f"Columnas en tiktok tema_aprobaciones: {cols}\n"
        f"Esperadas: {esperadas}\n"
        f"Faltan: {esperadas - cols}\n"
        f"Sobran: {cols - esperadas}"
    )


# ════════════════════════════════════════════════════════════
# Test 3: tiktok.db::comments tiene columnas computed (8.3 / 8.5)
# ════════════════════════════════════════════════════════════


def test_esquema_tiktok_comments_computed():
    """tiktok.db::comments tiene sentiment/sentiment_score/
    topic_category/zona tras asegurar_computed_tiktok()."""
    from dashboard.tema_aprobaciones import asegurar_computed_tiktok

    db = _crear_bd_vacia(_TIKTOK_COMMENTS_SCHEMA)
    asegurar_computed_tiktok(db)

    conn = sqlite3.connect(db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(comments)").fetchall()}
    conn.close()

    for col in ("sentiment", "sentiment_score", "topic_category", "zona"):
        assert col in cols, f"Falta columna '{col}' en tiktok.db::comments"


# ════════════════════════════════════════════════════════════
# Test 4: externos.db::external_comments tiene columnas
# computed (8.3 / 8.5)
# ════════════════════════════════════════════════════════════


def test_esquema_externos_comments_computed():
    """externos.db::external_comments tiene sentiment/
    sentiment_score/topic_category/zona tras
    asegurar_computed_externos()."""
    from dashboard.tema_aprobaciones import asegurar_computed_externos

    db = _crear_bd_vacia(_EXTERNAL_COMMENTS_SCHEMA)
    asegurar_computed_externos(db)

    conn = sqlite3.connect(db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(external_comments)").fetchall()}
    conn.close()

    for col in ("sentiment", "sentiment_score", "topic_category", "zona"):
        assert col in cols, f"Falta columna '{col}' en externos.db::external_comments"


# ════════════════════════════════════════════════════════════
# Test 5: Idempotencia de las 3 migraciones (8.7.3)
# ════════════════════════════════════════════════════════════


def test_migraciones_idempotentes():
    """asegurar_tabla/asegurar_tabla_en_tiktok/asegurar_computed_tiktok/
    asegurar_computed_externos se pueden ejecutar dos veces
    consecutivas sin lanzar error.
    """
    from dashboard.tema_aprobaciones import (
        asegurar_tabla,
        asegurar_tabla_en_tiktok,
        asegurar_computed_tiktok,
        asegurar_computed_externos,
    )

    # asegurar_tabla duplicado
    db1 = _crear_bd_vacia()
    asegurar_tabla(db1)
    asegurar_tabla(db1)  # segunda llamada

    conn = sqlite3.connect(db1)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(tema_aprobaciones)").fetchall()}
    conn.close()
    # columna emocion debe aparecer solo una vez
    assert len([c for c in cols if c == "emocion"]) == 1
    assert len([c for c in cols if c == "postura"]) == 1

    # asegurar_tabla_en_tiktok duplicado
    db2 = _crear_bd_vacia()
    asegurar_tabla_en_tiktok(db2)
    asegurar_tabla_en_tiktok(db2)  # segunda chamada
    conn = sqlite3.connect(db2)
    cols2 = {r[1] for r in conn.execute("PRAGMA table_info(tema_aprobaciones)").fetchall()}
    conn.close()
    assert "emocion" in cols2
    assert "postura" in cols2

    # asegurar_computed_tiktok duplicado
    db3 = _crear_bd_vacia(_TIKTOK_COMMENTS_SCHEMA)
    asegurar_computed_tiktok(db3)
    asegurar_computed_tiktok(db3)  # segunda chamada
    conn = sqlite3.connect(db3)
    cols3 = set(r[1] for r in conn.execute("PRAGMA table_info(comments)").fetchall())
    conn.close()
    for col in ("sentiment", "sentiment_score", "topic_category", "zona"):
        assert col in cols3, f"Falta {col}"
    # Verify no duplicates
    conn = sqlite3.connect(db3)
    raw_cols = conn.execute("PRAGMA table_info(comments)").fetchall()
    conn.close()
    col_names = [r[1] for r in raw_cols]
    for col in ("sentiment", "sentiment_score", "topic_category", "zona"):
        assert col_names.count(col) == 1, \
            f"Columna duplicada: {col} aparece {col_names.count(col)} veces"

    # asegurar_computed_externos duplicado
    db4 = _crear_bd_vacia(_EXTERNAL_COMMENTS_SCHEMA)
    asegurar_computed_externos(db4)
    asegurar_computed_externos(db4)  # segunda chamada
    conn4 = sqlite3.connect(db4)
    cols4 = set(r[1] for r in conn4.execute("PRAGMA table_info(external_comments)").fetchall())
    for col in ("sentiment", "sentiment_score", "topic_category", "zona"):
        assert col in cols4, f"Falta {col}"
    raw_cols4 = conn4.execute("PRAGMA table_info(external_comments)").fetchall()
    col_names4 = [r[1] for r in raw_cols4]
    for col in ("sentiment", "sentiment_score", "topic_category", "zona"):
        assert col_names4.count(col) == 1, \
            f"Columna duplicada: {col} aparece {col_names4.count(col)} veces"
    conn4.close()



# ════════════════════════════════════════════════════════════
# Test 6: Clave propuesta de emocion determinista (mismo texto
# sin match léxico → misma clave, incluso emoji-only) (8.2)
# ════════════════════════════════════════════════════════════


def test_propuesta_emocion_determinista():
    """classify_emotion() con el mismo texto sin match siempre
    devuelve la misma clave propuesta.

    Mismo patron que test_propuesta_tema_determinista (Bloque 5.3/20.3).
    Incluye caso emoji-only (fuerza ruta del hash).
    """
    from analytics.emotion import classify_emotion

    textos = [
        "El cielo esta hermoso hoy en la manana",
        "Las estrellas brillan muchisimo esta noche",
        "Mi gato duerme todo el dia en el sofa",
        "👏👏👏",               # emoji-only → ruta hash
        "👍❤️🙏",               # emoji-only → ruta hash
    ]
    for texto in textos:
        r1 = classify_emotion(texto)
        r2 = classify_emotion(texto)
        assert r1.emocion == r2.emocion, (
            f"Clave no determinista para '{texto}': "
            f"'{r1.emocion}' vs '{r2.emocion}'"
        )
