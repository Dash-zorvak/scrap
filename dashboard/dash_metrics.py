"""Capa de datos y metricas del dashboard (extraida de app.py).

Contiene consultas SQL seguras, carga de engagement/sentimiento/series,
clculos (semaforo, patrones, confianza, narrativas, contagio, viralidad,
correlacion) y la capa de narrativa IA (cascada NIM: DeepSeek -> GLM). Las
rutas de BD activas se resuelven en tiempo de ejecucion via _activas().
"""

import streamlit as st
import sqlite3
import pandas as pd
import logging
import os
import json

from config import (
    FACEBOOK_DB, TIKTOK_DB, EXTERNOS_DB,
)
from dashboard.llm_groq import chat_texto, groq_disponible, VERIFIER_MODEL


def _activas():
    """Devuelve (FACEBOOK_DB, TIKTOK_DB, EXTERNOS_DB)."""
    return (FACEBOOK_DB, TIKTOK_DB, EXTERNOS_DB)


@st.cache_data(ttl=3600, show_spinner=False)
def generar_narrativa_ia(tipo: str, contexto: dict) -> str:
    """
    Genera narrativa ejecutiva con la cascada de IA en NVIDIA NIM: modelo
    primario DeepSeek V4 Flash (LLM_TEXT_MODEL) y, si falla, respaldo con el
    verificador GLM 5.1 (LLM_VERIFIER_MODEL). Es la MISMA cascada NIM que usa la
    clasificacion de temas; no se usa Groq.
    Tipos: 'eco_historico', 'leccion', 'brecha', 'contexto',
           'correlacion', 'proyeccion', 'recomendacion'
    """
    if not groq_disponible():
        return "Análisis IA no disponible en este momento (falta LLM_API_KEY / NVIDIA_API_KEY en el entorno o en .env)"

    reglas_comunes = (
        " REGLAS OBLIGATORIAS DE SALIDA: "
        "(1) Escribe en español claro y directo, como si se lo explicaras a una persona sin "
        "formación técnica (nivel de bachillerato): frases cortas, sin jerga, sin adjetivos vacíos "
        "ni frases de relleno. Si usas un término técnico, explícalo en pocas palabras. "
        "(2) PROHIBIDO mencionar o insinuar 'reelección', 'campaña', 'propaganda', 'voto', 'votos', "
        "'candidato' o cualquier estrategia electoral o de imagen. Esto es un análisis de GESTIÓN y "
        "PERCEPCIÓN ciudadana, NO de política electoral. "
        "(3) Cada afirmación se sostiene con una cifra concreta del contexto (porcentaje, conteo, "
        "índice, interacciones, comentarios). Nada de generalidades sin un número detrás. "
        "(4) Cuando el dato exista, nombra la zona, colonia, categoría o tema concreto. NUNCA inventes "
        "datos, eventos ni cifras que no estén en el contexto; si falta evidencia, dilo explícitamente. "
        "(5) Un solo párrafo, máximo 110 palabras."
    )

    prompts = {
        "eco_historico": (
            "Eres analista de percepción ciudadana para la Alcaldía de Santa Ana. "
            "Con las métricas de percepción del período, responde a una pregunta concreta: "
            "¿esta situación ya se vivió antes según los datos (un patrón de enojo, de apoyo o un "
            "tema que reaparece) y cómo se comportó entonces? Si en el contexto no hay un precedente "
            "claro, dilo sin rodeos en lugar de inventarlo. Solo describe el patrón, no opines."
        ),
        "leccion": (
            "Eres analista de percepción ciudadana. Extrae UNA sola lección operativa concreta de "
            "este período: qué tipo de contenido o tema funcionó o falló según las cifras, y qué "
            "conviene repetir o evitar. Debe ser específica y verificable con los números del "
            "contexto, no un consejo genérico. Describe el aprendizaje a partir de los datos."
        ),
        "brecha": (
            "Eres analista de percepción ciudadana. Señala 'lo que nadie ve': un dato del contexto "
            "que contradice la lectura superficial. Por ejemplo, apoyo general alto pero concentrado "
            "en un solo tema; calma aparente con un foco de enojo en una zona; o un sentimiento "
            "promedio neutro que en realidad esconde dos bandos opuestos. Explica el contraste entre "
            "la percepción evidente y lo que muestran las cifras. No inventes una 'realidad de gestión': "
            "usa solo los datos disponibles."
        ),
        "contexto": (
            "Eres analista de percepción ciudadana. Explica qué factores FUERA de las redes podrían "
            "estar detrás del sentimiento detectado (temas dominantes, zonas con más enojo, picos de "
            "actividad), basándote SOLO en las señales presentes en el contexto. No inventes eventos, "
            "noticias ni fechas; si no hay señal suficiente para afirmarlo, dilo con claridad."
        ),
        "correlacion": (
            "Eres analista de percepción ciudadana. Describe la relación entre el TIPO DE CONTENIDO "
            "publicado y la REACCIÓN ciudadana (la brecha entre la reacción al post y el tono de los "
            "comentarios). Indica qué tipo de contenido genera desconexión, con cifras. Solo diagnóstico."
        ),
        "proyeccion": (
            "Eres analista de percepción ciudadana. Proyecta el escenario de las próximas 24 a 48 horas "
            "si la tendencia actual de sentimiento y de interacción se mantiene. Di hacia dónde va la "
            "conversación y qué señal concreta habría que vigilar en ese plazo. Es una estimación a partir "
            "de la tendencia, no una certeza: dilo así. Alerta temprana, con cifras y sin alarmismo."
        ),
        "recomendacion": (
            "Eres analista de percepción ciudadana. Entrega UNA recomendación estratégica de GESTIÓN y "
            "COMUNICACIÓN INSTITUCIONAL (nunca electoral ni de imagen) priorizada por los datos: qué "
            "conviene atender PRIMERO según el tema o la zona con más fricción, y por qué, citando la "
            "cifra que lo justifica. Debe ser concreta y accionable (qué revisar, aclarar o responder), "
            "no un diagnóstico ni una generalidad. Una sola recomendación principal, sustentada en el contexto."
        ),
    }

    prompt_base = prompts.get(tipo, prompts["recomendacion"]) + reglas_comunes
    ctx_str = json.dumps(contexto, ensure_ascii=False, default=str)[:3000]
    prompt_full = f"{prompt_base}\n\nCONTEXTO (JSON):\n{ctx_str}"

    modelos = [None]
    if VERIFIER_MODEL:
        modelos.append(VERIFIER_MODEL)

    ultimo_error = None
    for modelo in modelos:
        try:
            resultado, _, _ = chat_texto(
                prompt_full,
                max_tokens=600,
                temperature=0.6,
                json=False,
                model=modelo,
            )
            return resultado
        except Exception as e:
            ultimo_error = e
            continue

    logging.warning(
        "generar_narrativa_ia: cascada agotada (%s): %r", tipo, ultimo_error
    )
    return "Análisis IA no disponible en este momento (error en llamada API)"


def generar_interpretacion(tipo, datos):
    score = datos.get('score', 0)
    pct_neg = datos.get('pct_negativo', 0)
    pct_pos = datos.get('pct_positivo', 0)
    enojo = datos.get('indice_enojo', 0)
    total = datos.get('total_comentarios', 0)

    def _a(num, singular, plural):
        return singular if num == 1 else plural

    if tipo == "semaforo":
        if total < 20 and total > 0:
            n_pos = datos.get('n_positivos', round(pct_pos / 100 * total))
            n_neg = datos.get('n_negativos', round(pct_neg / 100 * total))
            return (f"{n_pos} {_a(n_pos, 'comentario es', 'comentarios son')} positivos "
                    f"y {n_neg} {_a(n_neg, 'es', 'son')} negativos, de {int(total)} en total.")
        if score >= 0.25:
            return f"{pct_pos:.0f}% de los comentarios son de apoyo. El {pct_neg:.0f}% son negativos. Las reacciones positivas superan a las negativas."
        elif score >= 0.10:
            return f"{pct_pos:.0f}% de los comentarios son positivos y {pct_neg:.0f}% negativos. Balance ligeramente favorable con señales mixtas (score {score:.2f})."
        elif score >= 0:
            return f"{pct_neg:.0f}% de los comentarios son negativos y el enojo representa el {enojo*100:.0f}% de las reacciones. Apoyo y rechazo están casi empatados."
        else:
            return f"ALERTA. El enojo es el {enojo*100:.0f}% de las reacciones. {pct_neg:.0f}% de los comentarios son negativos. Las reacciones adversas superan ampliamente a las positivas."

    elif tipo == "tema_critico":
        tema = datos.get('tema', '')
        reacciones = datos.get('reacciones', 0)
        return f"'{tema}' concentra {reacciones:,} reacciones con {pct_neg:.0f}% de comentarios negativos. Las reacciones adversas (enojo, burla) superan al apoyo en este tema."

    elif tipo == "tema_positivo":
        tema = datos.get('tema', '')
        return f"'{tema}' registra {pct_pos:.0f}% de comentarios positivos. La ciudadanía comparte este contenido sin necesidad de amplificación pagada."

    elif tipo == "anomalia":
        fecha = datos.get('fecha', '')
        views = datos.get('views', 0)
        tipo_pico = datos.get('tipo', 'positivo')
        if tipo_pico == 'positivo':
            return f"La semana del {fecha} registró {views:,} interacciones, por encima del promedio semanal."
        else:
            return f"La semana del {fecha} registró una caída en la interacción, con más rechazo que el promedio."

    elif tipo == "patron_rechazo":
        nombre = datos.get('nombre', '')
        count = datos.get('count', 0)
        tendencia = datos.get('tendencia', '')
        return f"{count} personas expresaron este patrón con sus propias palabras. No es un comentario aislado: es una narrativa colectiva. Tendencia: {tendencia}. Es ciudadanía expresando un reclamo directo."

    elif tipo == "patron_respaldo":
        nombre = datos.get('nombre', '')
        count = datos.get('count', 0)
        return f"{count} personas expresaron respaldo ciudadano sin mediar encuesta ni estímulo directo."

    elif tipo == "microsegmentacion":
        tipo_contenido = datos.get('tipo', '')
        eng = datos.get('engagement', 0)
        patron = datos.get('patron', '')
        if patron == 'ALTO IMPACTO':
            return f"'{tipo_contenido}' genera {eng:,.0f} interacciones en promedio, por encima del resto de tipos de contenido."
        elif patron == 'BAJO IMPACTO':
            return f"'{tipo_contenido}' genera {eng:,.0f} interacciones en promedio, por debajo del resto."
        else:
            return f"'{tipo_contenido}' genera {eng:,.0f} interacciones en promedio, dentro del rango medio."

    elif tipo == "contexto_externo":
        n_neg = datos.get('negativas', 0)
        n_total = datos.get('total', 0)
        fuente_top = datos.get('fuente_top', '')
        pct_neg_ext = (n_neg/n_total*100) if n_total > 0 else 0
        return f"En medios externos, {pct_neg_ext:.0f}% de las menciones son negativas. La fuente más activa es '{fuente_top}'."

    return ""


def safe_query(query: str, db_path: str, params=None) -> pd.DataFrame:
    """Lee SQL devolviendo un DataFrame vacío si la DB/tabla no existe o la query falla."""
    if not os.path.exists(db_path):
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as conn:
            return pd.read_sql_query(query, conn, params=params)
    except Exception as e:
        logging.warning(f"safe_query falló ({db_path}): {e}")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def cargar_externos(db_path):
    posts = safe_query("SELECT * FROM external_posts", db_path)
    if posts.empty:
        return posts
    posts['created_time'] = pd.to_datetime(posts['created_time'], errors='coerce')
    sent = safe_query("SELECT * FROM external_sentimiento", db_path)
    if not sent.empty:
        return posts.merge(sent, on='post_id', how='left')
    posts['score_sentimiento'] = 0.0
    posts['comentario_mas_negativo'] = ''
    return posts


@st.cache_data(ttl=3600, show_spinner=False)
def calcular_contagio_emocional(df_fb):
    """Pure transformation: recibe df_fb ya cargado y filtrado (con columnas:
    post_id, created_time, score_emocional, indice_amor, indice_humor,
    indice_tristeza, total_reacciones, message, categoria_nombre, score_sentimiento,
    pct_positivo, pct_negativo).
    No hace consultas SQL ni filtro de fecha — eso se hace en cargar_engagement_periodo.
    Devuelve (df_posts, conteo_tipos, distorsion_alta, por_semana).
    """
    if df_fb is None or df_fb.empty:
        return pd.DataFrame(), {}, pd.DataFrame(), pd.DataFrame()

    # Asegurar columnas necesarias
    req = ["post_id", "created_time", "score_emocional", "sent_comentarios",
           "pct_positivo", "pct_negativo", "categoria_nombre", "message"]
    for c in req:
        if c not in df_fb.columns:
            return pd.DataFrame(), {}, pd.DataFrame(), pd.DataFrame()

    df_posts = df_fb.copy()
    df_posts["created_time"] = pd.to_datetime(
        df_posts["created_time"], errors="coerce"
    )
    df_posts["semana"] = df_posts["created_time"].dt.to_period("W").dt.start_time
    df_posts = df_posts.dropna(subset=["created_time"])

    df_posts["distorsion"] = (
        df_posts["score_emocional"] - df_posts["sent_comentarios"]
    )

    umbral_pos = df_posts["score_emocional"].quantile(0.75)
    umbral_neg = df_posts["score_emocional"].quantile(0.25)

    def clasificar_contagio(row):
        em = row.get("score_emocional", 0) or 0
        sent = row.get("sent_comentarios", 0) or 0
        dist = row.get("distorsion", 0) or 0

        if pd.isna(em) or pd.isna(sent):
            return "sin_datos", "Sin datos suficientes"

        if em >= umbral_pos and sent >= umbral_pos:
            return "resonancia_positiva", "Resonancia positiva"
        elif em >= umbral_pos and sent <= umbral_neg:
            return "rechazo_a_positivo", "Rechazo a mensaje positivo"
        elif em <= umbral_neg and sent <= umbral_neg:
            return "resonancia_negativa", "Resonancia negativa"
        elif em <= umbral_neg and sent >= umbral_pos:
            return "inversion_positiva", "Inversión positiva"
        elif abs(dist) > 0.3:
            return "distorsion_alta", "Alta distorsión narrativa"
        else:
            return "neutral", "Respuesta neutral"

    df_posts["tipo_contagio"] = df_posts.apply(
        lambda r: clasificar_contagio(r)[0], axis=1
    )
    df_posts["label_contagio"] = df_posts.apply(
        lambda r: clasificar_contagio(r)[1], axis=1
    )

    conteo_tipos = df_posts["tipo_contagio"].value_counts().to_dict()

    distorsion_alta = df_posts[
        df_posts["tipo_contagio"] == "rechazo_a_positivo"
    ].nlargest(5, "distorsion")[
        ["post_id", "created_time", "message",
         "score_emocional", "sent_comentarios",
         "distorsion", "categoria_nombre"]
    ]

    por_semana = df_posts.groupby("semana").agg(
        score_post=("score_emocional", "mean"),
        score_comentarios=("sent_comentarios", "mean"),
        distorsion_prom=("distorsion", "mean")
    ).reset_index().dropna()

    return df_posts, conteo_tipos, distorsion_alta, por_semana


