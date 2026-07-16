"""Persistencia de aprobaciones manuales de temas.

Guarda, por comentario (comment_id de fb_comments), el tema que el usuario
APROBO manualmente y su POSTURA (apoyo/critica/neutral).

La postura es un eje SEPARADO del tema (ver dashboard/tema_taxonomia.py): permite
que la tarjeta de cada tema se divida en apoyo / critica / neutral y que una
critica NO se cuente como impulso positivo del tema.

Campos nuevos (Punto 5 / Punto 2 / Punto 3 / Punto 4):
  - subtema_especifico: entidad o subtema concreto (nullable)
  - intensidad_postura: leve/moderada/fuerte (nullable, default moderada)
  - emociones: JSON array de 1+ claves de emoción (reemplaza emoción única)
  - relevancia_al_post: directo_al_post/tangencial_via_respuesta/ruido_conversacional

Modulo puro de datos (sqlite + stdlib), sin Streamlit, para que sea verificable
en CI.
"""

import sqlite3
import json
import pandas as pd
from collections import defaultdict
from datetime import datetime, timezone

from dashboard.tema_taxonomia import (
    CATEGORIAS_VALIDAS,
    REMAP_LEGACY,
    EMOCIONES_VALIDAS,
    EMOCION_DEFAULT,
    POSTURA_DEFAULT,
    etiqueta_tema,
    normalizar_emocion,
    normalizar_postura,
    remapear,
)

TABLA = "tema_aprobaciones"

INTENSIDADES_POSTURA = {"leve", "moderada", "fuerte"}
INTENSIDAD_POSTURA_DEFAULT = "moderada"

RELEVANCIAS_POST = {"directo_al_post", "tangencial_via_respuesta", "ruido_conversacional"}
RELEVANCIA_DEFAULT = "directo_al_post"


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
    version anterior (agrega columnas postura, emocion, subtema_especifico,
    intensidad_postura, emociones, relevancia_al_post)."""
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
                fecha TEXT,
                emocion TEXT DEFAULT 'calma',
                subtema_especifico TEXT,
                intensidad_postura TEXT DEFAULT 'moderada',
                emociones TEXT,
                relevancia_al_post TEXT DEFAULT 'directo_al_post'
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
        if "subtema_especifico" not in cols:
            conn.execute(
                f"ALTER TABLE {TABLA} ADD COLUMN subtema_especifico TEXT"
            )
        if "intensidad_postura" not in cols:
            conn.execute(
                f"ALTER TABLE {TABLA} ADD COLUMN intensidad_postura TEXT DEFAULT 'moderada'"
            )
        if "emociones" not in cols:
            conn.execute(
                f"ALTER TABLE {TABLA} ADD COLUMN emociones TEXT"
            )
        if "relevancia_al_post" not in cols:
            conn.execute(
                f"ALTER TABLE {TABLA} ADD COLUMN relevancia_al_post TEXT DEFAULT 'directo_al_post'"
            )
        conn.commit()
    finally:
        conn.close()


def guardar_aprobacion(db_path, comment_id, tema, texto="",
                       tema_sugerido=None, tono=None, confianza=None,
                       postura="neutral", emocion=None, emociones=None,
                       subtema_especifico=None, intensidad_postura=None,
                       relevancia_al_post=None):
    """Guarda (o actualiza) la aprobacion de un comentario.

    Devuelve True si se guardo. En la aprobacion MANUAL validamos de forma
    estricta: solo se aceptan categorias englobantes validas o claves legacy
    conocidas (que luego se remapean a su englobante). Cualquier otro tema
    inexistente -o falta comment_id/tema- no guarda y devuelve False.

    `postura` (apoyo/critica/neutral) se normaliza; lanza ValueError si no es
    reconocida (H-DS1: sin normalizacion silenciosa).

    `intensidad_postura` (leve/moderada/fuerte): solo aplica a apoyo y critica.
    Para neutral se usa "moderada" por defecto. Lanza ValueError si no es
    reconocida.

    `emociones` (Punto 3): lista de 1+ claves de emoción. Se guarda como JSON.
    Si se provee `emocion` (legacy) en vez de `emociones`, se envuelve en lista.

    `emocion` (legacy) se normaliza con normalizar_emocion(); lanza ValueError
    si no es reconocida. Si no se provee `emocion` ni `emociones`, se auto-detecta
    desde el texto usando classify_emotion().

    `subtema_especifico` (Punto 1): entidad o subtema concreto (nullable).

    `relevancia_al_post` (Punto 4): directo_al_post/tangencial_via_respuesta/
    ruido_conversacional. Si no se provee, default "directo_al_post".

    Raises:
        ValueError: si postura, intensidad_postura o emociones no son reconocidas.
    """
    if not comment_id or not tema:
        return False
    if tema not in CATEGORIAS_VALIDAS and tema not in REMAP_LEGACY:
        return False
    tema = remapear(tema)
    postura = normalizar_postura(postura)

    # Normalizar intensidad_postura
    if intensidad_postura is None:
        intensidad_postura = INTENSIDAD_POSTURA_DEFAULT
    else:
        ip = str(intensidad_postura).strip().lower()
        if ip not in INTENSIDADES_POSTURA:
            raise ValueError(
                f"Intensidad de postura '{intensidad_postura}' no reconocida. "
                f"Valores válidos: {sorted(INTENSIDADES_POSTURA)}"
            )
        intensidad_postura = ip
    # Neutral siempre "moderada" (no tiene dirección que intensificar)
    if postura == "neutral":
        intensidad_postura = INTENSIDAD_POSTURA_DEFAULT

    # Normalizar relevancia_al_post
    if relevancia_al_post is None:
        relevancia_al_post = RELEVANCIA_DEFAULT
    else:
        ra = str(relevancia_al_post).strip().lower()
        if ra not in RELEVANCIAS_POST:
            raise ValueError(
                f"Relevancia al post '{relevancia_al_post}' no reconocida. "
                f"Valores válidos: {sorted(RELEVANCIAS_POST)}"
            )
        relevancia_al_post = ra

    # Auto-detectar emocion/tono desde el texto si no se proveyeron
    emociones_lista = None
    if emociones is not None:
        # Punto 3: emociones como lista
        if isinstance(emociones, str):
            try:
                emociones_lista = json.loads(emociones)
            except (json.JSONDecodeError, TypeError):
                emociones_lista = [emociones]
        else:
            emociones_lista = list(emociones)
        if not emociones_lista:
            emociones_lista = [EMOCION_DEFAULT]
    elif emocion is not None:
        # Legacy: emoción única → envolver en lista
        emociones_lista = [emocion]
    else:
        # Auto-detectar desde el texto
        from analytics.emotion import classify_emotion
        er = classify_emotion(texto or "")
        emociones_lista = [er.emocion]
        if tono is None:
            tono = er.familia

    # Normalizar cada emoción de la lista
    emociones_normalizadas = []
    for emo in emociones_lista:
        try:
            emociones_normalizadas.append(normalizar_emocion(emo))
        except ValueError:
            if "_nueva_" in emo or emo.startswith("nueva_"):
                emociones_normalizadas.append(emo)
            else:
                emociones_normalizadas.append(EMOCION_DEFAULT)
    if not emociones_normalizadas:
        emociones_normalizadas = [EMOCION_DEFAULT]

    # Emoción dominante = primera de la lista (la que el usuario seleccionó primero)
    emocion_dominante = emociones_normalizadas[0]
    emociones_json = json.dumps(emociones_normalizadas, ensure_ascii=False)

    asegurar_tabla(db_path)
    conn = _conectar(db_path)
    try:
        conn.execute(
            f"""
            INSERT OR REPLACE INTO {TABLA}
            (comment_id, tema, tema_sugerido, tono, postura, confianza, texto,
             estado, fecha, emocion, subtema_especifico, intensidad_postura,
             emociones, relevancia_al_post)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'aprobado', ?, ?, ?, ?, ?, ?)
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
                emocion_dominante,
                subtema_especifico or None,
                intensidad_postura,
                emociones_json,
                relevancia_al_post,
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
    """Devuelve {comment_id: {tema, tema_sugerido, tono, postura, emocion,
    emociones, subtema_especifico, intensidad_postura, relevancia_al_post,
    confianza, texto, ...}}.

    `emociones` es una lista de claves (JSON parseado). `emocion` es la dominante
    (primera de la lista, o la legacy si la fila es anterior a la migración).
    """
    asegurar_tabla(db_path)
    conn = _conectar(db_path)
    try:
        rows = conn.execute(
            f"SELECT comment_id, tema, tema_sugerido, tono, postura, emocion, "
            f"confianza, texto, estado, fecha, subtema_especifico, "
            f"intensidad_postura, emociones, relevancia_al_post FROM {TABLA}"
        ).fetchall()
    finally:
        conn.close()
    salida = {}
    for (cid, tema, sug, tono, postura, emocion, conf, texto, estado, fecha,
         subtema, ipost, emociones_raw, relevancia) in rows:
        try:
            postura_norm = normalizar_postura(postura)
        except ValueError:
            postura_norm = POSTURA_DEFAULT
        try:
            emocion_norm = normalizar_emocion(emocion)
        except ValueError:
            if "_nueva_" not in emocion and not emocion.startswith("nueva_"):
                emocion_norm = EMOCION_DEFAULT
            else:
                emocion_norm = emocion
        # Parsear emociones JSON (Punto 3)
        if emociones_raw:
            try:
                emociones_lista = json.loads(emociones_raw)
                if not isinstance(emociones_lista, list):
                    emociones_lista = [emociones_raw]
            except (json.JSONDecodeError, TypeError):
                emociones_lista = [emociones_raw]
        else:
            # Fila legacy: usar emocion singular
            emociones_lista = [emocion_norm]
        salida[cid] = {
            "tema": tema,
            "tema_sugerido": sug,
            "tono": tono,
            "postura": postura_norm,
            "emocion": emocion_norm,
            "emociones": emociones_lista,
            "subtema_especifico": subtema,
            "intensidad_postura": ipost or INTENSIDAD_POSTURA_DEFAULT,
            "relevancia_al_post": relevancia or RELEVANCIA_DEFAULT,
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
    positivo. Se incluye ademas desglose por EMOCION con soporte para seleccion
    multiple (Punto 3): cada comentario contribuye a TODAS sus emociones
    seleccionadas, no solo a la dominante.

    Nuevos campos (Puntos 1-4):
    - saldo_ponderado: saldo ponderado por intensidad de postura (leve=1,
      moderada=2, fuerte=3). No reemplaza saldo simple.
    - subtema_especificoBreakdown: conteo de entidades/subtemas específicos.
    - relevance_excluidos: comentarios marcados como 'ruido_conversacional' que
      se excluyen de los conteos.

    Devuelve una lista de dicts ordenada de mayor a menor doc_count:
    {id, categoria, label, pct, doc_count, ejemplo, apoyo, critica, neutral,
     pct_apoyo, pct_critica, pct_neutral, saldo, saldo_ponderado,
     ejemplo_critica, emociones, emocion_dominante, entidades}.
    """
    asegurar_tabla(db_path)
    conn = _conectar(db_path)
    try:
        rows = conn.execute(
            f"SELECT tema, texto, postura, emocion, emociones, "
            f"intensidad_postura, subtema_especifico, relevancia_al_post "
            f"FROM {TABLA} WHERE estado='aprobado'"
        ).fetchall()
    finally:
        conn.close()

    _PESOS_INTENSIDAD = {"leve": 1, "moderada": 2, "fuerte": 3}

    conteo = defaultdict(int)
    posturas = defaultdict(lambda: {"apoyo": 0, "critica": 0, "neutral": 0})
    pesos = defaultdict(float)  # saldo ponderado por tema
    emociones_conteo = defaultdict(lambda: defaultdict(int))
    ejemplos = {}
    ejemplos_critica = {}
    entidades_conteo = defaultdict(lambda: defaultdict(int))
    total_con_tema = 0

    for tema, texto, postura, emocion_legacy, emociones_raw, ipost, subtema, relevancia in rows:
        if not tema or tema == "no_aplica":
            continue
        # Punto 4: excluir ruido conversacional
        if relevancia == "ruido_conversacional":
            continue

        try:
            post = normalizar_postura(postura)
        except ValueError:
            post = POSTURA_DEFAULT

        # Parsear emociones (Punto 3)
        if emociones_raw:
            try:
                emociones_lista = json.loads(emociones_raw)
                if not isinstance(emociones_lista, list):
                    emociones_lista = [emociones_raw]
            except (json.JSONDecodeError, TypeError):
                emociones_lista = [emociones_raw]
        else:
            # Fila legacy: usar emoción singular
            try:
                emociones_lista = [normalizar_emocion(emocion_legacy)]
            except ValueError:
                if "_nueva_" in emocion_legacy or emocion_legacy.startswith("nueva_"):
                    emociones_lista = [emocion_legacy]
                else:
                    emociones_lista = [EMOCION_DEFAULT]

        # Normalizar cada emoción de la lista
        emociones_norm = []
        for emo in emociones_lista:
            try:
                emociones_norm.append(normalizar_emocion(emo))
            except ValueError:
                if "_nueva_" in emo or emo.startswith("nueva_"):
                    emociones_norm.append(emo)
                else:
                    emociones_norm.append(EMOCION_DEFAULT)
        if not emociones_norm:
            emociones_norm = [EMOCION_DEFAULT]

        conteo[tema] += 1
        posturas[tema][post] += 1

        # Saldo ponderado (Punto 2)
        peso = _PESOS_INTENSIDAD.get(ipost or INTENSIDAD_POSTURA_DEFAULT, 2)
        if post == "apoyo":
            pesos[tema] += peso
        elif post == "critica":
            pesos[tema] -= peso

        # Conteo de emociones: cada emoción de la lista suma 1
        for emo in emociones_norm:
            emociones_conteo[tema][emo] += 1

        total_con_tema += 1

        # Entidad/subtema específico (Punto 1)
        if subtema:
            entidades_conteo[tema][subtema] += 1

        limpio = " ".join((texto or "").split())
        prev = ejemplos.get(tema)
        if limpio and (prev is None or 15 <= len(limpio) < len(prev)):
            ejemplos[tema] = limpio
        if post == "critica" and limpio:
            prev_c = ejemplos_critica.get(tema)
            if prev_c is None or 15 <= len(limpio) < len(prev_c):
                ejemplos_critica[tema] = limpio

    from dashboard.tema_taxonomia import EMOCIONES_VALIDAS

    temas = []
    for i, (tema, n) in enumerate(conteo.items()):
        ej = ejemplos.get(tema, "")
        if len(ej) > 120:
            ej = ej[:117] + "..."
        ej_c = ejemplos_critica.get(tema, "")
        if len(ej_c) > 120:
            ej_c = ej_c[:117] + "..."
        pst = posturas[tema]
        emo_counts = emociones_conteo.get(tema, {})
        emo_total = sum(emo_counts.values()) or 1
        emo_detalle = {
            e: {
                "count": emo_counts.get(e, 0),
                "pct": round(emo_counts.get(e, 0) / emo_total * 100, 1),
            }
            for e in EMOCIONES_VALIDAS
        }
        emo_dominante = max(EMOCIONES_VALIDAS, key=lambda e: emo_counts.get(e, 0)) if emo_counts else "calma"
        # Entidades del tema (top 5)
        entidades_tema = entidades_conteo.get(tema, {})
        entidades_sorted = sorted(entidades_tema.items(), key=lambda x: -x[1])[:5]

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
            "saldo_ponderado": round(pesos.get(tema, 0), 1),
            "ejemplo_critica": ej_c,
            "emociones": emo_detalle,
            "emocion_dominante": emo_dominante,
            "entidades": {e: c for e, c in entidades_sorted},
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


# ── Migraciones estructurales (8.3) ──────────────────────────


def asegurar_tabla_en_tiktok(tiktok_db_path):
    """Crea tema_aprobaciones en tiktok.db (mismo esquema que facebook.db)."""
    asegurar_tabla(tiktok_db_path)


def _asegurar_columnas_computed(conn, tabla):
    """Agrega columnas computed (sentiment, sentiment_score, topic_category, zona)
    a una tabla de comentarios si no existen. Idempotente."""
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({tabla})").fetchall()}
    migraciones = [
        ("sentiment", "TEXT"),
        ("sentiment_score", "FLOAT"),
        ("topic_category", "TEXT"),
        ("zona", "TEXT"),
    ]
    for col, tipo in migraciones:
        if col not in cols:
            conn.execute(f"ALTER TABLE {tabla} ADD COLUMN {col} {tipo}")


def asegurar_computed_tiktok(tiktok_db_path):
    """Agrega columnas sentiment/sentiment_score/topic_category/zona a
    tiktok.db::comments (misma estructura que fb_comments)."""
    conn = _conectar(tiktok_db_path)
    try:
        _asegurar_columnas_computed(conn, "comments")
        conn.commit()
    finally:
        conn.close()


def asegurar_computed_externos(externos_db_path):
    """Agrega columnas sentiment/sentiment_score/topic_category/zona a
    externos.db::external_comments."""
    conn = _conectar(externos_db_path)
    try:
        _asegurar_columnas_computed(conn, "external_comments")
        conn.commit()
    finally:
        conn.close()

