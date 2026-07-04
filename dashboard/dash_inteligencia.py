"""Capa de inteligencia: conecta Cambridge Index, IQ Engine y resúmenes por zona."""

import sys
import os
import sqlite3
import logging
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from config import FACEBOOK_DB
from dashboard.tema_taxonomia import etiqueta_tema
from dashboard.tema_clasificaciones_ia import guardar_clasificacion_ia

logger = logging.getLogger("dash_inteligencia")


def sugerir_temas_pendientes_cacheado(db_path=None, cache=None, limite=None) -> list[dict]:
    """Igual que sugerir_temas_pendientes pero reutilizando un cache por comentario.

    `cache` es un dict {comment_id: sugerencia_dict} que se MUTA in-place. Solo
    se invoca al LLM para los comentarios pendientes que aun NO estan en el
    cache; el resto se sirve desde el cache. Asi, aprobar un comentario (que en
    la UI dispara un rerun) ya no obliga a reclasificar a los demas: el bloque
    de revision deja de congelarse en cada aprobacion.
    """
    if db_path is None:
        db_path = FACEBOOK_DB
    if cache is None:
        cache = {}
    if limite is None:
        try:
            limite = int(os.environ.get("TEMAS_PENDIENTES_LOTE", "40"))
        except (TypeError, ValueError):
            limite = 40

    from dashboard.tema_aprobaciones import ids_aprobados, ejemplos_few_shot
    from dashboard.topic_llm import clasificar_temas_lote

    rows = []
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute("""
            SELECT comment_id, message FROM fb_comments
            WHERE message IS NOT NULL AND message != ''
            ORDER BY (created_time IS NULL), created_time DESC
        """).fetchall()
        conn.close()
    except Exception as e:
        logger.warning("No se pudo ordenar fb_comments por fecha, se intenta sin orden: %s", e)
        try:
            conn = sqlite3.connect(db_path)
            rows = conn.execute(
                "SELECT comment_id, message FROM fb_comments "
                "WHERE message IS NOT NULL AND message != ''"
            ).fetchall()
            conn.close()
        except Exception as e:
            logger.exception("Fallo leyendo fb_comments para sugerir temas pendientes")
            try:
                st.warning("No se pudieron cargar los comentarios pendientes de revisión (error interno).")
            except Exception:
                pass
            return []

    aprobados = ids_aprobados(db_path)
    pendientes = [(cid, msg) for cid, msg in rows if cid not in aprobados]
    if not pendientes:
        return []
    pendientes = pendientes[:limite]

    # Solo se clasifican (LLM) los pendientes que aun no tienen sugerencia en el
    # cache. Si todos ya estan cacheados, no se hace ninguna llamada al modelo.
    faltantes = [(cid, msg) for cid, msg in pendientes if cid not in cache]
    if faltantes:
        ejemplos = ejemplos_few_shot(db_path)
        textos = [m for _, m in faltantes]
        sugerencias = clasificar_temas_lote(textos, ejemplos=ejemplos or None)
        for (cid, msg), sug in zip(faltantes, sugerencias):
            sug = sug or {}
            cat = sug.get("categoria", "no_aplica") or "no_aplica"
            cache[cid] = {
                "comment_id": cid,
                "texto": " ".join(str(msg or "").split()),
                "sugerencia": cat,
                "sugerencia_label": etiqueta_tema(cat),
                "tono": sug.get("tono", "literal"),
                "confianza": sug.get("confianza", 0.5),
            }
            guardar_clasificacion_ia(
                db_path, cid, cat,
                postura=sug.get("postura", "neutral"),
                tono=sug.get("tono", "literal"),
                confianza=sug.get("confianza", 0.5),
                texto=msg,
            )

    salida = []
    for cid, msg in pendientes:
        item = cache.get(cid)
        if item is None:
            # Defensivo: si por algun motivo no se cacheo, crea uno neutro.
            item = {
                "comment_id": cid,
                "texto": " ".join(str(msg or "").split()),
                "sugerencia": "no_aplica",
                "sugerencia_label": etiqueta_tema("no_aplica"),
                "tono": "literal",
                "confianza": 0.5,
            }
        salida.append(item)
    return salida


def cargar_temas_universo(db_path=None) -> list[dict]:
    """Tarjetas de Temas Emergentes: comentarios aprobados + clasificaciones IA.

    Universo combinado: IA como base, aprobaciones manuales sobrescriben
    (control de calidad). Comentarios sin ninguna clasificacion quedan fuera.
    """
    if db_path is None:
        db_path = FACEBOOK_DB
    from dashboard.tema_aprobaciones import agregar_por_tema_universo
    return agregar_por_tema_universo(db_path)
