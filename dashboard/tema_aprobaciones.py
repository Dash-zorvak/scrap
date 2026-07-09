"""Persistencia de aprobaciones manuales de temas.

Guarda, por comentario (comment_id de fb_comments), el tema que el usuario
APROBO manualmente y su POSTURA (apoyo/critica/neutral).

La postura es un eje SEPARADO del tema (ver dashboard/tema_taxonomia.py): permite
que la tarjeta de cada tema se divida en apoyo / critica / neutral y que una
critica NO se cuente como impulso positivo del tema.

Modulo puro de datos (sqlite + stdlib), sin Streamlit, para que sea verificable
en CI.
"""

import sqlite3
import pandas as pd
from collections import defaultdict
from datetime import datetime, timezone

from dashboard.tema_taxonomia import (
    CATEGORIAS_VALIDAS,
    REMAP_LEGACY,
    etiqueta_tema,
    normalizar_postura,
    remapear,
)
from dashboard.tema_taxonomia_expandida import (
    EMOCIONES_VALIDAS,
    normalizar_emocion,
)

TABLA = "tema_aprobaciones"


def _conectar(db_path):
    return sqlite3.connect(db_path)


def _ids_comentarios_en_periodo(db_path, ini, fin):
    """IDs de fb_comments cuyo post cae en [ini, fin].

    Replica la misma resolución de fecha que dash_fuente._cargar_comentarios_fb
    (fecha heredada de fb_posts, con respaldo en fb_engagement si el post no
    aparece ahí), pero sin importar dash_fuente (que depende de Streamlit)
    para que este módulo siga siendo puro y verificable en CI.
    """
    conn = _conectar(db_path)
    try:
        cdf = pd.read_sql("SELECT comment_id, post_id FROM fb_comments", conn)
        try:
            jdf = pd.read_sql("SELECT post_id, created_time FROM fb_posts", conn)
        except Exception:
            jdf = None
        try:
            edf = pd.read_sql("SELECT post_id, created_time FROM fb_engagement", conn)
        except Exception:
            edf = None
    finally:
        conn.close()

    if cdf.empty:
        return set()

    cdf["post_id"] = cdf["post_id"].astype(str)
    fecha_post = {}
    if jdf is not None and not jdf.empty:
        j = jdf.copy()
        j["post_id"] = j["post_id"].astype(str)
        fecha_post = dict(zip(j["post_id"], j["created_time"]))
    fecha_eng = {}
    if edf is not None and not edf.empty:
        e = edf.copy()
        e["post_id"] = e["post_id"].astype(str)
        fecha_eng = dict(zip(e["post_id"], e["created_time"]))

    created = cdf["post_id"].map(fecha_post)
    created = created.fillna(cdf["post_id"].map(fecha_eng))
    fechas = pd.to_datetime(created, errors="coerce")
    mask = (fechas >= pd.Timestamp(ini)) & (fechas <= pd.Timestamp(fin))
    return set(cdf.loc[mask, "comment_id"].tolist())


def asegurar_tabla(db_path):
    """Crea la tabla de aprobaciones si no existe y la migra si es de una
    version anterior (agrega la columna 'postura')."""
    conn = _conectar(db_path)
    try:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLA} (
                comment_id TEXT PRIMARY KEY,
                tema TEXT NOT NULL,
                tema_sugerido TEXT,
                tono TEXT,
                postura TEXT DEFAULT 'neutral',
                confianza REAL,
                texto TEXT,
                estado TEXT DEFAULT 'aprobado',
                fecha TEXT
            )
            """
        )
        # Migraciones para columnas agregadas posteriormente.
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({TABLA})").fetchall()]
        if "postura" not in cols:
            conn.execute(
                f"ALTER TABLE {TABLA} ADD COLUMN postura TEXT DEFAULT 'neutral'"
            )
        if "emocion" not in cols:
            conn.execute(
                f"ALTER TABLE {TABLA} ADD COLUMN emocion TEXT DEFAULT 'calma'"
            )
        conn.commit()
    finally:
        conn.close()


def guardar_aprobacion(db_path, comment_id, tema, texto="",
                       tema_sugerido=None, tono="literal", confianza=None,
                       postura="neutral", emocion=None):
    """Guarda (o actualiza) la aprobacion de un comentario.

    Devuelve True si se guardo. En la aprobacion MANUAL validamos de forma
    estricta: solo se aceptan categorias englobantes validas o claves legacy
    conocidas (que luego se remapean a su englobante). Cualquier otro tema
    inexistente -o falta comment_id/tema- no guarda y devuelve False.

    `postura` (apoyo/critica/neutral) se normaliza; un valor desconocido cae a
    'neutral' para no contar como apoyo ni critica por error.

    `emocion` se normaliza con normalizar_emocion(); valor desconocido cae a
    'calma'.

    Nota: a diferencia de remapear() -que degrada lo desconocido a 'no_aplica'
    para tolerar ruido del modelo-, aqui un tema invalido se RECHAZA, porque es
    una decision explicita del usuario y no debe colarse como 'no_aplica'.
    """
    if not comment_id or not tema:
        return False
    if tema not in CATEGORIAS_VALIDAS and tema not in REMAP_LEGACY:
        return False
    tema = remapear(tema)
    postura = normalizar_postura(postura)
    emocion = normalizar_emocion(emocion)
    asegurar_tabla(db_path)
    conn = _conectar(db_path)
    try:
        conn.execute(
            f"""
            INSERT OR REPLACE INTO {TABLA}
            (comment_id, tema, tema_sugerido, tono, postura, confianza, texto, estado, fecha, emocion)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'aprobado', ?, ?)
            """,
            (
                comment_id,
                tema,
                remapear(tema_sugerido) if tema_sugerido else None,
                tono,
                postura,
                confianza,
                (texto or "")[:500],
                datetime.now(timezone.utc).isoformat(),
                emocion,
            ),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def ids_aprobados(db_path):
    """Conjunto de comment_id que ya fueron revisados/aprobados."""
    asegurar_tabla(db_path)
    conn = _conectar(db_path)
    try:
        rows = conn.execute(f"SELECT comment_id FROM {TABLA}").fetchall()
    finally:
        conn.close()
    return {r[0] for r in rows}


def obtener_aprobaciones(db_path):
    """Devuelve {comment_id: {tema, tema_sugerido, tono, postura, emocion, confianza, texto, ...}}."""
    asegurar_tabla(db_path)
    conn = _conectar(db_path)
    try:
        rows = conn.execute(
            f"SELECT comment_id, tema, tema_sugerido, tono, postura, emocion, confianza, "
            f"texto, estado, fecha FROM {TABLA}"
        ).fetchall()
    finally:
        conn.close()
    salida = {}
    for cid, tema, sug, tono, postura, emocion, conf, texto, estado, fecha in rows:
        salida[cid] = {
            "tema": tema,
            "tema_sugerido": sug,
            "tono": tono,
            "postura": normalizar_postura(postura),
            "emocion": normalizar_emocion(emocion),
            "confianza": conf,
            "texto": texto,
            "estado": estado,
            "fecha": fecha,
        }
    return salida


def agregar_por_tema(db_path):
    """Agrega los comentarios APROBADOS por tema (para las tarjetas).

    Excluye 'no_aplica'. El porcentaje es sobre el total de comentarios con un
    tema aprobado (no sobre el total analizado). Cada tema se divide ademas por
    POSTURA (apoyo/critica/neutral) para que una critica no se lea como impulso
    positivo. Se incluye ademas desglose por EMOCION (10 emociones del catalogo).

    Devuelve una lista de dicts ordenada de mayor a menor doc_count:
    {id, categoria, label, pct, doc_count, ejemplo, apoyo, critica, neutral,
     pct_apoyo, pct_critica, pct_neutral, saldo, ejemplo_critica, emociones,
     emocion_dominante}.
    """
    asegurar_tabla(db_path)
    conn = _conectar(db_path)
    try:
        rows = conn.execute(
            f"SELECT tema, texto, postura, emocion FROM {TABLA} WHERE estado='aprobado'"
        ).fetchall()
    finally:
        conn.close()

    conteo = defaultdict(int)
    posturas = defaultdict(lambda: {"apoyo": 0, "critica": 0, "neutral": 0})
    emociones = defaultdict(lambda: defaultdict(int))
    ejemplos = {}
    ejemplos_critica = {}
    total_con_tema = 0
    for tema, texto, postura, emocion in rows:
        if not tema or tema == "no_aplica":
            continue
        post = normalizar_postura(postura)
        emo = normalizar_emocion(emocion)
        conteo[tema] += 1
        posturas[tema][post] += 1
        emociones[tema][emo] += 1
        total_con_tema += 1
        limpio = " ".join((texto or "").split())
        prev = ejemplos.get(tema)
        if limpio and (prev is None or 15 <= len(limpio) < len(prev)):
            ejemplos[tema] = limpio
        if post == "critica" and limpio:
            prev_c = ejemplos_critica.get(tema)
            if prev_c is None or 15 <= len(limpio) < len(prev_c):
                ejemplos_critica[tema] = limpio

    from dashboard.tema_taxonomia_expandida import EMOCIONES_VALIDAS

    temas = []
    for i, (tema, n) in enumerate(conteo.items()):
        ej = ejemplos.get(tema, "")
        if len(ej) > 120:
            ej = ej[:117] + "..."
        ej_c = ejemplos_critica.get(tema, "")
        if len(ej_c) > 120:
            ej_c = ej_c[:117] + "..."
        pst = posturas[tema]
        emo_counts = emociones.get(tema, {})
        emo_total = sum(emo_counts.values()) or 1
        emo_detalle = {
            e: {
                "count": emo_counts.get(e, 0),
                "pct": round(emo_counts.get(e, 0) / emo_total * 100, 1),
            }
            for e in EMOCIONES_VALIDAS
        }
        emo_dominante = max(EMOCIONES_VALIDAS, key=lambda e: emo_counts.get(e, 0)) if emo_counts else "calma"
        temas.append({
            "id": i + 1,
            "categoria": tema,
            "label": etiqueta_tema(tema),
            "pct": round(n / total_con_tema * 100, 1) if total_con_tema else 0.0,
            "doc_count": n,
            "ejemplo": ej,
            "apoyo": pst["apoyo"],
            "critica": pst["critica"],
            "neutral": pst["neutral"],
            "pct_apoyo": round(pst["apoyo"] / n * 100, 1) if n else 0.0,
            "pct_critica": round(pst["critica"] / n * 100, 1) if n else 0.0,
            "pct_neutral": round(pst["neutral"] / n * 100, 1) if n else 0.0,
            "saldo": pst["apoyo"] - pst["critica"],
            "ejemplo_critica": ej_c,
            "emociones": emo_detalle,
            "emocion_dominante": emo_dominante,
        })
    temas.sort(key=lambda x: -x["doc_count"])
    return temas


def resumen_revision(db_path, total_comentarios=None, ini=None, fin=None):
    """Progreso de revision: con tema, sin tema y (si se da el total) pendientes.

    `ini`/`fin`, si se dan, restringen las aprobaciones contadas a los
    comentarios del período (mismo criterio que agregar_por_tema_universo).
    """
    asegurar_tabla(db_path)
    conn = _conectar(db_path)
    try:
        rows = conn.execute(
            f"SELECT comment_id, tema FROM {TABLA} WHERE estado='aprobado'"
        ).fetchall()
    finally:
        conn.close()
    if ini is not None and fin is not None:
        ids_periodo = _ids_comentarios_en_periodo(db_path, ini, fin)
        rows = [(cid, t) for cid, t in rows if cid in ids_periodo]
    aprobados = sum(1 for (_, t) in rows if t and t != "no_aplica")
    sin_tema = sum(1 for (_, t) in rows if t == "no_aplica")
    out = {
        "aprobados": aprobados,
        "sin_tema": sin_tema,
        "total_aprobaciones": len(rows),
    }
    if total_comentarios is not None:
        out["total_comentarios"] = total_comentarios
        out["pendientes"] = max(0, total_comentarios - len(rows))
    return out



