"""Capa de datos y metricas del dashboard (extraida de app.py).

Contiene consultas SQL seguras, carga de engagement/sentimiento/series,
clculos (semaforo, patrones, confianza, narrativas, contagio, viralidad,
correlacion) y la capa de narrativa IA (Groq). Las rutas de BD activas se
resuelven en tiempo de ejecucion via _activas().
"""

import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import os
import json

from config import (
    FACEBOOK_DB, TIKTOK_DB, EXTERNOS_DB,
)
from dashboard.llm_groq import chat_texto, groq_disponible


def _activas():
    """Devuelve (FACEBOOK_DB, TIKTOK_DB, EXTERNOS_DB)."""
    return (FACEBOOK_DB, TIKTOK_DB, EXTERNOS_DB)


@st.cache_data(ttl=3600, show_spinner=False)
def generar_narrativa_ia(tipo: str, contexto: dict) -> str:
    """
    Genera narrativa ejecutiva usando Groq (Llama 3.3 70B).
    Tipos: 'eco_historico', 'leccion', 'brecha', 'contexto',
           'correlacion', 'proyeccion', 'recomendacion'
    """
    if not groq_disponible():
        return "Análisis IA no disponible en este momento (falta GROQ_API_KEY en .streamlit/secrets.toml o variable de entorno)"

    reglas_comunes = (
        " REGLAS OBLIGATORIAS DE SALIDA: "
        "(1) Tono crudo y directo, sin eufemismos, sin adjetivos vacíos y sin frases de relleno. "
        "(2) PROHIBIDO mencionar 'reelección', 'campaña', 'propaganda', 'voto', 'candidato' o sugerir "
        "cualquier estrategia electoral o de propaganda; esto es un análisis de gestión y percepción "
        "ciudadana, NO de campaña. No recomiendes 'publicar más obras' ni acciones de imagen. "
        "(3) Cada afirmación debe respaldarse con cifras concretas del contexto (porcentajes, conteos, "
        "reacciones, comentarios, vistas). No escribas generalidades sin un número que las sostenga. "
        "(4) Cuando el dato exista, nombra zonas, colonias, cantones o categorías concretas. "
        "No inventes datos que no estén en el contexto."
    )

    prompts = {
        "eco_historico": (
            "Eres analista de percepción ciudadana para la Alcaldía de Santa Ana. "
            "Dado el contexto de métricas de percepción de la semana, escribe un párrafo ejecutivo "
            "(máx 120 palabras) que explique qué patrón histórico o 'eco' del pasado "
            "resuena con la situación actual y qué implica para la gestión. Español."
        ),
        "leccion": (
            "Eres analista de percepción ciudadana. Escribe un párrafo ejecutivo (máx 120 palabras) "
            "sintetizando la lección operativa clara que deja esta semana de datos. "
            "Qué NO repetir, qué replicar, sustentado en las cifras. Español."
        ),
        "brecha": (
            "Eres analista de percepción ciudadana. Escribe un párrafo ejecutivo (máx 120 palabras) "
            "sobre la brecha entre lo que la ciudadanía PERCIBE (sentimiento, temas, enojo) "
            "y la GESTIÓN REAL (obras, servicios, indicadores municipales — dato no disponible en BD, "
            "asume que existe). Confronta percepción vs realidad sin suavizar. Español."
        ),
        "contexto": (
            "Eres analista de percepción ciudadana. Escribe un párrafo ejecutivo (máx 120 palabras) "
            "explicando qué está pasando FUERA de las redes (eventos municipales, "
            "economía local, clima, noticias) que explica el sentimiento negativo detectado "
            "en comentarios. Usa solo el contexto implícito en los datos. Español."
        ),
        "correlacion": (
            "Eres analista de percepción ciudadana. Escribe un párrafo ejecutivo (máx 120 palabras) "
            "sobre la correlación entre TIPO DE CONTENIDO publicado y REACCIÓN CIUDADANA "
            "(brecha reacción vs comentario). Qué contenido genera desconexión. Diagnóstico preciso. Español."
        ),
        "proyeccion": (
            "Eres analista de percepción ciudadana. Escribe un párrafo ejecutivo (máx 120 palabras) "
            "proyectando el escenario a 2 semanas si la tendencia actual de sentimiento, "
            "engagement y narrativas se mantiene. Alerta temprana, sin alarmismo. Español."
        ),
        "recomendacion": (
            "Eres analista de percepción ciudadana. Escribe un párrafo ejecutivo (máx 120 palabras) "
            "con LA recomendación operativa única de la semana, sintetizando TODOS los indicadores: "
            "Pulso, Audiencia, Riesgo, Memoria. Qué hacer el lunes en términos de gestión y servicios "
            "concretos. Orden directa y ejecutable. Español."
        ),
    }

    prompt_base = prompts.get(tipo, prompts["recomendacion"]) + reglas_comunes
    ctx_str = json.dumps(contexto, ensure_ascii=False, default=str)[:3000]

    try:
        return chat_texto(
            f"{prompt_base}\n\nCONTEXTO (JSON):\n{ctx_str}",
            max_tokens=600,
            temperature=0.7,
            json=False,
        )
    except Exception:
        return "Análisis IA no disponible en este momento (error en llamada API)"


def generar_interpretacion(tipo, datos):
    score = datos.get('score', 0)
    pct_neg = datos.get('pct_negativo', 0)
    pct_pos = datos.get('pct_positivo', 0)
    enojo = datos.get('indice_enojo', 0)

    if tipo == "semaforo":
        if score >= 0.25:
            return f"{pct_pos:.0f}% de los comentarios son de apoyo. El {pct_neg:.0f}% son negativos. Las reacciones positivas superan a las negativas."
        elif score >= 0.10:
            return f"{pct_pos:.0f}% de los comentarios son positivos y {pct_neg:.0f}% negativos. El balance es ligeramente favorable pero con señales mixtas."
        elif score >= 0:
            return f"{pct_neg:.0f}% de los comentarios son negativos y el enojo representa el {enojo*100:.0f}% de las reacciones. Apoyo y rechazo están casi empatados."
        else:
            return f"ALERTA. El enojo es el {enojo*100:.0f}% de las reacciones. {pct_neg:.0f}% de los comentarios son negativos. Las reacciones adversas superan ampliamente a las positivas."

    elif tipo == "tema_critico":
        tema = datos.get('tema', '')
        reacciones = datos.get('reacciones', 0)
        return f"Aquí está el problema. '{tema}' concentra {reacciones:,} reacciones con {pct_neg:.0f}% de comentarios negativos. Cuando publicas sobre este tema, la ciudadanía responde con burla y enojo, no con apoyo. Hay una brecha entre lo que comunicas y lo que la gente vive en su colonia."

    elif tipo == "tema_positivo":
        tema = datos.get('tema', '')
        return f"'{tema}' es tu contenido más fuerte: el {pct_pos:.0f}% de comentarios son positivos y la gente lo comparte por cuenta propia. Aquí la ciudadanía se identifica, no solo consume lo que publicas."

    elif tipo == "anomalia":
        fecha = datos.get('fecha', '')
        views = datos.get('views', 0)
        tipo_pico = datos.get('tipo', 'positivo')
        if tipo_pico == 'positivo':
            return f"La semana del {fecha} fue inusual: {views:,} interacciones, muy por encima del promedio. Algo movilizó a la ciudadanía a tu favor. Identifica qué se publicó o qué evento ocurrió: ese es el contenido que conviene replicar."
        else:
            return f"La semana del {fecha} tuvo una caída inusual: más rechazo del habitual. Revisa qué se comunicó esa semana y qué pasó en el municipio en esas fechas."

    elif tipo == "patron_rechazo":
        nombre = datos.get('nombre', '')
        count = datos.get('count', 0)
        tendencia = datos.get('tendencia', '')
        return f"{count} personas expresaron este patrón con sus propias palabras. No es un comentario aislado: es una narrativa colectiva. Tendencia: {tendencia}. Cuando un patrón de rechazo crece semana a semana, se vuelve el reclamo dominante de la ciudadanía sobre tu gestión."

    elif tipo == "patron_respaldo":
        nombre = datos.get('nombre', '')
        count = datos.get('count', 0)
        return f"{count} personas expresaron apoyo genuino: no por obligación, sino porque algo resonó. Este es tu respaldo ciudadano real en redes. La diferencia entre apoyo genuino y apoyo vacío: el genuino se comparte, el vacío solo existe en el conteo."

    elif tipo == "microsegmentacion":
        tipo_contenido = datos.get('tipo', '')
        eng = datos.get('engagement', 0)
        patron = datos.get('patron', '')
        if patron == 'ALTO IMPACTO':
            return f"'{tipo_contenido}' es tu contenido más efectivo: genera {eng:,.0f} interacciones en promedio, por encima del resto. Cuando publicas esto, la ciudadanía responde."
        elif patron == 'BAJO IMPACTO':
            return f"'{tipo_contenido}' no está funcionando: solo {eng:,.0f} interacciones en promedio. La ciudadanía lo ignora o lo rechaza. Replantea cómo comunicas este tema."
        else:
            return f"'{tipo_contenido}' tiene impacto moderado ({eng:,.0f} interacciones en promedio). Hay potencial, pero algo en el mensaje no termina de conectar con la ciudadanía."

    elif tipo == "contexto_externo":
        n_neg = datos.get('negativas', 0)
        n_total = datos.get('total', 0)
        fuente_top = datos.get('fuente_top', '')
        pct_neg_ext = (n_neg/n_total*100) if n_total > 0 else 0
        return f"Fuera de tus redes, {pct_neg_ext:.0f}% de las menciones sobre ti son negativas. La fuente más activa es '{fuente_top}'. Lo que se dice fuera de tus páginas es lo que la ciudadanía lee cuando busca tu nombre, no lo que tú publicas."

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


def get_fecha_inicio(periodo):
    hoy = datetime.now()
    if periodo == "Esta semana": return hoy - timedelta(days=7)
    elif periodo == "Últimos 15 días": return hoy - timedelta(days=15)
    elif periodo == "Último mes": return hoy - timedelta(days=30)
    elif periodo == "Últimos 3 meses": return hoy - timedelta(days=90)
    else: return datetime(2020, 1, 1)


@st.cache_data(ttl=3600)
def cargar_fb_engagement(db_path):
    df = safe_query("""
        SELECT fe.*, pc.categoria_nombre
        FROM fb_engagement fe
        LEFT JOIN post_categorias pc ON fe.post_id = pc.item_id
    """, db_path)
    if df.empty:
        return df
    df['created_time'] = pd.to_datetime(df['created_time'], errors='coerce')
    df['categoria_nombre'] = df['categoria_nombre'].replace('Contenido promocional', 'Convocatorias y celebraciones')
    return df.dropna(subset=['created_time'])


@st.cache_data(ttl=3600)
def cargar_tk_engagement(tk_db_path, fb_db_path):
    df = safe_query("SELECT * FROM tiktok_engagement", tk_db_path)
    if df.empty:
        return df
    cats = safe_query("SELECT item_id, categoria_nombre FROM post_categorias", fb_db_path)
    if not cats.empty:
        cats['item_id'] = cats['item_id'].astype(str)
        df['id_str'] = df['id'].astype(str)
        df = df.merge(cats, left_on='id_str', right_on='item_id', how='left')
        df = df.drop(columns=['id_str','item_id'], errors='ignore')
    df['categoria_nombre'] = df.get('categoria_nombre', pd.Series(dtype=str))
    df['categoria_nombre'] = df['categoria_nombre'].replace('Contenido promocional', 'Convocatorias y celebraciones')
    df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
    return df.dropna(subset=['created_at'])


@st.cache_data(ttl=3600)
def cargar_sentimiento_fb(db_path):
    df = safe_query("""
        SELECT fs.*, pc.categoria_nombre
        FROM fb_sentimiento fs
        LEFT JOIN post_categorias pc ON fs.post_id = pc.item_id
    """, db_path)
    return df


@st.cache_data(ttl=3600)
def cargar_comentarios_fb(db_path):
    df = safe_query("""
        SELECT fc.message, fc.post_id,
               fs.score_sentimiento,
               fs.pct_positivo, fs.pct_negativo,
               pc.categoria_nombre
        FROM fb_comments fc
        LEFT JOIN fb_sentimiento fs ON fc.post_id = fs.post_id
        LEFT JOIN post_categorias pc ON fc.post_id = pc.item_id
        WHERE fc.message IS NOT NULL
        AND fc.message != ''
        AND LENGTH(fc.message) > 10
    """, db_path)
    return df


def cargar_comentarios_negativos() -> pd.DataFrame:
    FACEBOOK_DB_ACTIVA, _, _ = _activas()
    return safe_query("""
        SELECT comment_id, message, sentiment, sentiment_score, topic_category, zona
        FROM fb_comments
        WHERE sentiment IN ('negativo', 'muy_negativo')
        AND message IS NOT NULL AND TRIM(message) <> ''
    """, FACEBOOK_DB_ACTIVA)


@st.cache_data(ttl=3600)
def cargar_series(fb_db_path, tk_db_path):
    df_fb = safe_query("SELECT * FROM series_facebook", fb_db_path)
    df_tk = safe_query("SELECT * FROM series_tiktok", tk_db_path)
    if df_fb.empty and df_tk.empty:
        return pd.DataFrame(), pd.DataFrame()
    if not df_fb.empty:
        df_fb['semana'] = pd.to_datetime(df_fb['semana'])
        df_fb['engagement'] = df_fb['engagement_promedio'] * df_fb['total_posts']
        df_fb['plataforma'] = 'Facebook'
    if not df_tk.empty:
        df_tk['semana'] = pd.to_datetime(df_tk['semana'])
        df_tk['engagement'] = df_tk['views_suma']
        df_tk['plataforma'] = 'TikTok'
    return df_fb, df_tk


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


def filtrar_por_periodo_plataforma(df_fb, df_tk, periodo, plataforma):
    fecha_inicio = get_fecha_inicio(periodo)
    if df_fb is not None and not df_fb.empty and 'created_time' in df_fb.columns:
        fb = df_fb[df_fb['created_time'] >= fecha_inicio].copy()
    else:
        fb = pd.DataFrame()
    if df_tk is not None and not df_tk.empty and 'created_at' in df_tk.columns:
        tk = df_tk[df_tk['created_at'] >= fecha_inicio].copy()
    else:
        tk = pd.DataFrame()
    if plataforma == "Facebook": return fb, pd.DataFrame()
    if plataforma == "TikTok": return pd.DataFrame(), tk
    return fb, tk


def calcular_semaforo(df_fb):
    if df_fb.empty: return "amarillo", "SIN DATOS — No hay suficientes datos esta semana"
    score = df_fb['score_emocional'].mean()
    if score >= 0.25: return "verde", "RESPALDO — La ciudadanía te respalda esta semana"
    elif score >= 0.10: return "amarillo", "MIXTO — Hay señales mixtas esta semana"
    else: return "rojo", "ALERTA — La ciudadanía está inquieta esta semana"


def detectar_patrones_comentarios(df_comentarios):
    patrones_rechazo = {
        'abandono_territorial': {
            'keywords': ['calle', 'colonia', 'barrio', 'paviment',
                        'abandon', 'olvidado', 'espera', 'nunca vienen'],
            'nombre': 'Abandono territorial',
            'descripcion': 'Colonias y comunidades que se sienten ignoradas'
        },
        'desconfianza': {
            'keywords': ['corrupto', 'mentira', 'robo', 'ladron',
                        'nefasto', 'inutil', 'pura propaganda'],
            'nombre': 'Desconfianza institucional',
            'descripcion': 'Ciudadanos que cuestionan la honestidad de la gestion'
        },
        'narrativa_electoral': {
            'keywords': ['eleccion', 'voto', 'reeleccion', 'campana',
                        'boto', 'votar', 'elecciones', 'proximas'],
            'nombre': 'Narrativa electoral activa',
            'descripcion': 'Ciudadanos que leen las acciones en clave electoral'
        },
        'servicios_basicos': {
            'keywords': ['basura', 'alumbrado', 'lampara', 'luz',
                        'agua', 'telefono', 'atencion'],
            'nombre': 'Falla en servicios basicos',
            'descripcion': 'Quejas sobre servicios municipales sin respuesta'
        }
    }
    patrones_respaldo = {
        'reconocimiento_obras': {
            'keywords': ['excelente', 'buen trabajo', 'gracias',
                        'bendicion', 'felicitaciones', 'sigan'],
            'nombre': 'Reconocimiento de obras visibles',
            'descripcion': 'Ciudadanos que valoran los resultados concretos'
        },
        'identidad_local': {
            'keywords': ['orgulloso', 'santa ana', 'santaneco',
                        'fas', 'deporte', 'cultura', 'identidad'],
            'nombre': 'Conexion con identidad local',
            'descripcion': 'Ciudadanos que se identifican con el municipio'
        }
    }
    resultados_rechazo = []
    resultados_respaldo = []

    df_neg = df_comentarios[
        df_comentarios['score_sentimiento'].notna() &
        (df_comentarios['score_sentimiento'] < -0.1)
    ].copy()

    df_pos = df_comentarios[
        df_comentarios['score_sentimiento'].notna() &
        (df_comentarios['score_sentimiento'] > 0.1)
    ].copy()

    for key, patron in patrones_rechazo.items():
        mask = df_neg['message'].str.lower().str.contains(
            '|'.join(patron['keywords']), na=False
        )
        comentarios_patron = df_neg[mask]
        if len(comentarios_patron) > 0:
            rep = str(comentarios_patron.iloc[0]['message'])
            otros = [str(x) for x in comentarios_patron.iloc[1:4]['message'].tolist()]
            cat = comentarios_patron['categoria_nombre'].mode()
            categoria = cat.iloc[0] if len(cat) > 0 else "General"
            resultados_rechazo.append({
                'nombre': patron['nombre'],
                'descripcion': patron['descripcion'],
                'count': len(comentarios_patron),
                'representativo': rep,
                'otros': otros,
                'categoria': categoria,
                'tendencia': 'Creciendo' if len(comentarios_patron) > 20
                            else 'Estable'
            })

    for key, patron in patrones_respaldo.items():
        mask = df_pos['message'].str.lower().str.contains(
            '|'.join(patron['keywords']), na=False
        )
        comentarios_patron = df_pos[mask]
        if len(comentarios_patron) > 0:
            rep = str(comentarios_patron.iloc[0]['message'])
            otros = [str(x) for x in comentarios_patron.iloc[1:4]['message'].tolist()]
            cat = comentarios_patron['categoria_nombre'].mode()
            categoria = cat.iloc[0] if len(cat) > 0 else "General"
            resultados_respaldo.append({
                'nombre': patron['nombre'],
                'descripcion': patron['descripcion'],
                'count': len(comentarios_patron),
                'representativo': rep,
                'otros': otros,
                'categoria': categoria,
                'tendencia': 'Estable' if len(comentarios_patron) > 50
                            else 'Creciendo'
            })

    return resultados_rechazo, resultados_respaldo


@st.cache_data(ttl=3600)
def calcular_confianza_institucional():
    FACEBOOK_DB_ACTIVA, _, _ = _activas()
    df = safe_query("""
        SELECT fc.message, fc.post_id,
               fs.score_sentimiento,
               pc.categoria_nombre
        FROM fb_comments fc
        LEFT JOIN fb_sentimiento fs ON fc.post_id = fs.post_id
        LEFT JOIN post_categorias pc ON fc.post_id = pc.item_id
        WHERE fc.message IS NOT NULL
        AND LENGTH(fc.message) > 10
    """, FACEBOOK_DB_ACTIVA)
    if df.empty:
        return {}, 0, ("", {"score": 0})

    dimensiones = {
        'honestidad': {
            'trust': ['honesto','transparente','cumple','palabra',
                     'verdad','confiable','serio','responsable'],
            'distrust': ['corrupto','mentira','roba','ladron',
                        'trampa','engaño','deshonesto','fraude',
                        'corrucion','corrupto']
        },
        'competencia': {
            'trust': ['capaz','eficiente','trabaja','logro',
                     'resultado','avance','progreso','gestiona',
                     'resuelve','soluciona'],
            'distrust': ['inutil','incapaz','incompetente','nefasto',
                        'no sirve','mal trabajo','pésimo','fracaso',
                        'no hace nada','abandono']
        },
        'presencia': {
            'trust': ['presente','cercano','visita','recorre',
                     'atiende','responde','llega','aparece'],
            'distrust': ['ausente','no aparece','no viene',
                        'desaparecido','no atiende','ignoramos',
                        'olvidados','no llega']
        },
        'integridad': {
            'trust': ['justo','equitativo','todos','comunidades',
                     'igual','imparcial','beneficia'],
            'distrust': ['favoritismo','solo algunos','donde conviene',
                        'preferidos','discrimina','desigual',
                        'olvidadas','nada mas']
        }
    }

    resultados = {}
    for dim, palabras in dimensiones.items():
        trust_mask = df['message'].str.lower().str.contains(
            '|'.join(palabras['trust']), na=False
        )
        distrust_mask = df['message'].str.lower().str.contains(
            '|'.join(palabras['distrust']), na=False
        )
        n_trust = trust_mask.sum()
        n_distrust = distrust_mask.sum()
        total = n_trust + n_distrust
        if total > 0:
            score = (n_trust - n_distrust) / total
        else:
            score = 0
        ejemplos_raw = df[distrust_mask]['message'].tolist()
        ejemplos_dedup = list(dict.fromkeys(ejemplos_raw))[:3]
        resultados[dim] = {
            'trust': int(n_trust),
            'distrust': int(n_distrust),
            'score': float(score),
            'comentarios_distrust': ejemplos_dedup
        }

    total_trust_global = sum(d['trust'] for d in resultados.values())
    total_distrust_global = sum(d['distrust'] for d in resultados.values())

    if total_distrust_global > 0:
        ratio_global = total_trust_global / total_distrust_global
    else:
        ratio_global = total_trust_global  # sin desconfianza → confianza perfecta

    if ratio_global >= 2.0:
        score_global = 1.0
    elif ratio_global >= 1.0:
        score_global = 0.5
    elif ratio_global >= 0.5:
        score_global = 0.0
    else:
        score_global = -0.5

    dim_riesgo = min(resultados.items(), key=lambda x: x[1]['score'])

    return resultados, score_global, dim_riesgo


@st.cache_data(ttl=3600)
def calcular_narrativas_activas():
    FACEBOOK_DB_ACTIVA, _, _ = _activas()
    df = safe_query("""
        SELECT fc.message, fc.post_id,
               fe.created_time,
               fs.score_sentimiento,
               pc.categoria_nombre
        FROM fb_comments fc
        LEFT JOIN fb_engagement fe ON fc.post_id = fe.post_id
        LEFT JOIN fb_sentimiento fs ON fc.post_id = fs.post_id
        LEFT JOIN post_categorias pc ON fc.post_id = pc.item_id
        WHERE fc.message IS NOT NULL
        AND LENGTH(fc.message) > 10
    """, FACEBOOK_DB_ACTIVA)
    if df.empty:
        return {}

    df['created_time'] = pd.to_datetime(df['created_time'], errors='coerce')
    df['semana'] = df['created_time'].dt.to_period('W').dt.start_time

    narrativas = {
        'abandono_territorial': {
            'nombre': 'Abandono territorial',
            'descripcion': 'La ciudadanía siente que ciertas zonas o '
                          'colonias son ignoradas sistemáticamente',
            'keywords': ['colonia','barrio','calle','canton','comunidad',
                        'abandon','olvidado','nunca vienen','no llegan',
                        'esperando','años esperando'],
            'color': '#ef4444',
            'icono': '[ABANDONO]'
        },
        'promesas_incumplidas': {
            'nombre': 'Promesas incumplidas',
            'descripcion': 'Menciones de compromisos que el alcalde '
                          'hizo y que la ciudadanía percibe como no cumplidos',
            'keywords': ['prometio','prometieron','prometido','dijeron',
                        'para cuando','cuando van','siguen igual',
                        'nunca','años prometiendo','todavia'],
            'color': '#f59e0b',
            'icono': '[PROMESA]'
        },
        'narrativa_electoral': {
            'nombre': 'Narrativa electoral',
            'descripcion': 'La ciudadanía interpreta las acciones '
                          'del alcalde en clave de campaña electoral',
            'keywords': ['eleccion','voto','reeleccion','campaña',
                        'boto','votar','candidato','proximas',
                        'solo cuando hay','interesa el voto'],
            'color': '#8b5cf6',
            'icono': '[ELECTORAL]'
        },
        'corrupcion': {
            'nombre': 'Narrativa de corrupción',
            'descripcion': 'Señalamientos directos o indirectos '
                          'sobre manejo irregular de recursos',
            'keywords': ['corrupto','robo','ladron','dinero','fondos',
                        'recursos','licitacion','contrato','empleados',
                        'enchufado','nepotismo','millones'],
            'color': '#dc2626',
            'icono': '[CORRUPCIÓN]'
        },
        'reconocimiento': {
            'nombre': 'Reconocimiento ciudadano',
            'descripcion': 'Narrativa positiva — ciudadanos que '
                          'defienden y reconocen la gestión',
            'keywords': ['excelente','buen trabajo','gracias alcalde',
                        'sigan adelante','lo apoyamos','felicitaciones',
                        'bien hecho','orgullo','progreso','cambio'],
            'color': '#22c55e',
            'icono': '[RECONOCIMIENTO]'
        }
    }

    resultados = {}
    for key, narr in narrativas.items():
        mask = df['message'].str.lower().str.contains(
            '|'.join(narr['keywords']), na=False
        )
        df_narr = df[mask].copy()

        if not df_narr.empty and 'semana' in df_narr.columns:
            por_semana = df_narr.groupby('semana').size().reset_index(
                name='count'
            ).sort_values('semana')

            if len(por_semana) >= 4:
                recientes = por_semana.tail(4)['count'].mean()
                anteriores = por_semana.iloc[-8:-4]['count'].mean() if len(por_semana) >= 8 else por_semana.head(4)['count'].mean()
                if anteriores > 0:
                    cambio_pct = ((recientes - anteriores) / anteriores) * 100
                else:
                    cambio_pct = 0
            else:
                cambio_pct = 0
                por_semana = pd.DataFrame({'semana':[],'count':[]})
        else:
            cambio_pct = 0
            por_semana = pd.DataFrame({'semana':[],'count':[]})

        if cambio_pct > 20:
            tendencia = '↑ Creciendo'
            tend_color = '#ef4444' if key != 'reconocimiento' else '#22c55e'
        elif cambio_pct < -20:
            tendencia = '↓ Bajando'
            tend_color = '#22c55e' if key != 'reconocimiento' else '#ef4444'
        else:
            tendencia = '→ Estable'
            tend_color = '#6b7280'

        resultados[key] = {
            **narr,
            'total': len(df_narr),
            'cambio_pct': cambio_pct,
            'tendencia': tendencia,
            'tend_color': tend_color,
            'por_semana': por_semana,
            'ejemplos': list(dict.fromkeys(df_narr['message'].tolist()))[:3]
        }

    return resultados


@st.cache_data(ttl=3600)
def calcular_contagio_emocional():
    FACEBOOK_DB_ACTIVA, _, _ = _activas()
    df_posts = safe_query("""
        SELECT fe.post_id,
               fe.created_time,
               fe.score_emocional,
               fe.indice_amor,
               fe.indice_humor,
               fe.indice_tristeza,
               fe.total_reacciones,
               fe.message,
               pc.categoria_nombre,
               fs.score_sentimiento as sent_comentarios,
               fs.pct_positivo,
               fs.pct_negativo
        FROM fb_engagement fe
        LEFT JOIN post_categorias pc ON fe.post_id = pc.item_id
        LEFT JOIN fb_sentimiento fs ON fe.post_id = fs.post_id
        WHERE 1=1
    """, FACEBOOK_DB_ACTIVA)
    if df_posts.empty:
        return pd.DataFrame(), {}, pd.DataFrame(), pd.DataFrame()

    df_posts['created_time'] = pd.to_datetime(
        df_posts['created_time'], errors='coerce'
    )
    df_posts['semana'] = df_posts['created_time'].dt.to_period('W').dt.start_time

    df_posts['distorsion'] = (
        df_posts['score_emocional'] - df_posts['sent_comentarios']
    )

    umbral_pos = df_posts['score_emocional'].quantile(0.75)
    umbral_neg = df_posts['score_emocional'].quantile(0.25)

    def clasificar_contagio(row):
        em = row.get('score_emocional', 0) or 0
        sent = row.get('sent_comentarios', 0) or 0
        dist = row.get('distorsion', 0) or 0

        if pd.isna(em) or pd.isna(sent):
            return 'sin_datos', 'Sin datos suficientes'

        if em >= umbral_pos and sent >= umbral_pos:
            return 'resonancia_positiva', 'Resonancia positiva'
        elif em >= umbral_pos and sent <= umbral_neg:
            return 'rechazo_a_positivo', 'Rechazo a mensaje positivo'
        elif em <= umbral_neg and sent <= umbral_neg:
            return 'resonancia_negativa', 'Resonancia negativa'
        elif em <= umbral_neg and sent >= umbral_pos:
            return 'inversion_positiva', 'Inversión positiva'
        elif abs(dist) > 0.3:
            return 'distorsion_alta', 'Alta distorsión narrativa'
        else:
            return 'neutral', 'Respuesta neutral'

    df_posts['tipo_contagio'] = df_posts.apply(
        lambda r: clasificar_contagio(r)[0], axis=1
    )
    df_posts['label_contagio'] = df_posts.apply(
        lambda r: clasificar_contagio(r)[1], axis=1
    )

    conteo_tipos = df_posts['tipo_contagio'].value_counts().to_dict()

    distorsion_alta = df_posts[
        df_posts['tipo_contagio'] == 'rechazo_a_positivo'
    ].nlargest(5, 'distorsion')[
        ['post_id','created_time','message',
         'score_emocional','sent_comentarios',
         'distorsion','categoria_nombre']
    ]

    por_semana = df_posts.groupby('semana').agg(
        score_post=('score_emocional','mean'),
        score_comentarios=('sent_comentarios','mean'),
        distorsion_prom=('distorsion','mean')
    ).reset_index().dropna()

    return df_posts, conteo_tipos, distorsion_alta, por_semana


def calcular_score_emocional_neto(min_reacciones: int = 0) -> pd.DataFrame:
    """Score emocional neto por post (Módulo 3 del blueprint).
    Lee fb_posts (reacciones/shares/views reales) + fb_sentimiento (sentimiento por post)."""
    FACEBOOK_DB_ACTIVA, _, _ = _activas()
    posts = safe_query("""
        SELECT post_id, page_name, message, created_time,
               likes_count, loves_count, cares_count, hahas_count, wows_count,
               sads_count, angrys_count, shares_count, views_count,
               comments_count, topic_category, zona
        FROM fb_posts
    """, FACEBOOK_DB_ACTIVA)
    if posts.empty:
        return pd.DataFrame()

    num_cols = ["likes_count", "loves_count", "cares_count", "hahas_count", "wows_count",
                "sads_count", "angrys_count", "shares_count", "views_count", "comments_count"]
    for c in num_cols:
        posts[c] = pd.to_numeric(posts[c], errors="coerce").fillna(0)

    posts["engagement_total"] = (
        posts["likes_count"] + posts["loves_count"] + posts["cares_count"] + posts["hahas_count"]
        + posts["wows_count"] + posts["sads_count"] + posts["angrys_count"]
        + posts["shares_count"]
    )
    posts["total_reacciones"] = (
        posts["likes_count"] + posts["loves_count"] + posts["cares_count"] + posts["hahas_count"]
        + posts["wows_count"] + posts["sads_count"] + posts["angrys_count"]
    )

    base = posts["engagement_total"].replace(0, pd.NA)
    posts["afecto_positivo"] = ((posts["loves_count"] + posts["wows_count"]) / base).fillna(0.0)
    posts["controversia"]    = ((posts["angrys_count"] + posts["sads_count"]) / base).fillna(0.0)

    sent = safe_query("""
        SELECT post_id, pct_positivo, pct_negativo, total_comentarios
        FROM fb_sentimiento
    """, FACEBOOK_DB_ACTIVA)
    if not sent.empty:
        for c in ["pct_positivo", "pct_negativo", "total_comentarios"]:
            sent[c] = pd.to_numeric(sent[c], errors="coerce").fillna(0)
        denom = 100.0 if sent[["pct_positivo", "pct_negativo"]].max().max() > 1.5 else 1.0
        sent["score_sent_norm"] = (sent["pct_positivo"] - sent["pct_negativo"]) / denom
        posts = posts.merge(sent[["post_id", "score_sent_norm", "total_comentarios"]],
                            on="post_id", how="left")
    else:
        posts["score_sent_norm"] = 0.0
        posts["total_comentarios"] = 0
    posts["score_sent_norm"] = posts["score_sent_norm"].fillna(0.0)
    posts["total_comentarios"] = posts["total_comentarios"].fillna(0)

    posts["score_emocional_neto"] = (
        posts["afecto_positivo"] - posts["controversia"] + (posts["score_sent_norm"] * 0.3)
    )

    return posts


def calcular_viralidad_tiktok(min_views: int = 0) -> pd.DataFrame:
    """Índice de viralidad de TikTok (Módulo 3, adaptado)."""
    _, TIKTOK_DB_ACTIVA, _ = _activas()
    df = safe_query("SELECT * FROM videos", TIKTOK_DB_ACTIVA)
    if df.empty:
        return pd.DataFrame()
    for c in ["views", "likes", "shares", "comments_count", "favorites_count"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0) if c in df.columns else 0
    if df.empty:
        return df
    v = df["views"].replace(0, pd.NA)
    df["indice_viralidad"] = (df["shares"] / v).fillna(0.0)
    df["engagement_rate"]  = ((df["likes"] + df["comments_count"] + df["shares"]) / v).fillna(0.0)
    label_col = next((c for c in ["descripcion", "description", "caption", "desc",
                                   "titulo", "title", "video_url", "url"] if c in df.columns), None)
    if label_col:
        df["video"] = df[label_col].astype(str).str.replace("\n", " ").str.slice(0, 80)
    else:
        df["video"] = "video " + df.index.astype(str)
    return df.sort_values("indice_viralidad", ascending=False)


def calcular_correlacion_noticias_picos(z_umbral: float = 1.0, ventana_dias: int = 3) -> dict:
    """Cruza picos de engagement de FB con noticias externas que coinciden en el tiempo.
    Es correlación TEMPORAL, no causalidad."""
    FACEBOOK_DB_ACTIVA, _, EXTERNOS_DB_ACTIVA = _activas()
    posts = safe_query("""
        SELECT created_time, likes_count, loves_count, cares_count, hahas_count, wows_count,
               sads_count, angrys_count, shares_count, comments_count
        FROM fb_posts
        WHERE created_time IS NOT NULL AND TRIM(created_time) <> ''
    """, FACEBOOK_DB_ACTIVA)
    if posts.empty:
        return {}
    react = ["likes_count", "loves_count", "cares_count", "hahas_count", "wows_count",
             "sads_count", "angrys_count", "shares_count", "comments_count"]
    for c in react:
        posts[c] = pd.to_numeric(posts[c], errors="coerce").fillna(0)
    posts["engagement"] = posts[react].sum(axis=1)
    posts["fecha"] = pd.to_datetime(posts["created_time"], errors="coerce", utc=True).dt.tz_localize(None)
    posts = posts.dropna(subset=["fecha"])
    if posts.empty:
        return {}
    posts["semana"] = posts["fecha"].dt.to_period("W-SUN").dt.start_time
    serie = posts.groupby("semana", as_index=False)["engagement"].sum().sort_values("semana")
    mu = serie["engagement"].mean()
    sd = serie["engagement"].std(ddof=0)
    serie["z"] = (serie["engagement"] - mu) / (sd if sd and sd > 0 else 1)
    serie["es_pico"] = serie["z"] >= z_umbral
    noticias = safe_query("""
        SELECT created_time, source, message, total_reactions, comments_count, post_url
        FROM external_posts
        WHERE created_time IS NOT NULL AND TRIM(created_time) <> ''
    """, EXTERNOS_DB_ACTIVA)
    if not noticias.empty:
        noticias["fecha"] = pd.to_datetime(noticias["created_time"], errors="coerce", utc=True).dt.tz_localize(None)
        noticias = noticias.dropna(subset=["fecha"])
    coincidencias = []
    for _, pk in serie[serie["es_pico"]].iterrows():
        wk = pk["semana"]
        if noticias is not None and not noticias.empty:
            mask = (noticias["fecha"] >= wk - pd.Timedelta(days=ventana_dias)) & \
                   (noticias["fecha"] <= wk + pd.Timedelta(days=7 + ventana_dias))
            for _, nt in noticias[mask].iterrows():
                coincidencias.append({
                    "semana_pico": wk.date().isoformat(),
                    "engagement": int(pk["engagement"]),
                    "z": round(float(pk["z"]), 2),
                    "fuente": str(nt.get("source", "") or ""),
                    "noticia": (str(nt.get("message", "") or ""))[:120],
                    "fecha_noticia": nt["fecha"].date().isoformat(),
                })
    return {"serie": serie, "coincidencias": pd.DataFrame(coincidencias),
            "n_picos": int(serie["es_pico"].sum())}
