"""Orquestador del pipeline Fase 5: ejecuta módulos 1-4 en orden."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from config import FACEBOOK_DB, TIKTOK_DB
from modulo2_sentimiento import analizar_sentimiento_facebook, analizar_sentimiento_tiktok
from modulo1_categorias import categorizar_posts, guardar_nombres_clusters
from modulo3_engagement import procesar_facebook, procesar_tiktok
from modulo4_series import series_facebook, series_tiktok


def procesar_pipeline(progreso_cb=None):
    """Ejecuta el pipeline completo en orden.

    Args:
        progreso_cb: Callable(paso_actual, total, etiqueta) para UI.

    Returns:
        dict con motor_sentimiento, pasos_ok, errores, resumen.
    """
    fb_db = FACEBOOK_DB
    tk_db = TIKTOK_DB
    total_pasos = 6
    pasos_ok = []
    errores = []
    motor_sentimiento = "reglas"

    def _notificar(paso, etiqueta):
        if progreso_cb:
            progreso_cb(paso, total_pasos, etiqueta)

    _notificar(1, "Analizando sentimiento Facebook...")
    try:
        df_fb_sent, motor_fb = analizar_sentimiento_facebook(db_path=fb_db)
        motor_sentimiento = motor_fb
        pasos_ok.append("sentimiento_facebook")
    except Exception as e:
        errores.append(f"sentimiento_facebook: {e}")
        motor_sentimiento = "reglas"

    _notificar(2, "Analizando sentimiento TikTok...")
    try:
        df_tk_sent, motor_tk = analizar_sentimiento_tiktok(db_path=tk_db)
        if motor_sentimiento == "reglas":
            motor_sentimiento = motor_tk
        pasos_ok.append("sentimiento_tiktok")
    except Exception as e:
        errores.append(f"sentimiento_tiktok: {e}")

    _notificar(3, "Categorizando posts (embeddings + KMeans)...")
    try:
        categorizar_posts(fb_db=fb_db, tk_db=tk_db)
        guardar_nombres_clusters(fb_db=fb_db)
        pasos_ok.append("categorias")
    except Exception as e:
        errores.append(f"categorias: {e}")

    _notificar(4, "Calculando engagement Facebook...")
    try:
        procesar_facebook(fb_db=fb_db)
        pasos_ok.append("engagement_facebook")
    except Exception as e:
        errores.append(f"engagement_facebook: {e}")

    _notificar(5, "Calculando engagement TikTok...")
    try:
        procesar_tiktok(tk_db=tk_db)
        pasos_ok.append("engagement_tiktok")
    except Exception as e:
        errores.append(f"engagement_tiktok: {e}")

    _notificar(6, "Generando series temporales...")
    try:
        series_facebook(fb_db=fb_db)
        series_tiktok(tk_db=tk_db)
        pasos_ok.append("series")
    except Exception as e:
        errores.append(f"series: {e}")

    resumen = {}
    for paso in pasos_ok:
        resumen[paso] = "ok"

    _notificar(total_pasos, "Pipeline completado")

    # Persistir tablas agregadas en HF Dataset si la sincronización está activa
    # (no-op en local/Railway).
    try:
        from dashboard.hf_sync import push_dbs as _hf_push_dbs
        _hf_push_dbs()
    except Exception:
        pass

    return {
        "motor_sentimiento": motor_sentimiento,
        "pasos_ok": pasos_ok,
        "errores": errores,
        "resumen": resumen,
    }
