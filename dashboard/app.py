import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re
from collections import Counter
import logging
import os
import sys
import json
import uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard"))
from config import (
    FACEBOOK_DB, TIKTOK_DB, EXTERNOS_DB,
    FACEBOOK_TEST_DB, TIKTOK_TEST_DB, EXTERNOS_TEST_DB,
    FB_PAGES_OFICIALES, FB_REACTIONS, TK_ENGAGEMENT,
    TK_ACCOUNTS, OUTPUT_DIR, MIN_COMENTARIOS_MUESTRA,
)
from dashboard.guardar_lote import guardar_lote
from dashboard.procesar_lote import procesar_pipeline
from dashboard.muestra import evaluar_muestra
from dashboard.sentimiento_engine import get_diagnostico_sentimiento

# ── Toggle modo prueba — antes de cualquier función cacheada ──
if "modo_prueba" not in st.session_state:
    st.session_state.modo_prueba = False

# ── Estado del lote de ingreso (Fase 1: solo en memoria) ──
if "lote_ingreso" not in st.session_state:
    st.session_state["lote_ingreso"] = []

FACEBOOK_DB_ACTIVA = (
    FACEBOOK_TEST_DB if st.session_state.get("modo_prueba", False) else FACEBOOK_DB
)
TIKTOK_DB_ACTIVA = (
    TIKTOK_TEST_DB if st.session_state.get("modo_prueba", False) else TIKTOK_DB
)
EXTERNOS_DB_ACTIVA = (
    EXTERNOS_TEST_DB if st.session_state.get("modo_prueba", False) else EXTERNOS_DB
)

# ═══════════════════════════════════════════
# CAPA DE IA — Groq (API compatible OpenAI)
# ═══════════════════════════════════════════

from dashboard.llm_groq import chat_texto, groq_disponible

@st.cache_data(ttl=3600, show_spinner=False)
def generar_narrativa_ia(tipo: str, contexto: dict) -> str:
    """
    Genera narrativa ejecutiva usando Groq (Llama 3.3 70B).
    Tipos: 'eco_historico', 'leccion', 'brecha', 'contexto',
           'correlacion', 'proyeccion', 'recomendacion'
    """
    if not groq_disponible():
        return "Análisis IA no disponible en este momento (falta GROQ_API_KEY en .streamlit/secrets.toml o variable de entorno)"
    
    prompts = {
        "eco_historico": (
            "Eres analista político senior para Alcaldía de Santa Ana. "
            "Dado el contexto de métricas de percepción de la semana, escribe un párrafo ejecutivo "
            "(máx 120 palabras) que explique qué patrón histórico o 'eco' del pasado "
            "resuena con la situación actual. Tono: directo, sin adjetivos vacíos, "
            "orientado a decisión de reelección. Español."
        ),
        "leccion": (
            "Eres analista político senior. Escribe un párrafo ejecutivo (máx 120 palabras) "
            "sintetizando la lección operativa clara que deja esta semana de datos. "
            "Qué NO repetir, qué replicar. Tono: brutal honestidad, acción inmediata. Español."
        ),
        "brecha": (
            "Eres analista político senior. Escribe un párrafo ejecutivo (máx 120 palabras) "
            "sobre la brecha entre lo que la ciudadanía PERCIBE (sentimiento, temas, enojo) "
            "y la GESTIÓN REAL (obras, servicios, indicadores municipales — dato no disponible en BD, "
            "asume que existe). Tono: confronta percepción vs realidad sin suavizar. Español."
        ),
        "contexto": (
            "Eres analista político senior. Escribe un párrafo ejecutivo (máx 120 palabras) "
            "explicando qué está pasando FUERA de las redes (eventos municipales, opositores, "
            "economía local, clima, noticias) que explica el sentimiento negativo detectado "
            "en comentarios. Usa solo el contexto implícito en los datos. Tono: discreto, informado. Español."
        ),
        "correlacion": (
            "Eres analista político senior. Escribe un párrafo ejecutivo (máx 120 palabras) "
            "sobre la correlación entre TIPO DE CONTENIDO publicado y REACCIÓN CIUDADANA "
            "(brecha reacción vs comentario). Qué contenido genera desconexión. Tono: diagnóstico preciso. Español."
        ),
        "proyeccion": (
            "Eres analista político senior. Escribe un párrafo ejecutivo (máx 120 palabras) "
            "proyectando el escenario a 2 semanas si la tendencia actual de sentimiento, "
            "engagement y narrativas se mantiene. Tono: alerta temprana, sin alarmismo. Español."
        ),
        "recomendacion": (
            "Eres analista político senior. Escribe un párrafo ejecutivo (máx 120 palabras) "
            "con LA recomendación estratégica única de la semana, sintetizando TODOS los indicadores: "
            "Pulso, Audiencia, Riesgo, Memoria. Qué hacer el lunes. Tono: orden directa, ejecutable. Español."
        ),
    }
    
    prompt_base = prompts.get(tipo, prompts["recomendacion"])
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
            return f"La ciudadanía te respalda. El {pct_pos:.0f}% de los comentarios son de apoyo — la gente está contenta con lo que ve en tus redes. Este es el momento de publicar más contenido de obras y logros."
        elif score >= 0.10:
            return f"Hay señales mixtas. Algunos te apoyan, otros empiezan a cuestionar. El {pct_neg:.0f}% de los comentarios son negativos — no es crisis todavía, pero la tendencia importa. Revisa qué temas generan más críticas esta semana."
        elif score >= 0:
            return f"Atención. El equilibrio entre apoyo y rechazo es frágil. El {pct_neg:.0f}% de los comentarios son negativos y el enojo representa el {enojo*100:.0f}% de las reacciones. La ciudadanía está observando — cualquier error se amplifica ahora."
        else:
            return f"ALERTA. La ciudadanía está en modo crítico. El enojo representa el {enojo*100:.0f}% de TODAS las reacciones — eso significa que por cada persona que apoya, hay varias que reaccionan con rechazo activo. El {pct_neg:.0f}% de los comentarios son negativos. Esto no es ruido — es una señal que históricamente precede pérdida de confianza electoral."

    elif tipo == "tema_critico":
        tema = datos.get('tema', '')
        reacciones = datos.get('reacciones', 0)
        return f"Aquí está el problema. '{tema}' concentra {reacciones:,} reacciones con {pct_neg:.0f}% de comentarios negativos. Cuando publicas sobre este tema, la ciudadanía responde principalmente con burla y enojo — no con apoyo. Esto indica una brecha entre lo que comunicas y lo que la gente experimenta en su colonia."

    elif tipo == "tema_positivo":
        tema = datos.get('tema', '')
        return f"'{tema}' es tu contenido más fuerte. El {pct_pos:.0f}% de comentarios son positivos — la gente comparte este tipo de contenido espontáneamente. Aquí la ciudadanía se identifica contigo, no solo consume lo que publicas."

    elif tipo == "anomalia":
        fecha = datos.get('fecha', '')
        views = datos.get('views', 0)
        tipo_pico = datos.get('tipo', 'positivo')
        if tipo_pico == 'positivo':
            return f"La semana del {fecha} fue inusual — {views:,} interacciones, muy por encima de tu promedio. Algo pasó esa semana que movilizó a la ciudadanía a tu favor. Identifica qué publicaste o qué evento ocurrió — ese es el tipo de contenido que debes replicar."
        else:
            return f"La semana del {fecha} tuvo una caída inusual. La ciudadanía reaccionó con más rechazo del habitual. Revisa qué comunicaste esa semana y qué pasó en el municipio en esas fechas."

    elif tipo == "patron_rechazo":
        nombre = datos.get('nombre', '')
        count = datos.get('count', 0)
        tendencia = datos.get('tendencia', '')
        return f"{count} personas expresaron este patrón con sus propias palabras. No es un comentario aislado — es una narrativa colectiva. Tendencia: {tendencia}. Cuando un patrón de rechazo crece semana a semana, eventualmente se convierte en el tema central que la oposición usará en campaña."

    elif tipo == "patron_respaldo":
        nombre = datos.get('nombre', '')
        count = datos.get('count', 0)
        return f"{count} personas expresaron apoyo genuino — no por obligación, sino porque algo resonó. Este es tu capital político real en redes. La diferencia entre apoyo genuino y apoyo vacío: el genuino se comparte, el vacío solo existe en el conteo."

    elif tipo == "microsegmentacion":
        tipo_contenido = datos.get('tipo', '')
        eng = datos.get('engagement', 0)
        patron = datos.get('patron', '')
        if patron == 'ALTO IMPACTO':
            return f"'{tipo_contenido}' es tu contenido más efectivo. Genera {eng:,.0f} interacciones en promedio — por encima del resto. Cuando publicas esto, la ciudadanía responde. Más de este contenido."
        elif patron == 'BAJO IMPACTO':
            return f"'{tipo_contenido}' no está funcionando. Solo {eng:,.0f} interacciones en promedio. La ciudadanía lo ignora o lo rechaza. Replantear cómo comunicas este tema."
        else:
            return f"'{tipo_contenido}' tiene impacto moderado. Hay potencial pero algo en el mensaje no termina de conectar con la ciudadanía."

    elif tipo == "contexto_externo":
        n_neg = datos.get('negativas', 0)
        n_total = datos.get('total', 0)
        fuente_top = datos.get('fuente_top', '')
        pct_neg_ext = (n_neg/n_total*100) if n_total > 0 else 0
        return f"Fuera de tus redes, {pct_neg_ext:.0f}% de las menciones sobre ti son negativas. La fuente más activa es '{fuente_top}'. Lo que dicen fuera de tus páginas es lo que la ciudadanía lee cuando busca tu nombre — no lo que tú publicas."

    return ""

def leyenda_grafica(elementos):
    items_html = "".join(
        '<div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:6px">'
        '<span style="font-size:14px;color:{};min-width:18px;font-weight:600;line-height:1.4;font-family:\'IBM Plex Mono\',monospace">'
        '{}</span>'
        '<div>'
        '<span style="font-size:11px;color:var(--fg-primary);font-weight:600;font-family:\'Inter\',sans-serif">'
        '{}</span>'
        '<span style="font-size:11px;color:var(--fg-muted);margin-left:4px;font-family:\'Inter\',sans-serif">'
        '— {}</span></div></div>'.format(
            e['color'], e['simbolo'], e['label'], e['descripcion']
        )
        for e in elementos
    )
    return (
        '<div style="background:var(--bg-card);border:1px solid var(--border);'
        'padding:12px 16px;margin-bottom:10px">'
        '<p style="font-size:9px;color:var(--fg-muted);margin:0 0 8px 0;'
        'font-weight:600;letter-spacing:1.5px;text-transform:uppercase;font-family:\'IBM Plex Mono\',monospace">'
        '◈ QUÉ ESTÁS VIENDO</p>{}</div>'
    ).format(items_html)

st.set_page_config(
    page_title="PANEL·SANTA ANA — Inteligencia Ciudadana",
    page_icon="\u2696",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
/* ═══════════════════════════════════════════
   BLOOMBERG-TERMINAL THEME
   Paleta ejecutiva oscura · tipografía mono
   Animaciones suaves · semáforo intuitivo
   ═══════════════════════════════════════════ */

@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

/* ── Tokens ── */
:root {
  --bg-base:      #0a0e17;
  --bg-surface:   #10141e;
  --bg-card:      #141822;
  --bg-elevated:  #1a1f2e;
  --fg-primary:   #e8e6e3;
  --fg-secondary: #9a9892;
  --fg-muted:     #5c5a55;
  --border:       #1e2332;
  --border-light: #2a2f3e;
  --accent:       #f0b34b;
  --accent-dim:   #a67c2e;
  --green:        #34d399;
  --green-dim:    #065f46;
  --red:          #f87171;
  --red-dim:      #7f1d1d;
  --amber:        #fbbf24;
  --amber-dim:    #713f12;
  --blue:         #60a5fa;
  --purple:       #a78bfa;
}

.stApp { background-color: var(--bg-base); color: var(--fg-primary); }
.stSidebar { background-color: var(--bg-surface); border-right: 1px solid var(--border); }
section[data-testid="stSidebar"] { background-color: var(--bg-surface); }

.stSelectbox > div > div {
  background-color: var(--bg-card);
  color: var(--fg-primary);
  border-color: var(--border-light);
  border-radius: 2px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
}
.stSelectbox > div > div:focus { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent-dim); }

.stRadio > div { color: var(--fg-primary); font-size: 12px; font-family: 'Inter', sans-serif; }
div[data-testid="stRadio"] label { font-size: 12px; }

/* ── Botón toggle ── */
div[data-testid="stToggle"] label { font-size: 12px; color: var(--fg-secondary); }
div[data-testid="stToggle"] > div[aria-checked="true"] {
  background-color: var(--accent-dim) !important;
}
div[data-testid="stMetric"] { background: var(--bg-card); border: 1px solid var(--border); border-radius: 2px; padding: 8px 12px; margin-bottom: 8px; }
div[data-testid="stMetricValue"] { font-family: 'IBM Plex Mono', monospace; font-size: 1.6rem !important; color: var(--fg-primary); }
div[data-testid="stMetricLabel"] { font-family: 'Inter', sans-serif; font-size: 0.7rem !important; color: var(--fg-muted); letter-spacing: 0.5px; text-transform: uppercase; }

/* ── Cards Bloomberg ── */
.bloom-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 2px;
  padding: 16px 20px;
  margin-bottom: 10px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.bloom-card:hover {
  border-color: var(--accent-dim);
  box-shadow: none;
}
.bloom-card-title {
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 1.8px;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin-bottom: 6px;
  font-family: 'Inter', sans-serif;
}
.bloom-card-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--fg-primary);
  font-family: 'IBM Plex Mono', monospace;
  line-height: 1.1;
  letter-spacing: -0.5px;
}
.bloom-card-sub {
  font-size: 11px;
  color: var(--fg-secondary);
  margin-top: 3px;
  font-family: 'Inter', sans-serif;
}
.bloom-border-accent { border-left: 3px solid var(--accent); }

/* ── Semáforo ejecutivo ── */
.semaforo-verde {
  background: linear-gradient(135deg, #052e16 0%, #0a3d1f 100%);
  border: 1px solid var(--green-dim);
  border-left: 4px solid var(--green);
  border-radius: 2px;
  padding: 20px 28px;
  text-align: center;
  margin-bottom: 18px;
  transition: opacity 0.3s ease;
}
.semaforo-amarillo {
  background: linear-gradient(135deg, #1c1407 0%, #2d1f07 100%);
  border: 1px solid var(--amber-dim);
  border-left: 4px solid var(--amber);
  border-radius: 2px;
  padding: 20px 28px;
  text-align: center;
  margin-bottom: 18px;
  transition: opacity 0.3s ease;
}
.semaforo-rojo {
  background: linear-gradient(135deg, #1a0505 0%, #2d0a0a 100%);
  border: 1px solid var(--red-dim);
  border-left: 4px solid var(--red);
  border-radius: 2px;
  padding: 20px 28px;
  text-align: center;
  margin-bottom: 18px;
  transition: opacity 0.3s ease;
}
.semaforo-texto {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.3px;
  margin: 0;
  font-family: 'Inter', sans-serif;
}
.semaforo-icono {
  font-size: 28px;
  display: block;
  margin-bottom: 6px;
}

/* ── Interpretación ── */
.interpretacion-box {
  background: var(--bg-card);
  border-left: 3px solid var(--accent);
  padding: 14px 18px;
  margin-bottom: 14px;
}
.interpretacion-label {
  font-size: 9px;
  color: var(--fg-muted);
  margin: 0 0 4px 0;
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  font-family: 'Inter', sans-serif;
}
.interpretacion-texto {
  font-size: 13px;
  color: var(--fg-primary);
  margin: 0;
  line-height: 1.7;
  font-family: 'Inter', sans-serif;
}

/* ── Section headers ── */
.seccion-header {
  border-bottom: 1px solid var(--border);
  padding-bottom: 10px;
  margin-bottom: 20px;
}
.seccion-titulo {
  font-size: 16px;
  font-weight: 700;
  color: var(--fg-primary);
  letter-spacing: 0.5px;
  font-family: 'Inter', sans-serif;
}
.seccion-subtitulo {
  font-size: 11px;
  color: var(--fg-muted);
  margin-top: 2px;
  font-family: 'Inter', sans-serif;
}

/* ── Patrones ── */
.patron-rechazo {
  background: #120808;
  border: 1px solid #3f1a1a;
  border-left: 4px solid var(--red);
  border-radius: 2px;
  padding: 18px 22px;
  margin-bottom: 14px;
}
.patron-respaldo {
  background: #071a0f;
  border: 1px solid #0a3d1f;
  border-left: 4px solid var(--green);
  border-radius: 2px;
  padding: 18px 22px;
  margin-bottom: 14px;
}
.patron-titulo { font-size: 12px; font-weight: 700; letter-spacing: 0.3px; margin-bottom: 4px; font-family: 'Inter', sans-serif; }
.patron-meta { font-size: 12px; color: var(--fg-secondary); margin-bottom: 10px; font-family: 'Inter', sans-serif; }
.patron-count { font-size: 24px; font-weight: 700; font-family: 'IBM Plex Mono', monospace; }

.comentario-rep {
  background: var(--bg-surface);
  border-left: 2px solid var(--border-light);
  padding: 10px 14px;
  font-size: 13px;
  font-style: italic;
  color: var(--fg-primary);
  margin: 6px 0;
  line-height: 1.5;
  font-family: 'Inter', sans-serif;
}
.comentario-lista { font-size: 11px; color: var(--fg-secondary); margin: 3px 0; padding-left: 10px; font-family: 'Inter', sans-serif; }

/* ── Badges ── */
.badge-positivo { background: var(--green-dim); color: var(--green); padding: 2px 7px; font-size: 10px; font-weight: 600; font-family: 'IBM Plex Mono', monospace; letter-spacing: 0.5px; }
.badge-mixto { background: var(--amber-dim); color: var(--amber); padding: 2px 7px; font-size: 10px; font-weight: 600; font-family: 'IBM Plex Mono', monospace; letter-spacing: 0.5px; }
.badge-critico { background: var(--red-dim); color: var(--red); padding: 2px 7px; font-size: 10px; font-weight: 600; font-family: 'IBM Plex Mono', monospace; letter-spacing: 0.5px; }

.riesgo-alto { color: var(--red); font-weight: 700; font-size: 11px; font-family: 'IBM Plex Mono', monospace; }
.riesgo-medio { color: var(--amber); font-weight: 700; font-size: 11px; font-family: 'IBM Plex Mono', monospace; }
.riesgo-bajo { color: var(--green); font-weight: 700; font-size: 11px; font-family: 'IBM Plex Mono', monospace; }

/* ── Señales ── */
.senal-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 2px;
  padding: 18px 22px;
  margin-bottom: 14px;
}
.senal-numero {
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 2px;
  color: var(--fg-muted);
  text-transform: uppercase;
  font-family: 'IBM Plex Mono', monospace;
}
.senal-titulo {
  font-size: 14px;
  font-weight: 700;
  color: var(--fg-primary);
  margin: 4px 0 10px 0;
  font-family: 'Inter', sans-serif;
}

/* ── Anomalía ── */
.anomalia-item {
  background: #120808;
  border: 1px solid #3f1a1a;
  border-radius: 2px;
  padding: 10px 14px;
  margin: 6px 0;
  font-size: 12px;
}

/* ── "Qué estás viendo" box ── */
.que-ves-box {
  background: var(--bg-surface);
  border-left: 2px solid var(--border-light);
  padding: 8px 12px;
  margin-bottom: 10px;
}
.que-ves-label {
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 1.5px;
  color: var(--fg-muted);
  text-transform: uppercase;
  font-family: 'IBM Plex Mono', monospace;
}
.que-ves-texto {
  font-size: 11px;
  color: var(--fg-secondary);
  margin: 3px 0 0 0;
  line-height: 1.5;
  font-family: 'Inter', sans-serif;
}

/* ── Tabla grid ── */
.tabla-grid {
  display: grid;
  padding: 8px 14px;
  border-bottom: 1px solid var(--border);
  font-size: 12px;
  align-items: center;
}
.tabla-header {
  padding: 8px 14px;
  border-bottom: 1px solid var(--border-light);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 1px;
  color: var(--fg-muted);
  text-transform: uppercase;
  font-family: 'IBM Plex Mono', monospace;
}
.tabla-numero {
  font-family: 'IBM Plex Mono', monospace;
  color: var(--blue);
  font-weight: 700;
}

/* ── Animaciones ── */
@keyframes blinkFadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes pulseGlow {
  0%, 100% { box-shadow: 0 0 0 rgba(240, 179, 75, 0); }
  50% { box-shadow: 0 0 6px rgba(240, 179, 75, 0.15); }
}
@keyframes cursorBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
@keyframes countUp {
  from { opacity: 0; }
  to { opacity: 1; }
}
.card-animate {
  animation: blinkFadeIn 0.4s ease both;
}
.semaforo-verde, .semaforo-amarillo, .semaforo-rojo {
  animation: blinkFadeIn 0.5s ease both;
}
.bloom-card {
  animation: blinkFadeIn 0.35s ease both;
}
.bloom-card:nth-child(2) { animation-delay: 0.05s; }
.bloom-card:nth-child(3) { animation-delay: 0.1s; }
.bloom-card:nth-child(4) { animation-delay: 0.15s; }
.bloom-card:nth-child(5) { animation-delay: 0.2s; }

/* ── Separador sutil ── */
/* ── Headings ── */
h1, h2, h3, h4 { font-family: 'Inter', sans-serif !important; color: var(--fg-primary) !important; letter-spacing: -0.02em; }
h1 { font-size: 1.4rem !important; font-weight: 700 !important; }
h2 { font-size: 1.15rem !important; font-weight: 600 !important; }
h3 { font-size: 1rem !important; font-weight: 600 !important; }
.stMarkdown { font-family: 'Inter', sans-serif; color: var(--fg-primary); }

/* ── Streamlit info/warning/error ── */
div[data-testid="stAlert"] { background: var(--bg-card) !important; border: 1px solid var(--border) !important; border-left: 3px solid var(--accent) !important; color: var(--fg-primary) !important; font-family: 'Inter', sans-serif; font-size: 12px !important; border-radius: 2px !important; }
div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p { font-size: 12px !important; color: var(--fg-primary) !important; }
.st-bd { background-color: transparent !important; }

/* ── Divider ── */
hr.stDivider { border-color: var(--border) !important; margin-top: 20px !important; margin-bottom: 20px !important; }

/* ── Caption ── */
.stCaption { color: var(--fg-muted) !important; font-family: 'IBM Plex Mono', monospace !important; font-size: 10px !important; }

/* ── Dataframes ── */
div[data-testid="stDataFrame"] { font-family: 'IBM Plex Mono', monospace; font-size: 11px; }
div[data-testid="stDataFrame"] td { background: var(--bg-surface) !important; color: var(--fg-primary) !important; border-color: var(--border) !important; }
div[data-testid="stDataFrame"] th { background: var(--bg-elevated) !important; color: var(--fg-muted) !important; border-color: var(--border) !important; font-size: 10px; letter-spacing: 0.5px; text-transform: uppercase; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: var(--border-light); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--fg-muted); }

/* ── Grid tables unificadas ── */
.grid-header {
  display: grid; padding: 10px 16px; border-bottom: 2px solid var(--border-light);
  font-size: 11px; font-weight: 600; letter-spacing: 1px;
  color: var(--fg-muted); text-transform: uppercase;
}
.grid-row {
  display: grid; padding: 14px 16px; border-bottom: 1px solid var(--border);
  font-size: 13px; align-items: center;
}
.grid-num {
  font-family: 'IBM Plex Mono', monospace; color: var(--blue); font-weight: 700;
}
.grid-label { font-weight: 600; color: var(--fg-primary); }
.grid-muted { color: var(--fg-secondary); }

/* ── Status boxes (reemplazo de st.info/st.warning) ── */
.bloom-status-info {
  background: var(--bg-card); border: 1px solid var(--border);
  border-left: 3px solid var(--blue); border-radius: 2px;
  padding: 12px 16px; margin-bottom: 14px;
  font-size: 12px; color: var(--fg-primary); font-family: 'Inter', sans-serif;
}
.bloom-status-warning {
  background: var(--bg-card); border: 1px solid var(--border);
  border-left: 3px solid var(--amber); border-radius: 2px;
  padding: 12px 16px; margin-bottom: 14px;
  font-size: 12px; color: var(--fg-primary); font-family: 'Inter', sans-serif;
}
.bloom-status-label {
  color: var(--amber); font-size: 10px; font-weight: 700;
  letter-spacing: 1px; text-transform: uppercase;
  font-family: 'IBM Plex Mono', monospace;
}

/* ── Subheader/caption Bloomberg ── */
.bloom-subheader {
  font-size: 15px; font-weight: 600; color: var(--fg-primary);
  font-family: 'Inter', sans-serif; letter-spacing: -0.02em; margin-bottom: 6px;
}
.bloom-caption {
  font-size: 10px; color: var(--fg-muted);
  font-family: 'IBM Plex Mono', monospace; margin-bottom: 14px;
}

/* ── Platform badge ── */
.plat-badge-fb {
  background: #1877f2; color: white; padding: 2px 8px;
  font-size: 10px; font-weight: 700; letter-spacing: 0.5px;
  font-family: 'IBM Plex Mono', monospace;
}
.plat-badge-tk {
  background: #ff0050; color: white; padding: 2px 8px;
  font-size: 10px; font-weight: 700; letter-spacing: 0.5px;
  font-family: 'IBM Plex Mono', monospace;
}
.cat-tag {
  background: var(--bg-elevated); color: var(--fg-muted);
  padding: 2px 8px; font-size: 10px;
  font-family: 'IBM Plex Mono', monospace;
}

/* ===== Responsive mobile (≤640px) ===== */
@media (max-width: 640px) {
  div[data-testid="stHorizontalBlock"] {
    flex-direction: column !important;
    gap: 0.4rem !important;
  }
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"],
  div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
    width: 100% !important;
    flex: 1 1 100% !important;
    min-width: 100% !important;
  }
  div[data-testid="stMetricValue"] { font-size: 1.3rem !important; }
  div[data-testid="stMetricLabel"] { font-size: 0.7rem !important; }
  .block-container { padding-left: 0.6rem !important; padding-right: 0.6rem !important; padding-top: 0.8rem !important; }
  h1 { font-size: 1.4rem !important; }
  h2 { font-size: 1.15rem !important; }
  h3 { font-size: 1rem !important; }
}
</style>
""", unsafe_allow_html=True)

# ── SIDEBAR ──

st.sidebar.markdown("""
<div style="border-bottom:1px solid var(--border);padding-bottom:12px;margin-bottom:12px">
  <div style="font-size:9px;letter-spacing:2px;color:var(--accent);font-weight:600;font-family:'IBM Plex Mono',monospace;text-transform:uppercase">PANEL·SANTA ANA</div>
  <div style="font-size:11px;color:var(--fg-muted);margin-top:2px;font-family:'Inter',sans-serif">Inteligencia Ciudadana</div>
</div>
""", unsafe_allow_html=True)

periodo = st.sidebar.selectbox("PERÍODO", [
    "Esta semana",
    "Últimos 15 días",
    "Último mes",
    "Últimos 3 meses",
    "Todo el período"
])

plataforma = st.sidebar.selectbox("PLATAFORMA", [
    "Ambas", "Facebook", "TikTok"
])

vista = st.sidebar.radio("VISTA", [
    "📊 Dashboard", "📥 Cargar contenido", "📋 Notas metodológicas"
])

st.sidebar.markdown("---")
modo_prueba = st.sidebar.toggle(
    "MODO PRUEBA",
    value=st.session_state.modo_prueba,
    help="Activa datos de prueba con alta negatividad para testear el semáforo rojo"
)
if modo_prueba != st.session_state.modo_prueba:
    st.session_state.modo_prueba = modo_prueba
    st.cache_data.clear()
    st.rerun()

if st.session_state.modo_prueba:
    st.sidebar.markdown(
        '<p style="color:var(--amber);font-size:10px;font-family:\'IBM Plex Mono\',monospace;letter-spacing:0.5px">'
        'TEST MODE</p>',
        unsafe_allow_html=True
    )

try:
    conn = sqlite3.connect(FACEBOOK_DB_ACTIVA)
    max_fb = pd.read_sql("SELECT MAX(created_time) as m FROM fb_engagement", conn).iloc[0]['m']
    conn.close()
    conn = sqlite3.connect(TIKTOK_DB_ACTIVA)
    max_tk = pd.read_sql("SELECT MAX(created_at) as m FROM tiktok_engagement", conn).iloc[0]['m']
    conn.close()
    fechas = []
    if max_fb: fechas.append(pd.Timestamp(max_fb))
    if max_tk: fechas.append(pd.Timestamp(max_tk))
    ultima_fecha = max(fechas) if fechas else datetime.now()
    dias = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
    meses = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
    fecha_str = f"{dias[ultima_fecha.weekday()]} {ultima_fecha.day} de {meses[ultima_fecha.month-1]}, {ultima_fecha.year}"
except:
    fecha_str = "No disponible"

st.sidebar.markdown(
    f'<p style="font-size:9px;color:var(--fg-muted);font-family:\'IBM Plex Mono\',monospace;letter-spacing:0.5px">'
    f'UPD: {fecha_str}</p>',
    unsafe_allow_html=True
)

st.sidebar.markdown("---")

with st.sidebar.expander("🔧 Diagnóstico"):
    st.caption("GROQ_API_KEY (visión + texto)")
    api_key_env = os.environ.get("GROQ_API_KEY")
    api_key_secrets = None
    try:
        api_key_secrets = st.secrets.get("GROQ_API_KEY")
    except Exception:
        pass
    if api_key_env:
        st.code("detectada (env)", language="text")
    elif api_key_secrets:
        st.code("detectada (secrets)", language="text")
    else:
        st.code("NO detectada", language="text")

    diag = get_diagnostico_sentimiento()
    st.caption("Motor de sentimiento")
    st.code(f"forzado: {diag['motor_forzado']}", language="text")
    st.code(f"bert_fallo: {diag['bert_fallo']}", language="text")
    if diag["ultimo_error_bert"]:
        st.code(f"último error BERT: {diag['ultimo_error_bert']}", language="text")
    if diag["ultimo_error_gemini"]:
        st.code(f"último error Gemini (sentimiento): {diag['ultimo_error_gemini']}", language="text")

# ── HELPERS ──

def get_fecha_inicio(periodo):
    hoy = datetime.now()
    if periodo == "Esta semana": return hoy - timedelta(days=7)
    elif periodo == "Últimos 15 días": return hoy - timedelta(days=15)
    elif periodo == "Último mes": return hoy - timedelta(days=30)
    elif periodo == "Últimos 3 meses": return hoy - timedelta(days=90)
    else: return datetime(2020, 1, 1)

def formato_fecha_espanol(fecha):
    dias = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
    meses = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
    try:
        if pd.isna(fecha): return "Fecha no disponible"
        d = pd.Timestamp(fecha)
        return f"{dias[d.weekday()]} {d.day} de {meses[d.month-1]}, {d.year}"
    except:
        return str(fecha)

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

def hay_datos(df, mensaje: str = "Aún no hay datos suficientes para esta sección.") -> bool:
    """Muestra un aviso elegante y devuelve False si el DataFrame está vacío."""
    if df is None or len(df) == 0:
        st.markdown(
            f'<div class="bloom-status-info"><span class="bloom-status-marker">●</span> {mensaje}</div>',
            unsafe_allow_html=True
        )
        return False
    return True


def card_explicativa(que_es: str, como_leerlo: str, ojo: str | None = None):
    """Tarjeta en lenguaje sencillo para explicar un gráfico al edil."""
    ojo_html = (
        f'<div style="margin-top:8px;font-size:11px;color:var(--amber);font-family:\'Inter\',sans-serif;border-top:1px solid var(--border);padding-top:6px">'
        f'<span style="font-weight:600">◈</span> {ojo}</div>'
        if ojo else ""
    )
    st.markdown(
        f"""
        <div class="interpretacion-box" style="margin:4px 0 16px 0">
            <div class="interpretacion-label">◈ CÓMO LEER ESTO</div>
            <div class="interpretacion-texto">
                <strong style="color:var(--accent)">Qué muestra:</strong> {que_es}<br>
                <strong style="color:var(--accent)">Cómo leerlo:</strong> {como_leerlo}
            </div>
            {ojo_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def que_ves_box(texto: str):
    """Caja QUÉ ESTÁS VIENDO en lenguaje ciudadano."""
    st.markdown(
        f'<div class="que-ves-box"><span class="que-ves-label">◈ QUÉ ESTÁS VIENDO</span>'
        f'<p class="que-ves-texto">{texto}</p></div>',
        unsafe_allow_html=True,
    )


def bloom_subheader(texto: str):
    """Reemplazo de st.subheader con estilo Bloomberg."""
    st.markdown(f'<p class="bloom-subheader">{texto}</p>', unsafe_allow_html=True)


def bloom_caption(texto: str):
    """Reemplazo de st.caption con estilo Bloomberg."""
    st.markdown(f'<p class="bloom-caption">{texto}</p>', unsafe_allow_html=True)


def bloom_metric(label: str, value: str, delta: str | None = None, color: str | None = None):
    """Tarjeta métrica compacta estilo Bloomberg."""
    val_color = f'color:{color};' if color else ''
    delta_html = f'<div class="bloom-card-sub">{delta}</div>' if delta else ''
    st.markdown(
        f'<div class="bloom-card { "bloom-border-accent" if color else "" }">'
        f'<div class="bloom-card-title">{label}</div>'
        f'<div class="bloom-card-value" style="{val_color}font-size:28px">{value}</div>'
        f'{delta_html}</div>',
        unsafe_allow_html=True,
    )


def plotly_bloom_theme(bg: str = "var(--bg-card)", fg: str = "var(--fg-secondary)"):
    """Tema oscuro Bloomberg para gráficas Plotly."""
    return dict(
        plot_bgcolor=bg, paper_bgcolor=bg,
        font=dict(color=fg, size=10, family='IBM Plex Mono, monospace'),
        xaxis=dict(gridcolor='var(--border)', showgrid=True, tickfont=dict(size=9)),
        yaxis=dict(gridcolor='var(--border)', showgrid=True, tickfont=dict(size=9)),
        margin=dict(l=0, r=0, t=10, b=0),
    )


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
        WHERE fe.total_reacciones >= 10
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

def calcular_score_emocional_neto(min_reacciones: int = 10) -> pd.DataFrame:
    """Score emocional neto por post (Módulo 3 del blueprint).
    Lee fb_posts (reacciones/shares/views reales) + fb_sentimiento (sentimiento por post)."""
    posts = safe_query("""
        SELECT post_id, page_name, message, created_time,
               likes_count, loves_count, hahas_count, wows_count,
               sads_count, angrys_count, shares_count, views_count,
               comments_count, topic_category, zona
        FROM fb_posts
    """, FACEBOOK_DB_ACTIVA)
    if posts.empty:
        return pd.DataFrame()

    num_cols = ["likes_count", "loves_count", "hahas_count", "wows_count",
                "sads_count", "angrys_count", "shares_count", "views_count", "comments_count"]
    for c in num_cols:
        posts[c] = pd.to_numeric(posts[c], errors="coerce").fillna(0)

    # engagement_total (blueprint): like + encanta + divierte + asombra + entristece + enoja + compartidos
    posts["engagement_total"] = (
        posts["likes_count"] + posts["loves_count"] + posts["hahas_count"]
        + posts["wows_count"] + posts["sads_count"] + posts["angrys_count"]
        + posts["shares_count"]
    )
    # total reacciones (sin shares) para la regla de exclusión <10
    posts["total_reacciones"] = (
        posts["likes_count"] + posts["loves_count"] + posts["hahas_count"]
        + posts["wows_count"] + posts["sads_count"] + posts["angrys_count"]
    )

    base = posts["engagement_total"].replace(0, pd.NA)
    # afecto positivo = encanta(loves) + asombra(wows) ; controversia = enoja(angrys) + entristece(sads)
    posts["afecto_positivo"] = ((posts["loves_count"] + posts["wows_count"]) / base).fillna(0.0)
    posts["controversia"]    = ((posts["angrys_count"] + posts["sads_count"]) / base).fillna(0.0)

    # score_sentimiento por post desde fb_sentimiento, normalizado a [-1, 1]
    sent = safe_query("""
        SELECT post_id, pct_positivo, pct_negativo, total_comentarios
        FROM fb_sentimiento
    """, FACEBOOK_DB_ACTIVA)
    if not sent.empty:
        for c in ["pct_positivo", "pct_negativo", "total_comentarios"]:
            sent[c] = pd.to_numeric(sent[c], errors="coerce").fillna(0)
        # detecta si los pct vienen en 0-100 o ya en 0-1
        denom = 100.0 if sent[["pct_positivo", "pct_negativo"]].max().max() > 1.5 else 1.0
        sent["score_sent_norm"] = (sent["pct_positivo"] - sent["pct_negativo"]) / denom
        posts = posts.merge(sent[["post_id", "score_sent_norm", "total_comentarios"]],
                            on="post_id", how="left")
    else:
        posts["score_sent_norm"] = 0.0
        posts["total_comentarios"] = 0
    posts["score_sent_norm"] = posts["score_sent_norm"].fillna(0.0)
    posts["total_comentarios"] = posts["total_comentarios"].fillna(0)

    # SCORE EMOCIONAL NETO (blueprint M3)
    posts["score_emocional_neto"] = (
        posts["afecto_positivo"] - posts["controversia"] + (posts["score_sent_norm"] * 0.3)
    )

    # regla del blueprint: solo posts con >= min_reacciones cuentan para proporciones
    posts["incluido_proporciones"] = posts["total_reacciones"] >= min_reacciones
    return posts

def calcular_viralidad_tiktok(min_views: int = 100) -> pd.DataFrame:
    """Índice de viralidad de TikTok (Módulo 3, adaptado).
    TikTok no tiene reacciones diferenciadas → medimos ALCANCE/propagación, no emoción."""
    df = safe_query("SELECT * FROM videos", TIKTOK_DB_ACTIVA)
    if df.empty:
        return pd.DataFrame()
    for c in ["views", "likes", "shares", "comments_count", "favorites_count"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0) if c in df.columns else 0
    df = df[df["views"] >= min_views].copy()
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
    """Cruza picos de engagement de FB (alcaldía) con noticias externas que coinciden en el tiempo.
    Es correlación TEMPORAL, no causalidad."""
    posts = safe_query("""
        SELECT created_time, likes_count, loves_count, hahas_count, wows_count,
               sads_count, angrys_count, shares_count, comments_count
        FROM fb_posts
        WHERE created_time IS NOT NULL AND TRIM(created_time) <> ''
    """, FACEBOOK_DB_ACTIVA)
    if posts.empty:
        return {}
    react = ["likes_count", "loves_count", "hahas_count", "wows_count",
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

# ═══════════════════════════════════════════
# SECCIÓN 1 — ESTADO GENERAL
# ═══════════════════════════════════════════

def render_notas_metodologicas():
    st.header("NOTAS METODOLÓGICAS")
    bloom_caption("Límites honestos del sistema — léelos antes de tomar decisiones con estos datos.")
    st.markdown(
        "Este panel analiza contenido público (posts, reacciones y comentarios) de las "
        "páginas de la Alcaldía y el alcalde. Es una herramienta de lectura de percepción "
        "colectiva, no un oráculo. Sus límites:"
    )
    st.markdown(
        '<div class="bloom-status-warning"><span class="bloom-status-label">LIMITACIÓN</span> '
        'No predice votos individuales. Mide qué temas generan qué emociones en '
        'conjunto, no el comportamiento de personas concretas.</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="bloom-status-info">Las reacciones son un proxy emocional, no un test psicológico validado. '
        'Úsalas como señal de tono colectivo, no como diagnóstico.</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="bloom-status-info">El sentimiento de comentarios tiene ~85% de precisión en español. '
        'Alrededor de 1 de cada 7 comentarios puede estar mal clasificado.</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="bloom-status-warning"><span class="bloom-status-label">LIMITACIÓN</span> '
        'Correlación ≠ causalidad. Que un pico de engagement coincida con una noticia '
        'externa no prueba que una haya causado la otra; pueden influir terceros factores.</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="bloom-status-info">TikTok no tiene reacciones diferenciadas (solo "me gusta"). Su lectura emocional '
        'depende 100% de los comentarios.</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="bloom-status-info">En Facebook, las reacciones con datos sólidos son "Me gusta", "Me encanta", '
        '"Me divierte" y "Me enoja". "Me asombra" y "Me entristece" aparecen en volúmenes '
        'mínimos (decenas de casos), así que las métricas de afecto/controversia se apoyan '
        'sobre todo en las primeras.</div>',
        unsafe_allow_html=True
    )
    bloom_caption(
        "Metodología inspirada en Kosinski et al. (2013), adaptada a datos agregados por "
        "publicación (no a perfiles individuales) y con las limitaciones señaladas por "
        "Farina et al. (2025)."
    )


# ═══════════════════════════════════════════
# SECCIÓN — 📥 Cargar contenido (Fase 1)
# ═══════════════════════════════════════════

# ═══════════════════════════════════════════════════
# Helpers de revisión (Fase 3)
# ═══════════════════════════════════════════════════

def _campo_numero(label: str, dato_confianza: dict, key_suffix: str, id_temporal: str) -> None:
    """Renderiza st.number_input con resaltado por confianza.

    confianza 'seguro' → normal
    confianza 'dudoso' → 🟡 + "revisar: lectura dudosa"
    confianza 'no_detectado' → 🟡 + "no detectado — completa a mano"
    confianza 'manual' → 🟡 + "se teclea a mano (no se confía al OCR)"
    """
    confianza = dato_confianza.get("confianza", "no_detectado")
    valor = dato_confianza.get("valor")
    key = f"rev_{key_suffix}_{id_temporal}"

    label_display = f"🟡 {label}" if confianza != "seguro" else label
    initial = valor if valor is not None else 0

    st.number_input(label_display, min_value=0, value=initial, step=1, key=key)
    if confianza == "dudoso":
        st.caption("revisar: lectura dudosa")
    elif confianza == "no_detectado":
        st.caption("no detectado — completa a mano")
    elif confianza == "manual":
        st.caption("se teclea a mano (no se confía al OCR)")


def _contrato_vacio(plataforma: str) -> dict:
    """Contrato vacío para rellenar a mano cuando la IA falla."""
    vacio = {"valor": None, "confianza": "no_detectado"}
    if plataforma == "facebook":
        return {
            "plataforma": "facebook",
            "texto_post": "",
            "fecha": {"valor": None, "confianza": "no_detectado"},
            "autor_pagina": None,
            "reacciones": {k: dict(vacio) for k in (
                "likes", "loves", "hahas", "sads", "wows", "angrys", "total"
            )},
            "comentarios_count": dict(vacio),
            "compartidos": {"valor": None, "confianza": "manual"},
            "vistas": {"valor": None, "confianza": "manual"},
            "comentarios": [],
        }
    elif plataforma == "tiktok":
        return {
            "plataforma": "tiktok",
            "texto_post": "",
            "fecha": {"valor": None, "confianza": "no_detectado"},
            "autor_cuenta": None,
            "metricas": {k: dict(vacio) for k in (
                "likes", "favoritos", "comentarios_count"
            )} | {
                "compartidos": {"valor": None, "confianza": "manual"},
                "vistas": {"valor": None, "confianza": "manual"},
            },
            "comentarios": [],
        }


# ═══════════════════════════════════════════════════
# Fase 3 — Revisión editable del lote
# ═══════════════════════════════════════════════════

def seccion_revisar_lote() -> None:
    """Pantalla de revisión editable post-extracción (Fase 3).

    Dispara extracción con Groq (Llama 4 Scout), muestra tarjetas editables
    con resaltado por confianza, y produce datos_revisados.
    """
    lote = st.session_state["lote_ingreso"]
    pendientes = [p for p in lote if p["estado"] == "pendiente"]
    extraidos = [p for p in lote if p["estado"] in ("extraido", "revisado")]
    errores = [p for p in lote if p["estado"] == "error"]

    if not pendientes and not extraidos and not errores:
        return

    # ── Paso 1: Botón de extracción ──
    if pendientes:
        st.markdown("### 🔍 Extracción con IA")
        st.caption(
            "Groq (Llama 4 Scout) leerá las capturas y extraerá texto, fechas, "
            "reacciones y comentarios. Los números borrosos o no visibles "
            "quedarán marcados para que los completes."
        )
        if st.button("🔍 Extraer y revisar lote", width='stretch', type="primary"):
            from ingreso_extraccion import extraer_posts_desde_archivos
            import uuid

            n = len(pendientes)
            status = st.status(f"Extrayendo datos de los archivos… 0/{n}", expanded=True)
            nuevos_items = []
            for item in st.session_state["lote_ingreso"]:
                if item.get("estado") != "pendiente":
                    nuevos_items.append(item)
                    continue

                resultado = extraer_posts_desde_archivos(item["imagenes"], item["plataforma"])

                if isinstance(resultado, dict) and resultado.get("error"):
                    item["estado"] = "error"
                    item["error_msg"] = resultado["error"]
                    nuevos_items.append(item)
                    continue

                posts = resultado.get("posts", [])
                if not posts:
                    item["estado"] = "error"
                    item["error_msg"] = "No se detectaron posts en el archivo"
                    nuevos_items.append(item)
                    continue

                for datos in posts:
                    enlace_auto = (datos.get("enlace") or {}).get("valor")
                    nuevos_items.append({
                        "id_temporal": str(uuid.uuid4()),
                        "plataforma": item["plataforma"],
                        "fuente": item["fuente"],
                        "imagenes": item["imagenes"],
                        "enlace": enlace_auto or item.get("enlace", ""),
                        "enlace_confianza": (datos.get("enlace") or {}).get("confianza", "no_detectado"),
                        "estado": "extraido",
                        "datos_extraidos": datos,
                    })

            st.session_state["lote_ingreso"] = nuevos_items
            n_total = sum(1 for p in nuevos_items if p["estado"] == "extraido")
            status.update(label=f"✅ Extracción completada ({n_total} posts)", state="complete", expanded=False)
            st.rerun()

    # ── Paso 2: Tarjetas editables ──
    if extraidos:
        st.markdown("### ✏️ Revisión y corrección")
        st.caption("Campos marcados con 🟡 requieren atención. Vistas y compartidos se teclean siempre a mano.")

        n_revisados = sum(1 for p in extraidos if p["estado"] == "revisado")
        if n_revisados:
            st.info(f"{n_revisados}/{len(extraidos)} posts confirmados hasta ahora.")

        for i, item in enumerate(extraidos):
            datos = item.get("datos_extraidos", {})
            is_error = "error" in datos
            is_revisado = item["estado"] == "revisado"
            id_ = item["id_temporal"]

            plat_emoji = "📘" if item["plataforma"] == "facebook" else "🎵"
            tag = "✅ Revisado" if is_revisado else "🟡 Pendiente"
            label = f"{plat_emoji} Post {i+1}: {item['fuente']} — {tag}"

            with st.expander(label, expanded=not is_revisado):
                conf = item.get("enlace_confianza", "no_detectado")
                if conf in ("dudoso", "no_detectado"):
                    st.warning("Revisa el enlace: no se detectó con seguridad en el PDF.")
                st.text_input(
                    "Enlace del post",
                    value=item.get("enlace", ""),
                    key=f"rev_enlace_{id_}",
                    help="Extraído automáticamente del PDF. Corrige si es necesario.",
                )

                if is_error:
                    st.error(f"⚠️ Groq no pudo leer esta captura: «{datos['error']}». Llénala a mano.")
                    datos = _contrato_vacio(item["plataforma"])

                with st.form(key=f"form_revision_{id_}"):
                    # ── Texto del post ──
                    texto_key = f"rev_texto_{id_}"
                    texto_val = datos.get("texto_post", "")
                    st.text_area("Texto del post / descripción", value=texto_val, key=texto_key)
                    if not texto_val:
                        st.caption("no se leyó texto, escríbelo si aplica")

                    # ── Fecha ──
                    fecha_key = f"rev_fecha_{id_}"
                    fecha_dato = datos.get("fecha", {"valor": None, "confianza": "no_detectado"})
                    fecha_conf = fecha_dato.get("confianza", "no_detectado")
                    fecha_label = "🟡 Fecha" if fecha_conf != "seguro" else "Fecha"
                    fv = fecha_dato.get("valor")
                    try:
                        fecha_init = datetime.strptime(fv, "%Y-%m-%d").date() if fv else None
                    except (ValueError, TypeError):
                        fecha_init = None
                    st.date_input(fecha_label, value=fecha_init, key=fecha_key)
                    if fecha_conf == "dudoso":
                        st.caption("revisar: lectura dudosa")
                    elif fecha_conf == "no_detectado":
                        st.caption("no detectado — completa a mano")

                    # ── Métricas según plataforma ──
                    if item["plataforma"] == "facebook":
                        reacs = datos.get("reacciones", {})
                        st.markdown("**Reacciones**")
                        cols = st.columns(3)
                        fb_order = [
                            ("likes", "Likes"), ("loves", "Me encanta"),
                            ("hahas", "Me divierte"), ("sads", "Me entristece"),
                            ("wows", "Me asombra"), ("angrys", "Me enoja"),
                        ]
                        for idx, (field, lbl) in enumerate(fb_order):
                            with cols[idx % 3]:
                                _campo_numero(lbl, reacs.get(field, {"valor": None, "confianza": "no_detectado"}),
                                              f"fb_{field}", id_)
                        _campo_numero("Total reacciones",
                                      reacs.get("total", {"valor": None, "confianza": "dudoso"}),
                                      "fb_total", id_)
                        _campo_numero("Comentarios (conteo)",
                                      datos.get("comentarios_count", {"valor": None, "confianza": "no_detectado"}),
                                      "fb_comentarios_count", id_)
                        st.markdown("**Campos manuales**")
                        c2 = st.columns(2)
                        with c2[0]:
                            _campo_numero("Compartidos", {"valor": None, "confianza": "manual"},
                                          "fb_compartidos", id_)
                        with c2[1]:
                            _campo_numero("Vistas", {"valor": None, "confianza": "manual"},
                                          "fb_vistas", id_)
                    else:  # TikTok
                        metrics = datos.get("metricas", {})
                        st.markdown("**Métricas**")
                        cols = st.columns(3)
                        tk_order = [
                            ("likes", "Likes"), ("favoritos", "Favoritos"),
                            ("comentarios_count", "Comentarios (conteo)"),
                        ]
                        for idx, (field, lbl) in enumerate(tk_order):
                            with cols[idx % 3]:
                                _campo_numero(lbl, metrics.get(field, {"valor": None, "confianza": "no_detectado"}),
                                              f"tk_{field}", id_)
                        st.markdown("**Campos manuales**")
                        c2 = st.columns(2)
                        with c2[0]:
                            _campo_numero("Compartidos", {"valor": None, "confianza": "manual"},
                                          "tk_compartidos", id_)
                        with c2[1]:
                            _campo_numero("Vistas", {"valor": None, "confianza": "manual"},
                                          "tk_vistas", id_)

                    # ── Comentarios (data_editor dinámico) ──
                    comments_key = f"rev_comments_{id_}"
                    raw = datos.get("comentarios", [])
                    if item["plataforma"] == "facebook":
                        df_init = pd.DataFrame([
                            {"texto": c.get("texto", ""), "autor": c.get("autor") or ""}
                            for c in raw
                        ])
                    else:
                        df_init = pd.DataFrame([
                            {"texto": c.get("texto", "")} for c in raw
                        ])

                    st.markdown("**Comentarios transcritos**")
                    n_comments = len(df_init)
                    suf = "suficiente" if n_comments >= 15 else "insuficiente"
                    st.caption(
                        f"Edita, borra o agrega filas. Comentarios sin texto se descartan."
                    )
                    col_config = {
                        "texto": st.column_config.TextColumn("Texto", required=True, width="large"),
                    }
                    if item["plataforma"] == "facebook":
                        col_config["autor"] = st.column_config.TextColumn("Autor", width="medium")
                    edited_df = st.data_editor(
                        df_init,
                        column_config=col_config,
                        num_rows="dynamic",
                        key=comments_key,
                        width='stretch',
                    )

                    st.markdown("---")
                    confirmado = st.form_submit_button("✅ Confirmar este post", disabled=is_revisado)

                    if confirmado:
                        _confirmar_post(item, texto_key, fecha_key, edited_df)

    # ── Paso 3: Items en error ──
    errores = [p for p in lote if p["estado"] == "error"]
    if errores:
        st.markdown("### ❌ Errores de extracción")
        st.caption("Estos archivos no pudieron procesarse. Revisa el motivo y reintenta.")
        for item in errores:
            st.error(f"**{item.get('fuente', '?')}** — {item.get('error_msg', 'Error desconocido')}")
            if st.button("🔁 Reintentar extracción", key=f"retry_{item['id_temporal']}"):
                item["estado"] = "pendiente"
                item.pop("error_msg", None)
                st.rerun()


def _confirmar_post(item: dict, texto_key: str, fecha_key: str, df_comentarios: pd.DataFrame) -> None:
    """Lee widgets, valida, y escribe datos_revisados + estado revisado."""
    import streamlit as st

    id_ = item["id_temporal"]
    plataforma = item["plataforma"]

    mensaje = st.session_state.get(texto_key, "")
    fecha = st.session_state.get(fecha_key)

    if not fecha:
        st.error("❌ La fecha es obligatoria. Sin fecha, el post queda excluido del análisis.")
        return

    created = str(fecha)

    comentarios = []
    for _, row in df_comentarios.iterrows():
        t = str(row.get("texto", "") or "").strip()
        if t:
            entry = {"texto": t}
            if plataforma == "facebook":
                entry["autor"] = str(row.get("autor", "") or "").strip() or None
            comentarios.append(entry)

    muestra_suf = len(comentarios) >= 15
    if not muestra_suf:
        st.warning(f"⚠️ Muestra insuficiente ({len(comentarios)} < 15). "
                   "El análisis de sentimiento será limitado.")

    # Leer enlace del campo editable
    enlace_final = st.session_state.get(f"rev_enlace_{id_}", item.get("enlace", ""))
    if enlace_final:
        lote = st.session_state["lote_ingreso"]
        for otro in lote:
            if otro["id_temporal"] != id_ and otro.get("enlace", "").strip() == enlace_final.strip():
                st.warning(f"⚠️ Este enlace ya existe en el lote (post {otro.get('id_temporal', '?')[:8]}…).")
                break

    # Leer widgets numéricos
    def _r(suffix):
        return st.session_state.get(f"rev_{suffix}_{id_}", 0) or 0

    if plataforma == "facebook":
        revisados = {
            "plataforma": "facebook",
            "page_name": item["fuente"],
            "message": mensaje,
            "created_time": created,
            "likes_count": _r("fb_likes"),
            "loves_count": _r("fb_loves"),
            "hahas_count": _r("fb_hahas"),
            "sads_count": _r("fb_sads"),
            "wows_count": _r("fb_wows"),
            "angrys_count": _r("fb_angrys"),
            "comments_count": _r("fb_comentarios_count"),
            "shares_count": _r("fb_compartidos"),
            "views_count": _r("fb_vistas"),
            "post_url": enlace_final or None,
            "comentarios": comentarios,
            "muestra_suficiente": muestra_suf,
        }
    else:  # TikTok
        try:
            account_id = int(item["fuente"])
        except (ValueError, TypeError):
            account_id = 0
        revisados = {
            "plataforma": "tiktok",
            "account_id": account_id,
            "description": mensaje,
            "created_at": created,
            "post_url": enlace_final or None,
            "views": _r("tk_vistas"),
            "likes": _r("tk_likes"),
            "favorites_count": _r("tk_favoritos"),
            "shares": _r("tk_compartidos"),
            "comments_count": _r("tk_comentarios_count"),
            "comentarios": comentarios,
            "muestra_suficiente": muestra_suf,
        }

    item["datos_revisados"] = revisados
    item["estado"] = "revisado"
    st.success("✅ Post confirmado.")
    st.rerun()


def seccion_cargar_contenido():
    """Sección para que el operador cargue capturas y arme lotes de posts en memoria."""
    # TODO Fase 9: proteger esta sección con login

    st.markdown("""
    <div class="seccion-header">
        <div class="seccion-titulo">📥 Cargar contenido</div>
        <div class="seccion-subtitulo">
            Sube capturas de pantalla de redes sociales y arma lotes para procesar
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Formulario: agregar post al lote ──
    with st.form("form_agregar_post"):
        col_plat, col_fuente = st.columns(2)

        with col_plat:
            plataforma_post = st.radio(
                "Plataforma",
                ["Facebook", "TikTok"],
                horizontal=True,
            )

        with col_fuente:
            if plataforma_post == "Facebook":
                fuente = st.selectbox("Fuente (página oficial)", FB_PAGES_OFICIALES)
            else:
                tk_nombres = list(TK_ACCOUNTS.values())
                tk_label = st.selectbox("Fuente (cuenta oficial)", tk_nombres)
                tk_id_map = {v: k for k, v in TK_ACCOUNTS.items()}
                fuente = str(tk_id_map[tk_label])

        imagenes = st.file_uploader(
            "Sube capturas (PNG/JPG) o un PDF con uno o varios posts",
            type=["png", "jpg", "jpeg", "pdf"],
            accept_multiple_files=True,
            key=f"uploader_{st.session_state.get('uploader_nonce', 0)}",
            help="Un PDF puede contener varios posts distintos; el sistema los separa automáticamente.",
        )

        enlace = st.text_input(
            "Enlace del post (opcional)",
            help="Solo de respaldo. Si el PDF ya incluye el enlace, se extrae automáticamente y este campo puede quedar vacío.",
        )

        submitted = st.form_submit_button("➕ Agregar post al lote", width='stretch')

        if submitted:
            errores = []
            if not imagenes:
                errores.append("Debes subir al menos una captura de pantalla.")
            if not fuente:
                errores.append("Debes seleccionar una fuente (página/cuenta oficial).")

            if errores:
                for e in errores:
                    st.error(e)
            else:
                post = {
                    "id_temporal": str(uuid.uuid4()),
                    "plataforma": plataforma_post.lower(),
                    "fuente": fuente,
                    "imagenes": list(imagenes),
                    "enlace": enlace.strip(),
                    "estado": "pendiente",
                }
                st.session_state["lote_ingreso"].append(post)
                st.success(f"✅ Post agregado al lote ({len(imagenes)} imágenes)")

    # ── Estado visual del lote ──
    st.markdown("---")
    lote = st.session_state["lote_ingreso"]

    if not lote:
        st.info("Aún no has agregado posts. Sube las capturas de un post y pulsa Agregar.")
    else:
        pendientes = sum(1 for p in lote if p["estado"] == "pendiente")
        st.metric("Lote actual", f"{len(lote)} posts", f"{pendientes} pendientes de procesar")

        for post in lote:
            cols = st.columns([1, 2, 1, 1, 1, 0.5])
            emoji = "📘" if post["plataforma"] == "facebook" else "🎵"
            cols[0].markdown(f"**{emoji} {post['plataforma'].title()}**")
            cols[1].markdown(f"*Fuente:* {post['fuente']}")
            cols[2].markdown(f"*Imágenes:* {len(post['imagenes'])}")
            cols[3].markdown("*Enlace:* sí" if post["enlace"] else "*Enlace:* —")
            cols[4].markdown(f"*Estado:* {post['estado']}")
            if cols[5].button("🗑️", key=f"quitar_{post['id_temporal']}"):
                st.session_state["lote_ingreso"] = [
                    p for p in st.session_state["lote_ingreso"]
                    if p["id_temporal"] != post["id_temporal"]
                ]
                st.rerun()
            st.markdown("---")

    # ── Revisión Fase 3 ──
    seccion_revisar_lote()

    # ── Guardado a SQLite (Fase 4) ──
    lote = st.session_state["lote_ingreso"]
    revisados = [p for p in lote if p["estado"] == "revisado"]
    guardados = [p for p in lote if p["estado"] == "guardado"]
    if revisados:
        st.markdown("### 💾 Paso 4 — Guardar en base de datos")
        st.caption(f"{len(revisados)} post(s) confirmados listos para guardar.")
        if st.button("💾 Guardar lote en base de datos", type="primary"):
            resumen = guardar_lote(lote, st.session_state.get("modo_prueba", False))
            partes = []
            if resumen["fb_posts"]:
                partes.append(f"{resumen['fb_posts']} posts FB")
            if resumen["fb_comments"]:
                partes.append(f"{resumen['fb_comments']} comentarios FB")
            if resumen["tk_videos"]:
                partes.append(f"{resumen['tk_videos']} videos TikTok")
            if resumen["tk_comments"]:
                partes.append(f"{resumen['tk_comments']} comentarios TikTok")
            msg = "✅ Guardado: " + ", ".join(partes) if partes else "⚠️ No se guardó nada."
            if resumen["errores"]:
                msg += "  \n".join(f"❌ {e}" for e in resumen["errores"][:5])
                if len(resumen["errores"]) > 5:
                    msg += f"\n... y {len(resumen['errores'])-5} error(es) más."
            st.success(msg)
            st.rerun()
    if guardados:
        st.info(f"✅ {len(guardados)} post(s) ya guardados en la base de datos.")

    # ── Procesamiento del pipeline (Fase 5) ──
    st.markdown("### ⚙️ Procesar lote (reconstruir análisis)")
    st.caption("Reconstruye las tablas agregadas (sentimiento, categorías, engagement, series) a partir de los datos guardados.")
    if st.button("⚙️ Procesar lote (reconstruir análisis)", type="primary"):
        status = st.status("Iniciando pipeline…", expanded=True)
        def _progreso(paso, total, etiqueta):
            status.update(label=f"Paso {paso}/{total}: {etiqueta}")
        result = procesar_pipeline(st.session_state.get("modo_prueba", False), _progreso)
        st.session_state["ultimo_procesamiento"] = result
        st.cache_data.clear()
        status.update(label="Pipeline completado", state="complete", expanded=False)
    result = st.session_state.get("ultimo_procesamiento")
    if result:
        motor = result["motor_sentimiento"]
        if result["errores"]:
            st.warning("⚠️ Pipeline con errores:")
            for err in result["errores"]:
                st.error(f"❌ {err}")
        if motor == "bert":
            st.success("🧠 Sentimiento analizado con BERT local (modelo principal).")
        elif motor == "gemini":
            st.warning("⚠️ BERT no se pudo cargar; se usó Gemini (sentimiento_engine) como respaldo.")
        else:
            st.warning("⚠️ Ni BERT ni Gemini disponibles; se usó el clasificador de reglas (último recurso). Resultados menos precisos.")
        if result["pasos_ok"]:
            st.info(f"✅ Pasos completados: {', '.join(result['pasos_ok'])}")


def _build_serie_chart(df_fb_s, df_tk_s, periodo):
    if df_fb_s.empty and df_tk_s.empty:
        return None
    if plataforma == "Facebook":
        df = df_fb_s[['semana','engagement','es_anomalia']].copy()
    elif plataforma == "TikTok":
        df = df_tk_s[['semana','views_suma','es_anomalia']].copy()
        df = df.rename(columns={'views_suma':'engagement'})
    else:
        merged = pd.merge(
            df_fb_s[['semana','engagement']].rename(columns={'engagement':'fb'}),
            df_tk_s[['semana','views_suma','es_anomalia']].rename(columns={'views_suma':'tk'}),
            on='semana', how='outer'
        ).fillna(0)
        merged['engagement'] = merged['fb'] + merged['tk']
        df = merged[['semana','engagement','es_anomalia']].copy()
    fecha_inicio = get_fecha_inicio(periodo)
    df = df[df['semana'] >= fecha_inicio].copy()
    if df.empty:
        return None
    df['media_movil'] = df['engagement'].rolling(4, min_periods=1).mean()
    df['ratio'] = np.where(df['media_movil'] > 0, df['engagement'] / df['media_movil'], 1.0)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['semana'], y=df['engagement'], mode='lines',
        line=dict(color='#3b82f6', width=2.5), name='Actividad ciudadana',
        customdata=df[['ratio']].values,
        hovertemplate="<b>%{x|%d %b %Y}</b><br>%{y:,.0f} interacciones<extra></extra>"))
    anom = df[df['es_anomalia'] == True]
    if not anom.empty:
        fig.add_trace(go.Scatter(x=anom['semana'], y=anom['engagement'], mode='markers',
            marker=dict(color='#ef4444', size=12), name='Semana inusual',
            hovertemplate="<b>Semana inusual</b><br>%{x|%d %b %Y}<extra></extra>"))
    fig.update_layout(plot_bgcolor='var(--bg-card)', paper_bgcolor='var(--bg-card)',
        font=dict(color='var(--fg-secondary)', size=10, family='IBM Plex Mono, monospace'),
        xaxis=dict(gridcolor='var(--border)', tickformat='%d %b\n%Y', tickfont=dict(size=9)),
        yaxis=dict(gridcolor='var(--border)', tickformat=','),
        margin=dict(l=0,r=0,t=10,b=0), height=250, showlegend=False)
    return fig


# ═══════════════════════════════════════════
# BLOQUE I — PULSO GENERAL
# ═══════════════════════════════════════════

def render_bloque1_pulso():
    df_fb_raw = cargar_fb_engagement(FACEBOOK_DB_ACTIVA)
    df_tk_raw = cargar_tk_engagement(TIKTOK_DB_ACTIVA, FACEBOOK_DB_ACTIVA)
    df_fb, df_tk = filtrar_por_periodo_plataforma(df_fb_raw, df_tk_raw, periodo, plataforma)

    st.markdown("""
    <div class="seccion-header">
        <div class="seccion-titulo">📊 PULSO GENERAL</div>
        <div class="seccion-subtitulo">Panorama completo — 3 indicadores clave</div>
    </div>""", unsafe_allow_html=True)

    if df_fb.empty and df_tk.empty:
        hay_datos(df_fb, "No hay datos para este período.")
        return

    # ── 1. CLIMA NARRATIVO ──
    st.markdown("### 1. Clima Narrativo")
    color_sem, texto_sem = calcular_semaforo(df_fb)
    st.markdown(f'<div class="semaforo-{color_sem}"><p class="semaforo-texto">{texto_sem}</p></div>', unsafe_allow_html=True)

    df_sent = cargar_sentimiento_fb(FACEBOOK_DB_ACTIVA)
    score_val = df_sent['score_sentimiento'].mean() if not df_sent.empty else 0
    pct_neg_val = df_sent['pct_negativo'].mean() if not df_sent.empty else 0
    pct_pos_val = df_sent['pct_positivo'].mean() if not df_sent.empty else 0
    enojo_val = df_fb['indice_enojo'].mean() if not df_fb.empty and 'indice_enojo' in df_fb.columns else 0

    interp = generar_interpretacion("semaforo", {
        'score': score_val, 'pct_negativo': pct_neg_val,
        'pct_positivo': pct_pos_val, 'indice_enojo': enojo_val
    })
    st.markdown(f'<div class="interpretacion-box"><div class="interpretacion-label">◈ LO QUE ESTO SIGNIFICA</div><div class="interpretacion-texto">{interp}</div></div>', unsafe_allow_html=True)

    total_comentarios = df_sent['total_comentarios'].sum() if not df_sent.empty else 0
    m = evaluar_muestra(total_comentarios)
    st.markdown(f'<p style="font-size:12px;color:var(--fg-muted)">{m["emoji"]} {m["etiqueta"]} en total</p>', unsafe_allow_html=True)

    # ── 2. INTENSIDAD ──
    st.markdown("### 2. Intensidad de la Conversación")
    total_eng = (int(df_fb['engagement_total'].sum()) if not df_fb.empty else 0) + (int(df_tk['engagement_total'].sum()) if not df_tk.empty else 0)
    total_posts = len(df_fb) + len(df_tk)
    total_reacciones = (int(df_fb['total_reacciones'].sum()) if not df_fb.empty else 0) + (int(df_tk['likes'].sum()) if not df_tk.empty else 0)

    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="bloom-card"><div class="bloom-card-title">Interacciones totales</div><div class="bloom-card-value">{total_eng:,}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="bloom-card"><div class="bloom-card-title">Contenido publicado</div><div class="bloom-card-value">{total_posts}</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="bloom-card"><div class="bloom-card-title">Reacciones totales</div><div class="bloom-card-value">{total_reacciones:,}</div></div>', unsafe_allow_html=True)

    df_fb_s, df_tk_s = cargar_series(FACEBOOK_DB_ACTIVA, TIKTOK_DB_ACTIVA)
    fig = _build_serie_chart(df_fb_s, df_tk_s, periodo)
    if fig:
        card_explicativa("Qué tanto la gente reacciona, comenta y comparte.", "Más alto: más gente se involucra. Más bajo: la gente lo ve pero no responde.")
        st.plotly_chart(fig, width='stretch')

    # ── 3. CONCENTRACIÓN TEMÁTICA ──
    st.markdown("### 3. Concentración Temática")
    df_cat = safe_query("SELECT item_id, categoria_nombre FROM post_categorias", FACEBOOK_DB_ACTIVA)
    if not df_cat.empty:
        conteo = df_cat['categoria_nombre'].value_counts()
        total_cat = conteo.sum()
        top_tema = conteo.index[0]
        share_top = conteo.iloc[0] / total_cat * 100
        hhi = sum((c/total_cat*100)**2 for c in conteo) / 10000
        st.markdown(f'<p style="font-size:13px;color:var(--fg-secondary)">Tema principal: <strong>{top_tema}</strong> — {share_top:.0f}% del contenido · HHI: {hhi:.2f}</p>', unsafe_allow_html=True)
        st.markdown(f'<div style="background:var(--bg-card);padding:10px;border-radius:4px"><div style="background:var(--accent-dim);width:{share_top:.0f}%;height:12px;border-radius:2px"></div></div>', unsafe_allow_html=True)
        otros = conteo.iloc[1:].index.tolist()[:5]
        if otros:
            st.markdown(f'<p style="font-size:11px;color:var(--fg-muted);margin-top:6px">Otros temas: {", ".join(str(t) for t in otros)}</p>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="bloom-status-info">Clasificación de temas requiere sentence-transformers (no instalado).</div>', unsafe_allow_html=True)

    # Metodológica Fase 6
    st.info("El análisis de sentimiento se basa en los comentarios capturados, no en el 100% de la conversación. Los % son un proxy, no medición exhaustiva.")


# ═══════════════════════════════════════════
# BLOQUE II — SEGMENTACIÓN DE AUDIENCIA
# ═══════════════════════════════════════════

def render_bloque2_audiencia():
    st.markdown("""
    <div class="seccion-header">
        <div class="seccion-titulo">👥 SEGMENTACIÓN DE AUDIENCIA</div>
        <div class="seccion-subtitulo">¿Quién reacciona, quién critica y quién impulsa la conversación?</div>
    </div>""", unsafe_allow_html=True)

    df_comentarios = cargar_comentarios_fb(FACEBOOK_DB_ACTIVA)
    if not hay_datos(df_comentarios, "Aún no hay comentarios procesados."):
        return

    # ── 1. MAPA DE PÚBLICOS ──
    st.markdown("### 1. Mapa de Públicos")
    df_tmp = df_comentarios.dropna(subset=['score_sentimiento'])
    if not df_tmp.empty:
        n_pos = (df_tmp['score_sentimiento'] > 0.1).sum()
        n_neg = (df_tmp['score_sentimiento'] < -0.1).sum()
        n_neu = len(df_tmp) - n_pos - n_neg
        total = n_pos + n_neg + n_neu
        p_pos = n_pos / total * 100 if total else 0
        p_neg = n_neg / total * 100 if total else 0
        p_neu = n_neu / total * 100 if total else 0

        fig_pub = go.Figure()
        fig_pub.add_trace(go.Bar(name='Simpatizante', x=['Públicos'], y=[p_pos], marker_color='#16a34a', text=f'{p_pos:.0f}%', textposition='inside'))
        fig_pub.add_trace(go.Bar(name='Neutral', x=['Públicos'], y=[p_neu], marker_color='#374151', text=f'{p_neu:.0f}%', textposition='inside'))
        fig_pub.add_trace(go.Bar(name='Crítico', x=['Públicos'], y=[p_neg], marker_color='#dc2626', text=f'{p_neg:.0f}%', textposition='inside'))
        fig_pub.update_layout(barmode='stack', height=100, margin=dict(l=0,r=0,t=0,b=0), showlegend=True,
            plot_bgcolor='var(--bg-card)', paper_bgcolor='var(--bg-card)',
            font=dict(color='var(--fg-secondary)', size=10, family='IBM Plex Mono, monospace'),
            legend=dict(orientation='h', y=1.1))
        st.plotly_chart(fig_pub, width='stretch')
        st.markdown(f'<p style="font-size:12px;color:var(--fg-muted)">⚠️ Proxy: la base son comentarios, no personas individuales.</p>', unsafe_allow_html=True)

        m = evaluar_muestra(len(df_comentarios))
        st.markdown(f'<p style="font-size:12px;color:var(--fg-muted)">{m["emoji"]} {m["etiqueta"]}</p>', unsafe_allow_html=True)

    # ── 2. POLARIZACIÓN ──
    st.markdown("### 2. Polarización")
    if not df_tmp.empty:
        p_extremos = ((df_tmp['score_sentimiento'].abs() > 0.5).sum() / len(df_tmp) * 100)
        p_centro = 100 - p_extremos
        fig_pol = go.Figure()
        fig_pol.add_trace(go.Bar(name='Extremos', x=['Polarización'], y=[p_extremos], marker_color='#ef4444', text=f'{p_extremos:.0f}%', textposition='inside'))
        fig_pol.add_trace(go.Bar(name='Centro', x=['Polarización'], y=[p_centro], marker_color='#6b7280', text=f'{p_centro:.0f}%', textposition='inside'))
        fig_pol.update_layout(barmode='stack', height=100, margin=dict(l=0,r=0,t=0,b=0), showlegend=True,
            plot_bgcolor='var(--bg-card)', paper_bgcolor='var(--bg-card)',
            font=dict(color='var(--fg-secondary)', size=10, family='IBM Plex Mono, monospace'),
            legend=dict(orientation='h', y=1.1))
        st.plotly_chart(fig_pol, width='stretch')
        st.markdown(f'<p style="font-size:11px;color:var(--fg-muted)">Extremos = comentarios con |score| > 0.5 (muy positivos o muy negativos). Alto % indica audiencia polarizada.</p>', unsafe_allow_html=True)

    # ── 3. VOCES DE INFLUENCIA ──
    st.markdown("### 3. Voces de Influencia (proxy)")
    df_fb_raw = cargar_fb_engagement(FACEBOOK_DB_ACTIVA)
    if not df_fb_raw.empty:
        top_pages = df_fb_raw.groupby('page_name').agg(
            engagement=('engagement_total', 'sum'),
            posts=('post_id', 'count')
        ).reset_index().sort_values('engagement', ascending=False).head(5)
        for _, r in top_pages.iterrows():
            st.markdown(f'<div class="bloom-card" style="padding:8px 14px"><span style="font-size:13px;color:var(--fg-primary)"><strong>{r["page_name"]}</strong></span><span style="float:right;color:var(--fg-secondary)">{int(r["engagement"]):,} interacciones · {int(r["posts"])} posts</span></div>', unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:11px;color:var(--fg-muted)">⚠️ Son páginas/cuentas oficiales, no ciudadanos individuales.</p>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="bloom-status-info">Sin datos de engagement para identificar voces.</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════
# BLOQUE III — RIESGO Y AUTENTICIDAD
# ═══════════════════════════════════════════

def render_bloque3_riesgo():
    st.markdown("""
    <div class="seccion-header">
        <div class="seccion-titulo">⚠️ RIESGO Y AUTENTICIDAD</div>
        <div class="seccion-subtitulo">Señales de alerta temprana y calidad de la interacción</div>
    </div>""", unsafe_allow_html=True)

    df_fb_raw = cargar_fb_engagement(FACEBOOK_DB_ACTIVA)
    df_tk_raw = cargar_tk_engagement(TIKTOK_DB_ACTIVA, FACEBOOK_DB_ACTIVA)
    df_fb, df_tk = filtrar_por_periodo_plataforma(df_fb_raw, df_tk_raw, periodo, plataforma)
    df_sent = cargar_sentimiento_fb(FACEBOOK_DB_ACTIVA)
    df_fb_s, df_tk_s = cargar_series(FACEBOOK_DB_ACTIVA, TIKTOK_DB_ACTIVA)

    if df_fb.empty and df_tk.empty:
        hay_datos(df_fb, "No hay datos para este período.")
        return

    # ── 1. AUTENTICIDAD (heurística) ──
    st.markdown("### 1. Índice de Autenticidad (heurística)")
    if not df_fb.empty and 'created_time' in df_fb.columns:
        daily = df_fb.copy()
        daily['fecha'] = daily['created_time'].dt.date
        daily_vol = daily.groupby('fecha').size()
        cv = daily_vol.std() / daily_vol.mean() if daily_vol.mean() > 0 else 0
        if cv < 0.5:
            label_aut = "ESTABLE (perfil orgánico)"
            color_aut = "#22c55e"
        elif cv < 1.0:
            label_aut = "MODERADA (algunos picos)"
            color_aut = "#f59e0b"
        else:
            label_aut = "VOLÁTIL (posible coordinación)"
            color_aut = "#ef4444"
        st.markdown(f'<div class="bloom-card" style="border-left:4px solid {color_aut}"><div class="bloom-card-title">Coeficiente de variación: {cv:.2f}</div><div class="bloom-card-value" style="color:{color_aut};font-size:18px">{label_aut}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:11px;color:var(--fg-muted)">⚠️ Heurística: CV bajo = volumen diario estable (más orgánico). CV alto = picos súbitos (posible coordinación). No es detección de bots.</p>', unsafe_allow_html=True)

    # ── 2. NIVEL DE ALERTA ──
    st.markdown("### 2. Nivel de Alerta")
    color_sem, texto_sem = calcular_semaforo(df_fb)
    score_val = df_sent['score_sentimiento'].mean() if not df_sent.empty else 0
    pct_neg_val = df_sent['pct_negativo'].mean() if not df_sent.empty else 0
    pct_pos_val = df_sent['pct_positivo'].mean() if not df_sent.empty else 0
    enojo_val = df_fb['indice_enojo'].mean() if not df_fb.empty and 'indice_enojo' in df_fb.columns else 0
    interp = generar_interpretacion("semaforo", {
        'score': score_val, 'pct_negativo': pct_neg_val,
        'pct_positivo': pct_pos_val, 'indice_enojo': enojo_val
    })
    st.markdown(f'<div class="semaforo-{color_sem}"><p class="semaforo-texto">{texto_sem}</p></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="interpretacion-box"><div class="interpretacion-texto">{interp}</div></div>', unsafe_allow_html=True)

    # ── 3. VELOCIDAD DE PROPAGACIÓN ──
    st.markdown("### 3. Velocidad de Propagación")
    df_series = pd.concat([df_fb_s, df_tk_s], ignore_index=True) if not df_fb_s.empty or not df_tk_s.empty else pd.DataFrame()
    if not df_series.empty and 'engagement' in df_series.columns:
        df_series = df_series.sort_values('semana')
        recent = df_series.tail(2)
        if len(recent) == 2:
            prev = recent.iloc[0]['engagement']
            curr = recent.iloc[1]['engagement']
            if prev > 0:
                cambio = (curr - prev) / prev * 100
            else:
                cambio = 0
            if cambio > 15:
                flecha, color_v = "↑", "#ef4444"
                nota = f"La conversación creció {cambio:.0f}% vs la semana anterior."
            elif cambio < -15:
                flecha, color_v = "↓", "#3b82f6"
                nota = f"La conversación cayó {abs(cambio):.0f}% vs la semana anterior."
            else:
                flecha, color_v = "→", "#6b7280"
                nota = "Volumen estable respecto a la semana anterior."
            st.markdown(f'<div class="bloom-card"><span style="font-size:28px;color:{color_v};font-weight:700">{flecha}</span><span style="font-size:14px;color:var(--fg-secondary);margin-left:12px">{nota}</span></div>', unsafe_allow_html=True)

    # ── 4. PUNTOS DE FRICCIÓN ──
    st.markdown("### 4. Puntos de Fricción")
    df_neg = cargar_comentarios_negativos()
    if not df_neg.empty:
        top_neg = df_neg.nsmallest(3, 'sentiment_score') if 'sentiment_score' in df_neg.columns else df_neg.head(3)
        for _, r in top_neg.iterrows():
            msg = str(r.get('message', ''))[:120]
            st.markdown(f'<div class="patron-rechazo"><p style="font-size:13px;color:#d1d5db">"{msg}"</p></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="bloom-status-info">Sin comentarios negativos destacados.</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════
# BLOQUE IV — MEMORIA E INTELIGENCIA APLICADA
# ═══════════════════════════════════════════

def render_bloque4_inteligencia():
    st.markdown("""
    <div class="seccion-header">
        <div class="seccion-titulo">🧠 MEMORIA E INTELIGENCIA APLICADA</div>
        <div class="seccion-subtitulo">Análisis profundo con datos e IA</div>
    </div>""", unsafe_allow_html=True)

    df_sent = cargar_sentimiento_fb(FACEBOOK_DB_ACTIVA)
    df_fb_raw = cargar_fb_engagement(FACEBOOK_DB_ACTIVA)
    df_tk_raw = cargar_tk_engagement(TIKTOK_DB_ACTIVA, FACEBOOK_DB_ACTIVA)
    df_fb, df_tk = filtrar_por_periodo_plataforma(df_fb_raw, df_tk_raw, periodo, plataforma)

    score = df_sent['score_sentimiento'].mean() if not df_sent.empty else 0
    pct_neg = df_sent['pct_negativo'].mean() if not df_sent.empty else 0
    pct_pos = df_sent['pct_positivo'].mean() if not df_sent.empty else 0
    enojo = df_fb['indice_enojo'].mean() if not df_fb.empty and 'indice_enojo' in df_fb.columns else 0
    total_eng = (int(df_fb['engagement_total'].sum()) if not df_fb.empty else 0) + (int(df_tk['engagement_total'].sum()) if not df_tk.empty else 0)

    ctx = {"score": round(score, 3), "pct_negativo": round(pct_neg, 1), "pct_positivo": round(pct_pos, 1),
           "indice_enojo": round(enojo, 3), "interacciones": total_eng, "periodo": periodo}

    # ── Tarjetas IA ──
    for label, tipo in [
        ("Eco Histórico", "eco_historico"),
        ("Lección Aprendida", "leccion"),
        ("Contexto No Visible", "contexto"),
        ("Proyección de Escenario", "proyeccion"),
        ("Recomendación Estratégica", "recomendacion"),
    ]:
        with st.spinner(f"Generando {label}…"):
            narrativa = generar_narrativa_ia(tipo, ctx)
        st.markdown(f'<div class="bloom-card"><div class="bloom-card-title">{label.upper()}</div><p style="font-size:13px;color:var(--fg-primary);line-height:1.6">{narrativa}</p></div>', unsafe_allow_html=True)

    # ── Temas Emergentes / Extinción ──
    st.markdown("### Temas Emergentes y en Extinción")
    df_cat = safe_query("SELECT item_id, categoria_nombre, created_time FROM fb_posts LEFT JOIN post_categorias ON fb_posts.post_id = post_categorias.item_id", FACEBOOK_DB_ACTIVA)
    if not df_cat.empty and 'created_time' in df_cat.columns and 'categoria_nombre' in df_cat.columns:
        df_cat['created_time'] = pd.to_datetime(df_cat['created_time'], errors='coerce')
        df_cat['semana'] = df_cat['created_time'].dt.to_period('W').dt.start_time
        df_cat = df_cat.dropna(subset=['categoria_nombre', 'semana'])
        if not df_cat.empty:
            ultima_sem = df_cat['semana'].max()
            sem_actual = df_cat[df_cat['semana'] == ultima_sem]
            sem_prev = df_cat[df_cat['semana'] == ultima_sem - pd.Timedelta(days=7)]
            freq_actual = sem_actual['categoria_nombre'].value_counts()
            freq_prev = sem_prev['categoria_nombre'].value_counts()
            emergentes = [c for c in freq_actual.index if c not in freq_prev.index]
            extintos = [c for c in freq_prev.index if c not in freq_actual.index]

            col_e, col_x = st.columns(2)
            with col_e:
                st.markdown("**🆕 Emergentes**")
                if emergentes:
                    for t in emergentes[:5]:
                        st.markdown(f'<p style="font-size:13px;color:#22c55e">+ {t}</p>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<p style="font-size:12px;color:var(--fg-muted)">Sin temas nuevos esta semana.</p>', unsafe_allow_html=True)
            with col_x:
                st.markdown("**📉 En extinción**")
                if extintos:
                    for t in extintos[:5]:
                        st.markdown(f'<p style="font-size:13px;color:#ef4444">- {t}</p>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<p style="font-size:12px;color:var(--fg-muted)">Sin temas en extinción esta semana.</p>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="bloom-status-info">Clasificación de temas requiere sentence-transformers.</div>', unsafe_allow_html=True)

    # ── Correlación Contenido-Reacción ──
    st.markdown("### Correlación Contenido-Reacción")
    df_posts, conteo_tipos, distorsion_alta, por_semana = calcular_contagio_emocional()
    if not df_posts.empty:
        resonancia_pos = conteo_tipos.get('resonancia_positiva', 0)
        rechazo = conteo_tipos.get('rechazo_a_positivo', 0)
        total_p = len(df_posts)
        st.markdown(f'<div class="bloom-card"><p style="font-size:13px">Resonancia positiva: <strong style="color:#22c55e">{resonancia_pos}/{total_p}</strong> · Rechazo a positivo: <strong style="color:#ef4444">{rechazo}/{total_p}</strong></p></div>', unsafe_allow_html=True)

        if not distorsion_alta.empty:
            st.markdown("**Posts con mayor distorsión (brecha reacción vs comentarios):**")
            for _, r in distorsion_alta.head(3).iterrows():
                msg = str(r.get('message', ''))[:100]
                st.markdown(f'<div class="patron-rechazo"><p style="font-size:12px">"{msg}"</p></div>', unsafe_allow_html=True)

    # ── Comparativa Sectorial ──
    st.markdown("### Comparativa Sectorial")
    df_ext = cargar_externos(EXTERNOS_DB_ACTIVA)
    if not df_ext.empty:
        n_fuentes = df_ext['page_name'].nunique()
        n_menciones = len(df_ext)
        score_ext = df_ext['score_sentimiento'].mean() if 'score_sentimiento' in df_ext.columns else 0
        tono_ext = "POSITIVO" if score_ext > 0.1 else "MIXTO" if score_ext > -0.1 else "CRITICO"
        c_cs1, c_cs2, c_cs3 = st.columns(3)
        c_cs1.markdown(f'<div class="bloom-card"><div class="bloom-card-title">Fuentes</div><div class="bloom-card-value">{n_fuentes}</div></div>', unsafe_allow_html=True)
        c_cs2.markdown(f'<div class="bloom-card"><div class="bloom-card-title">Menciones</div><div class="bloom-card-value">{n_menciones}</div></div>', unsafe_allow_html=True)
        c_cs3.markdown(f'<div class="bloom-card"><div class="bloom-card-title">Tono externo</div><div class="bloom-card-value" style="color:{"#22c55e" if score_ext>0.1 else "#eab308" if score_ext>-0.1 else "#ef4444"}">{tono_ext}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="bloom-status-info">Sin datos externos para comparativa sectorial.</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════
# SECCIÓN 2 — TEMAS Y EMOCIONES
# ═══════════════════════════════════════════

# ═══════════════════════════════════════════
# DISPATCH PRINCIPAL
# ═══════════════════════════════════════════

if vista == "📊 Dashboard":
    tab_pulso, tab_audiencia, tab_riesgo, tab_inteligencia = st.tabs([
        "📊 Pulso General", "👥 Segmentación de Audiencia",
        "⚠️ Riesgo y Autenticidad", "🧠 Memoria e Inteligencia Aplicada"
    ])
    with tab_pulso:
        render_bloque1_pulso()
    with tab_audiencia:
        render_bloque2_audiencia()
    with tab_riesgo:
        render_bloque3_riesgo()
    with tab_inteligencia:
        render_bloque4_inteligencia()
elif vista == "📥 Cargar contenido":
    seccion_cargar_contenido()
elif vista == "📋 Notas metodológicas":
    render_notas_metodologicas()
