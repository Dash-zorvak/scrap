"""Persistencia de aprobaciones manuales de temas + aprendizaje (few-shot).

Guarda, por comentario (comment_id de fb_comments), el tema que el usuario
APROBO manualmente. La IA solo sugiere; nada cuenta en las tarjetas de Temas
Emergentes hasta que el usuario lo aprueba aqui.

"Aprendizaje" sin reentrenar y con presupuesto 0: las aprobaciones se reusan
como ejemplos validados (few-shot) que se inyectan al prompt del modelo. Cuantas
mas apruebes, mas se alinea la sugerencia con tu criterio.

Modulo puro de datos (sqlite + stdlib), sin Streamlit, para que sea verificable
en CI.
"""

import sqlite3
from collections import defaultdict
from datetime import datetime, timezone

from dashboard.tema_taxonomia import (
    CATEGORIAS_VALIDAS,
    REMAP_LEGACY,
    etiqueta_tema,
    remapear,
)

TABLA = "tema_aprobaciones"


def _conectar(db_path):
    return sqlite3.connect(db_path)


def asegurar_tabla(db_path):
    """Crea la tabla de aprobaciones si no existe."""
    conn = _conectar(db_path)
    try:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLA} (
                comment_id TEXT PRIMARY KEY,
                tema TEXT NOT NULL,
                tema_sugerido TEXT,
                tono TEXT,
                confianza REAL,
                texto TEXT,
                estado TEXT DEFAULT 'aprobado',
                fecha TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def guardar_aprobacion(db_path, comment_id, tema, texto="",
                       tema_sugerido=None, tono="literal", confianza=None):
    """Guarda (o actualiza) la aprobacion de un comentario.

    Devuelve True si se guardo. En la aprobacion MANUAL validamos de forma
    estricta: solo se aceptan categorias englobantes validas o claves legacy
    conocidas (que luego se remapean a su englobante). Cualquier otro tema
    inexistente -o falta comment_id/tema- no guarda y devuelve False.

    Nota: a diferencia de remapear() -que degrada lo desconocido a 'no_aplica'
    para tolerar ruido del modelo-, aqui un tema invalido se RECHAZA, porque es
    una decision explicita del usuario y no debe colarse como 'no_aplica'.
    """
    if not comment_id or not tema:
        return False
    if tema not in CATEGORIAS_VALIDAS and tema not in REMAP_LEGACY:
        return False
    tema = remapear(tema)
    asegurar_tabla(db_path)
    conn = _conectar(db_path)
    try:
        conn.execute(
            f"""
            INSERT OR REPLACE INTO {TABLA}
            (comment_id, tema, tema_sugerido, tono, confianza, texto, estado, fecha)
            VALUES (?, ?, ?, ?, ?, ?, 'aprobado', ?)
            """,
            (
                comment_id,
                tema,
                remapear(tema_sugerido) if tema_sugerido else None,
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
    """Devuelve {comment_id: {tema, tema_sugerido, tono, confianza, texto, ...}}."""
    asegurar_tabla(db_path)
    conn = _conectar(db_path)
    try:
        rows = conn.execute(
            f"SELECT comment_id, tema, tema_sugerido, tono, confianza, texto, "
            f"estado, fecha FROM {TABLA}"
        ).fetchall()
    finally:
        conn.close()
    salida = {}
    for cid, tema, sug, tono, conf, texto, estado, fecha in rows:
        salida[cid] = {
            "tema": tema,
            "tema_sugerido": sug,
            "tono": tono,
            "confianza": conf,
            "texto": texto,
            "estado": estado,
            "fecha": fecha,
        }
    return salida


def agregar_por_tema(db_path):
    """Agrega los comentarios APROBADOS por tema (para las tarjetas).

    Excluye 'no_aplica'. El porcentaje es sobre el total de comentarios con un
    tema aprobado (no sobre el total analizado). Devuelve una lista de dicts:
    {id, categoria, label, pct, doc_count, ejemplo}, ordenada de mayor a menor.
    """
    asegurar_tabla(db_path)
    conn = _conectar(db_path)
    try:
        rows = conn.execute(
            f"SELECT tema, texto FROM {TABLA} WHERE estado='aprobado'"
        ).fetchall()
    finally:
        conn.close()

    conteo = defaultdict(int)
    ejemplos = {}
    total_con_tema = 0
    for tema, texto in rows:
        if not tema or tema == "no_aplica":
            continue
        conteo[tema] += 1
        total_con_tema += 1
        limpio = " ".join((texto or "").split())
        prev = ejemplos.get(tema)
        if limpio and (prev is None or 15 <= len(limpio) < len(prev)):
            ejemplos[tema] = limpio

    temas = []
    for i, (tema, n) in enumerate(conteo.items()):
        ej = ejemplos.get(tema, "")
        if len(ej) > 120:
            ej = ej[:117] + "..."
        temas.append({
            "id": i + 1,
            "categoria": tema,
            "label": etiqueta_tema(tema),
            "pct": round(n / total_con_tema * 100, 1) if total_con_tema else 0.0,
            "doc_count": n,
            "ejemplo": ej,
        })
    temas.sort(key=lambda x: -x["doc_count"])
    return temas


def resumen_revision(db_path, total_comentarios=None):
    """Progreso de revision: con tema, sin tema y (si se da el total) pendientes."""
    asegurar_tabla(db_path)
    conn = _conectar(db_path)
    try:
        rows = conn.execute(
            f"SELECT tema FROM {TABLA} WHERE estado='aprobado'"
        ).fetchall()
    finally:
        conn.close()
    aprobados = sum(1 for (t,) in rows if t and t != "no_aplica")
    sin_tema = sum(1 for (t,) in rows if t == "no_aplica")
    out = {
        "aprobados": aprobados,
        "sin_tema": sin_tema,
        "total_aprobaciones": len(rows),
    }
    if total_comentarios is not None:
        out["total_comentarios"] = total_comentarios
        out["pendientes"] = max(0, total_comentarios - len(rows))
    return out


def ejemplos_few_shot(db_path, por_tema=3, max_total=24):
    """Muestra balanceada de aprobaciones para ensenar al modelo (few-shot).

    Hasta `por_tema` ejemplos por categoria (incluido 'no_aplica', util para que
    el modelo aprenda que NO es un tema), con tope global `max_total`. Cada item:
    {"texto", "tema"}. Orden determinista para que sea testeable.
    """
    asegurar_tabla(db_path)
    conn = _conectar(db_path)
    try:
        rows = conn.execute(
            f"SELECT tema, texto FROM {TABLA} "
            f"WHERE estado='aprobado' AND texto IS NOT NULL AND texto != ''"
        ).fetchall()
    finally:
        conn.close()

    por_cat = defaultdict(list)
    for tema, texto in rows:
        t = " ".join((texto or "").split())
        if t and tema:
            por_cat[tema].append(t)

    salida = []
    for tema in sorted(por_cat.keys()):
        for t in sorted(por_cat[tema])[:por_tema]:
            salida.append({"texto": t[:200], "tema": tema})
    return salida[:max_total]
