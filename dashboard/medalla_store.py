"""Estado de la «medalla»: sugerencia, aprobación manual y aprendizaje por ejemplos.

Guarda en facebook.db dos tablas:
  - medalla_seleccion: la medalla aprobada vigente (post FB) + los medios/páginas
    externas asociadas (réplicas que el analista marcó) + el período.
  - medalla_feedback: historial de decisiones (aprobada/rechazada) con las
    características del post, para que la sugerencia «aprenda» del criterio del
    analista (ejemplos few-shot para el re-ranking del LLM).

Módulo independiente (sqlite3 directo), sin dependencia de Streamlit.
"""

import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config import FACEBOOK_DB  # type: ignore
except Exception:
    FACEBOOK_DB = os.getenv("FACEBOOK_DB", "facebook.db")


def _db(db_path=None):
    return db_path or os.getenv("FACEBOOK_DB", "") or FACEBOOK_DB


def asegurar_tablas(db_path=None):
    conn = sqlite3.connect(_db(db_path))
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS medalla_seleccion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT,
                estado TEXT DEFAULT 'aprobada',
                score REAL DEFAULT 0,
                periodo_label TEXT DEFAULT '',
                medios_json TEXT DEFAULT '[]',
                nota TEXT DEFAULT '',
                decidido_en DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS medalla_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT,
                decision TEXT,
                features_json TEXT DEFAULT '{}',
                nota TEXT DEFAULT '',
                creado_en DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def aprobar_medalla(post_id, score=0, periodo_label="", medios=None, nota="",
                    features=None, db_path=None):
    """Registra la medalla aprobada vigente y deja constancia del feedback positivo.

    medios: lista de post_id de external_posts (réplicas marcadas por el analista).
    """
    asegurar_tablas(db_path)
    medios = list(medios or [])
    conn = sqlite3.connect(_db(db_path))
    try:
        conn.execute(
            "INSERT INTO medalla_seleccion "
            "(post_id, estado, score, periodo_label, medios_json, nota) "
            "VALUES (?,?,?,?,?,?)",
            (str(post_id), "aprobada", float(score or 0), periodo_label or "",
             json.dumps(medios), nota or ""),
        )
        conn.commit()
    finally:
        conn.close()
    registrar_feedback(post_id, "aprobada", features=features, nota=nota, db_path=db_path)


def registrar_feedback(post_id, decision, features=None, nota="", db_path=None):
    """Guarda una decisión del analista (aprobada/rechazada) como ejemplo."""
    asegurar_tablas(db_path)
    conn = sqlite3.connect(_db(db_path))
    try:
        conn.execute(
            "INSERT INTO medalla_feedback (post_id, decision, features_json, nota) "
            "VALUES (?,?,?,?)",
            (str(post_id), str(decision), json.dumps(features or {}), nota or ""),
        )
        conn.commit()
    finally:
        conn.close()


def get_medalla_vigente(db_path=None):
    """Devuelve la medalla aprobada más reciente como dict, o None."""
    asegurar_tablas(db_path)
    conn = sqlite3.connect(_db(db_path))
    try:
        row = conn.execute(
            "SELECT post_id, score, periodo_label, medios_json, nota, decidido_en "
            "FROM medalla_seleccion WHERE estado='aprobada' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    try:
        medios = json.loads(row[3] or "[]")
    except Exception:
        medios = []
    return {
        "post_id": row[0], "score": row[1], "periodo_label": row[2],
        "medios": medios, "nota": row[4], "decidido_en": row[5],
    }


def get_ejemplos_feedback(limit=20, db_path=None):
    """Últimas decisiones del analista, para usarlas como ejemplos del re-ranking."""
    asegurar_tablas(db_path)
    conn = sqlite3.connect(_db(db_path))
    try:
        rows = conn.execute(
            "SELECT post_id, decision, features_json, nota FROM medalla_feedback "
            "ORDER BY id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    finally:
        conn.close()
    out = []
    for r in rows:
        try:
            feats = json.loads(r[2] or "{}")
        except Exception:
            feats = {}
        out.append({"post_id": r[0], "decision": r[1], "features": feats, "nota": r[3]})
    return out
