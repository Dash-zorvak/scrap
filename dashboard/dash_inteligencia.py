"""Capa de inteligencia: conecta Cambridge Index, IQ Engine y resúmenes por zona."""

import sys
import os
import sqlite3
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from config import FACEBOOK_DB
from dashboard.tema_taxonomia import (
    TEMA_LABELS as _TAX_LABELS,
    REMAP_LEGACY as _REMAP_LEGACY,
    etiqueta_tema,
)
from dashboard.tema_clasificaciones_ia import guardar_clasificacion_ia

_SEVERIDAD_COLOR = {1: "🟢", 2: "🟡", 3: "🔴", 4: "🔴"}
_SEVERIDAD_LABEL = {1: "bajo", 2: "medio", 3: "alto", 4: "crítico"}

# Etiquetas legibles de los temas englobantes (fuente: tema_taxonomia). Se
# conservan tambien las claves historicas por compatibilidad con datos viejos.
TEMA_LABELS = dict(_TAX_LABELS)
for _old, _new in _REMAP_LEGACY.items():
    TEMA_LABELS.setdefault(_old, _TAX_LABELS.get(_new, _old))

# Umbral de confianza por debajo del cual una clasificación se considera dudosa.
UMBRAL_CONFIANZA_DUDOSA = float(os.environ.get("TEMAS_UMBRAL_DUDOSO", "0.55"))
# Máximo de comentarios ambiguos que se exponen para revisión manual.
MAX_AMBIGUOS_REVISION = int(os.environ.get("TEMAS_MAX_AMBIGUOS", "15"))


def _construir_posts(db_path=None) -> list[dict]:
    if db_path is None:
        db_path = FACEBOOK_DB
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT p.post_id, p.created_time, p.likes_count, p.loves_count,
                   p.cares_count, p.hahas_count, p.wows_count, p.sads_count,
                   p.angrys_count, p.shares_count, p.comments_count, p.views_count,
                   p.topic_category, p.zona,
                   s.pct_positivo, s.pct_negativo
            FROM fb_posts p
            LEFT JOIN fb_sentimiento s ON p.post_id = s.post_id
        """).fetchall()
        conn.close()
    except Exception:
        return []

    posts = []
    for r in rows:
        d = dict(r)
        pct_pos = d.get("pct_positivo", 0) or 0
        pct_neg = d.get("pct_negativo", 0) or 0

        if pct_neg > pct_pos:
            sentiment = "negative"
        elif pct_pos > pct_neg:
            sentiment = "positive"
        else:
            sentiment = None

        total_reactions = (
            d.get("likes_count", 0) + d.get("loves_count", 0)
            + d.get("cares_count", 0) + d.get("hahas_count", 0)
            + d.get("wows_count", 0) + d.get("sads_count", 0)
            + d.get("angrys_count", 0)
        )

        topic = (d.get("topic_category") or "").strip()
        zona = (d.get("zona") or "").strip()

        posts.append({
            "likes_count": d.get("likes_count", 0),
            "loves_count": d.get("loves_count", 0),
            "cares_count": d.get("cares_count", 0),
            "hahas_count": d.get("hahas_count", 0),
            "wows_count": d.get("wows_count", 0),
            "sads_count": d.get("sads_count", 0),
            "angrys_count": d.get("angrys_count", 0),
            "shares_count": d.get("shares_count", 0),
            "comments_count": d.get("comments_count", 0),
            "views_count": d.get("views_count", 0),
            "created_time": d.get("created_time"),
            "topic_category": topic,
            "topic": topic,
            "zona": zona,
            "zone": zona,
            "zone_ner": None,
            "sentiment": sentiment,
            "total_reactions": total_reactions,
        })
    return posts


def cargar_alertas_cambridge(db_path=None) -> list[dict]:
    from src.intelligence.cambridge_index import run_all_detectors, SuppressionEngine

    posts = _construir_posts(db_path)
    if len(posts) < 5:
        return []

    suppression = SuppressionEngine()
    result = run_all_detectors(posts, suppression)
    return result.get("alerts", [])


def traducir_alerta(alert: dict) -> dict:
    tipo = alert.get("type", "")
    severidad = alert.get("severity", 1)
    color = _SEVERIDAD_COLOR.get(severidad, "🟡")
    zona = alert.get("zona", "")

    titulares = {
        "ici": "Sube la controversia en redes",
        "sdi": "Lo que publican no coincide con lo que siente la gente",
        "efi": "La conversación está perdiendo fuerza",
        "tai": "Un tema genera mucho más enojo de lo normal",
        "zdi": f"{zona}: la gente está molesta",
    }
    titular = titulares.get(tipo, alert.get("title", "Alerta detectada"))

    score = alert.get("score", 0)
    n_posts = alert.get("n_posts", 0) or 0

    if tipo == "ici":
        lectura = f"Las reacciones de enojo y tristeza están muy por encima de lo normal en redes sociales."
    elif tipo == "sdi":
        lectura = f"El sentimiento de los comentarios es más negativo de lo que las reacciones del post sugieren."
    elif tipo == "efi":
        lectura = f"La gente está respondiendo menos a las publicaciones en comparación con semanas anteriores."
    elif tipo == "tai":
        topic = alert.get("topic", "")
        lectura = f"Las publicaciones sobre {topic} tienen una proporción de enojo muy por encima de lo normal."
    elif tipo == "zdi" and zona:
        lectura = f"Las publicaciones sobre {zona} tienen más reacciones negativas que positivas."
    else:
        lectura = alert.get("description", "Comportamiento fuera de lo normal detectado.")

    return {
        "titular": titular,
        "lectura": f"🔎 Léelo así: {lectura}",
        "color": color,
        "severidad": severidad,
        "tipo": tipo,
        "zona": zona,
    }


def cargar_iq(db_path=None) -> dict:
    from src.analyzer.iq_engine import (
        compute_all_dimensions, compute_iq_score, compute_matrix_position,
        DIMENSION_LABELS,
    )

    posts = _construir_posts(db_path)
    if not posts:
        return {"iq": None, "dimensiones": [], "cuadrante": None}

    dims = compute_all_dimensions(posts)
    iq = compute_iq_score(dims)
    matrix = compute_matrix_position(posts)

    ordenadas = sorted(dims.items(), key=lambda x: x[1], reverse=True)
    dimensiones = [
        {
            "clave": k,
            "label": DIMENSION_LABELS.get(k, {}).get("label", k),
            "valor": v,
        }
        for k, v in ordenadas
    ]

    return {
        "iq": iq,
        "dimensiones": dimensiones,
        "cuadrante": matrix.get("quadrant"),
    }


def cargar_zonas_resumen(db_path=None) -> dict:
    if db_path is None:
        db_path = FACEBOOK_DB
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.execute("PRAGMA table_info(fb_comments)")
        cols = [r[1] for r in cur.fetchall()]
        if "zona" not in cols or "sentiment" not in cols:
            conn.close()
            return {"apoyo": [], "enojo": [], "total_zonas": 0}
        rows = conn.execute("""
            SELECT zona, sentiment, message FROM fb_comments
            WHERE zona IS NOT NULL AND zona != ''
            AND message IS NOT NULL AND message != ''
        """).fetchall()
        conn.close()
    except Exception:
        return {"apoyo": [], "enojo": [], "total_zonas": 0}

    zonas_sent = defaultdict(lambda: {"n_com": 0, "negativos": 0, "mensajes_neg": []})
    for zona, sentiment, msg in rows:
        zonas_sent[zona]["n_com"] += 1
        if sentiment in ("negativo", "muy_negativo"):
            zonas_sent[zona]["negativos"] += 1
            if len(zonas_sent[zona]["mensajes_neg"]) < 3:
                zonas_sent[zona]["mensajes_neg"].append(msg)

    apoyo = []
    enojo = []
    for zona, datos in zonas_sent.items():
        pct_neg = round(datos["negativos"] / max(datos["n_com"], 1) * 100, 1)
        motivo = datos["mensajes_neg"][0][:120] if datos["mensajes_neg"] else None
        item = {
            "zona": zona,
            "n_comentarios": datos["n_com"],
            "pct_negativos": pct_neg,
            "motivo": motivo,
        }
        if pct_neg >= 50:
            enojo.append(item)
        else:
            apoyo.append(item)

    apoyo = sorted(apoyo, key=lambda x: x["n_comentarios"], reverse=True)[:7]
    enojo = sorted(enojo, key=lambda x: x["pct_negativos"], reverse=True)[:7]

    return {
        "apoyo": apoyo,
        "enojo": enojo,
        "total_zonas": len(zonas_sent),
    }


def cargar_cruce_tema_zona(db_path=None) -> list[dict]:
    """Ranking de combinaciones tema × zona × sentimiento."""
    if db_path is None:
        db_path = FACEBOOK_DB
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute("""
            SELECT fc.zona, pc.categoria_nombre AS tema, fc.sentiment,
                   COUNT(*) as n
            FROM fb_comments fc
            LEFT JOIN post_categorias pc ON fc.post_id = pc.item_id
            WHERE fc.zona IS NOT NULL AND fc.zona != ''
              AND fc.sentiment IS NOT NULL
            GROUP BY fc.zona, pc.categoria_nombre, fc.sentiment
            ORDER BY n DESC
            LIMIT 20
        """).fetchall()
        conn.close()
    except Exception:
        return []
    return [
        {"zona": r[0], "tema": r[1] or "Sin categoría", "sentiment": r[2], "n": r[3]}
        for r in rows if r[0] and r[2]
    ]


def cargar_perfil_ocean(db_path=None) -> dict:
    """Perfil de audiencia vía OCEAN engine (PCA + clusters)."""
    from src.analyzer.ocean_engine import run_ocean_analysis
    posts = _construir_posts(db_path)
    if len(posts) < 5:
        return {"has_sklearn": False, "clusters": {}, "pca": {}}
    result = run_ocean_analysis(posts, posts)
    perfiles = {}
    clusters = result.get("clusters", {}).get("profiles", {})
    for label, p in clusters.items():
        perfiles[label] = {
            "size": p.get("size", 0),
            "avg_reactions": p.get("avg_reactions", 0),
            "dominant_topic": p.get("dominant_topic", ""),
            "dominant_sentiment": p.get("dominant_sentiment", ""),
        }
    pca = result.get("pca", {})
    return {
        "has_sklearn": result.get("has_sklearn", False),
        "clusters": perfiles,
        "pca": {
            "total_explained": pca.get("total_explained", 0),
            "n_components": pca.get("n_components", 0),
        },
    }


def cargar_temas_latentes_detallado(db_path=None) -> dict:
    """Version detallada (legacy) de Temas Emergentes con banderas de confianza.

    Se conserva por compatibilidad; el dashboard ahora usa el modelo de
    aprobacion manual (cargar_temas_aprobados / sugerir_temas_pendientes).
    """
    from dashboard.topic_llm import clasificar_temas_lote
    if db_path is None:
        db_path = FACEBOOK_DB
    vacio = {"temas": [], "ambiguos": [], "resumen": {}}
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute("""
            SELECT message FROM fb_comments
            WHERE message IS NOT NULL AND message != ''
            LIMIT 2000
        """).fetchall()
        conn.close()
    except Exception:
        return vacio
    textos = [r[0] for r in rows]
    if len(textos) < 10:
        return vacio

    clasificacion = clasificar_temas_lote(textos)

    agreg = defaultdict(lambda: {
        "n": 0, "suma_conf": 0.0, "n_sarcasticos": 0, "n_dudosos": 0, "n_reglas": 0,
    })
    ejemplos = {}
    ejemplos_alt = {}
    ambiguos = []
    total_clasificados = 0
    n_no_aplica = 0
    n_sarcasticos_total = 0
    n_dudosos_total = 0
    n_reglas_total = 0

    for texto, info in zip(textos, clasificacion):
        info = info or {}
        cat = info.get("categoria", "") or ""
        tono = info.get("tono", "literal")
        try:
            conf = float(info.get("confianza", 0.5))
        except (TypeError, ValueError):
            conf = 0.5
        motor = info.get("motor", "llm")
        limpio = " ".join(str(texto).split())
        es_dudoso = conf < UMBRAL_CONFIANZA_DUDOSA
        es_sarcastico = tono == "sarcastico"
        if motor == "reglas":
            n_reglas_total += 1

        if not cat or cat == "no_aplica":
            n_no_aplica += 1
            continue

        a = agreg[cat]
        a["n"] += 1
        a["suma_conf"] += conf
        total_clasificados += 1
        if es_sarcastico:
            a["n_sarcasticos"] += 1
            n_sarcasticos_total += 1
        if es_dudoso:
            a["n_dudosos"] += 1
            n_dudosos_total += 1
        if motor == "reglas":
            a["n_reglas"] += 1

        alt_prev = ejemplos_alt.get(cat)
        if alt_prev is None or 15 <= len(limpio) < len(alt_prev):
            ejemplos_alt[cat] = limpio
        if not es_sarcastico and not es_dudoso:
            prev = ejemplos.get(cat)
            if prev is None or 15 <= len(limpio) < len(prev):
                ejemplos[cat] = limpio

        if (es_dudoso or es_sarcastico) and len(ambiguos) < MAX_AMBIGUOS_REVISION:
            if es_sarcastico and es_dudoso:
                motivo = "posible sarcasmo + clasificación dudosa"
            elif es_sarcastico:
                motivo = "posible sarcasmo"
            else:
                motivo = "clasificación dudosa"
            texto_corto = limpio if len(limpio) <= 160 else limpio[:157] + "..."
            ambiguos.append({
                "texto": texto_corto,
                "categoria_tentativa": cat,
                "label_tentativa": TEMA_LABELS.get(cat, cat.replace("_", " ").capitalize()),
                "tono": tono,
                "confianza": round(conf, 2),
                "motivo": motivo,
            })

    resumen = {
        "total": len(textos),
        "clasificados": total_clasificados,
        "no_aplica": n_no_aplica,
        "sarcasticos": n_sarcasticos_total,
        "dudosos": n_dudosos_total,
        "por_reglas": n_reglas_total,
        "umbral_dudoso": UMBRAL_CONFIANZA_DUDOSA,
    }

    if total_clasificados == 0:
        return {"temas": [], "ambiguos": ambiguos, "resumen": resumen}

    temas = []
    for i, (cat, a) in enumerate(agreg.items()):
        n = a["n"]
        ejemplo = ejemplos.get(cat) or ejemplos_alt.get(cat, "")
        if len(ejemplo) > 120:
            ejemplo = ejemplo[:117] + "..."
        conf_prom = a["suma_conf"] / n if n else 0.0
        frac_sarc = a["n_sarcasticos"] / n if n else 0.0
        frac_dud = a["n_dudosos"] / n if n else 0.0
        if conf_prom < UMBRAL_CONFIANZA_DUDOSA or frac_dud >= 0.5:
            bandera = "dudosa"
        elif frac_sarc >= 0.34:
            bandera = "sarcasmo"
        else:
            bandera = "ok"
        temas.append({
            "id": i + 1,
            "label": TEMA_LABELS.get(cat, cat.replace("_", " ").capitalize()),
            "categoria": cat,
            "pct": round(n / total_clasificados * 100, 1),
            "doc_count": n,
            "ejemplo": ejemplo,
            "words": [],
            "confianza_promedio": round(conf_prom, 2),
            "n_sarcasticos": a["n_sarcasticos"],
            "n_dudosos": a["n_dudosos"],
            "bandera": bandera,
        })

    temas = sorted(temas, key=lambda x: -x["doc_count"])
    return {"temas": temas, "ambiguos": ambiguos, "resumen": resumen}


def cargar_temas_aprobados(db_path=None) -> list[dict]:
    """Tarjetas de Temas Emergentes: SOLO comentarios aprobados manualmente.

    Cada tema trae su etiqueta, el numero de comentarios aprobados (doc_count) y
    su porcentaje sobre el total de comentarios con tema aprobado (pct). Sin
    banderas de confianza: el badge es '%·N comentarios'.
    """
    if db_path is None:
        db_path = FACEBOOK_DB
    from dashboard.tema_aprobaciones import agregar_por_tema
    return agregar_por_tema(db_path)


def cargar_temas_latentes(db_path=None) -> list[dict]:
    """Compat: temas mostrados en el dashboard.

    En el modelo de aprobacion manual, los temas mostrados son los aprobados.
    """
    return cargar_temas_aprobados(db_path)


def sugerir_temas_pendientes(db_path=None, limite=None) -> list[dict]:
    """Comentarios SIN aprobacion, con una sugerencia de tema de la IA.

    La IA solo sugiere (no cuenta en las tarjetas). El usuario aprueba/corrige.
    Las aprobaciones previas se inyectan como ejemplos (few-shot) para que la
    sugerencia se afine con el criterio del usuario.

    Equivale a sugerir_temas_pendientes_cacheado con un cache vacio: clasifica
    todos los pendientes en cada llamada (comportamiento historico).
    """
    return sugerir_temas_pendientes_cacheado(db_path, cache={}, limite=limite)


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
    except Exception:
        try:
            conn = sqlite3.connect(db_path)
            rows = conn.execute(
                "SELECT comment_id, message FROM fb_comments "
                "WHERE message IS NOT NULL AND message != ''"
            ).fetchall()
            conn.close()
        except Exception:
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
