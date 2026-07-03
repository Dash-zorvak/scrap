"""Persistencia de clasificaciones de IA (sugerencias, no decisiones humanas).

Modulo puro de datos (sqlite + stdlib), sin Streamlit, para que sea verificable
en CI. Almacena las sugerencias que la IA genera en sugerir_temas_pendientes
para ampliar el universo de calculo en Temas Emergentes sin disparar llamadas
nuevas a la IA desde el dashboard del alcalde.
"""

import sqlite3
from datetime import datetime, timezone

TABLA = "tema_clasificaciones_ia"


def _conectar(db_path):
    return sqlite3.connect(db_path)


def asegurar_tabla(db_path):
    """Crea la tabla de clasificaciones IA si no existe."""
    conn = _conectar(db_path)
    try:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLA} (
                comment_id TEXT PRIMARY KEY,
                tema TEXT NOT NULL,
                postura TEXT DEFAULT 'neutral',
                tono TEXT,
                confianza REAL,
                texto TEXT,
                fecha TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def guardar_clasificacion_ia(db_path, comment_id, tema, postura="neutral",
                             tono="literal", confianza=None, texto=""):
    """Guarda (o actualiza) la clasificacion IA de un comentario.

    Devuelve True si se guardo. No valida tanto como guardar_aprobacion
    (es una sugerencia de IA, no una decision humana), pero descarta si
    falta comment_id o tema.
    """
    if not comment_id or not tema:
        return False
    asegurar_tabla(db_path)
    conn = _conectar(db_path)
    try:
        conn.execute(
            f"""
            INSERT OR REPLACE INTO {TABLA}
            (comment_id, tema, postura, tono, confianza, texto, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                comment_id,
                tema,
                postura,
                tono,
                confianza,
                (texto or "")[:500],
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def obtener_clasificaciones_ia(db_path):
    """Devuelve {comment_id: {tema, postura, tono, confianza, texto, fecha}}."""
    asegurar_tabla(db_path)
    conn = _conectar(db_path)
    try:
        rows = conn.execute(
            f"SELECT comment_id, tema, postura, tono, confianza, texto, fecha FROM {TABLA}"
        ).fetchall()
    finally:
        conn.close()
    salida = {}
    for cid, tema, postura, tono, conf, texto, fecha in rows:
        salida[cid] = {
            "tema": tema,
            "postura": postura,
            "tono": tono,
            "confianza": conf,
            "texto": texto,
            "fecha": fecha,
        }
    return salida