"""Persistencia de aprobaciones manuales de temas.

Guarda, por comentario (comment_id de fb_comments), el tema que el usuario
APROBO manualmente y su POSTURA (apoyo/critica/neutral).

La postura es un eje SEPARADO del tema (ver dashboard/tema_taxonomia.py): permite
que la tarjeta de cada tema se divida en apoyo / critica / neutral y que una
critica NO se cuente como impulso positivo del tema.

La postura se calcula automaticamente a partir de la emoción usando una tabla
de valencia fija (VALENCIA_POSTURA). El humano clasifica la emoción; la
postura se deriva determinísticamente.

Campos:
  - intensidad_postura: leve/moderada/fuerte (nullable, default moderada)
  - emociones: JSON array de 1+ claves de emoción (reemplaza emoción única)

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
    EMOCIONES,
    etiqueta_tema,
    normalizar_emocion,
    normalizar_postura,
    remapear,
    familia_de,
)

TABLA = "tema_aprobaciones"

INTENSIDADES_POSTURA = {"leve", "moderada", "fuerte"}
INTENSIDAD_POSTURA_DEFAULT = "moderada"


# ---------------------------------------------------------------------------
# Tabla de valencia fija: emoción/familia → postura.
#
# Determinística, sin modelo nuevo. Se usa la familia de la emoción (ya
# definida en tema_taxonomia.py::EMOCIONES) para ubicarla en esta tabla.
# Las claves aquí son familias de Plutchik + prefijo "civica".
# ---------------------------------------------------------------------------

VALENCIA_POSTURA = {
    "apoyo": {
        "joy", "trust", "anticipation",
        "esperanza",
    },
    "critica": {
        "fear", "sadness", "disgust", "anger",
        "envidia", "desprecio", "indignacion", "incredulidad",
        "ansiedad", "pesimismo",
    },
    "neutral": {
        "surprise", "civica",
        "culpa", "curiosidad",
    },
}


def derivar_postura(emocion: str) -> str:
    """Deriva postura (apoyo/critica/neutral) a partir de una emoción.

    Busca primero la clave de emoción directamente en VALENCIA_POSTURA
    (para díadas mapeadas explícitamente). Si no se encuentra, usa la
    familia de Plutchik (via familia_de()).

    Para emociones cívicas (familia "civica" o claves que empiezan con
    "civica_"), devuelve "neutral".
    """
    if not emocion:
        return POSTURA_DEFAULT
    for postura, keys in VALENCIA_POSTURA.items():
        if emocion in keys:
            return postura
    fam = familia_de(emocion)
    for postura, keys in VALENCIA_POSTURA.items():
        if fam in keys:
            return postura
    return POSTURA_DEFAULT


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


def _reconstruir_tabla(db_path):
    """Reconstruye tema_aprobaciones eliminando columnas obsoletas.

    SQLite < 3.35 no soporta DROP COLUMN. Estrategia:
    1. Crear tabla nueva sin las columnas obsoletas.
    2. Copiar filas existentes.
    3. Drop vieja + rename nueva.
    """
    conn = _conectar(db_path)
    try:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({TABLA})").fetchall()]
        cols_a_quitar = {"subtema_especifico", "relevancia_al_post"}
        if not cols_a_quitar.intersection(cols):
            return False

        colnames = [c for c in cols if c not in cols_a_quitar]
        col_list = ", ".join(colnames)

        conn.execute(f"CREATE TABLE {TABLA}_nueva AS SELECT {col_list} FROM {TABLA}")
        conn.execute(f"DROP TABLE {TABLA}")
        conn.execute(f"ALTER TABLE {TABLA}_nueva RENAME TO {TABLA}")
        conn.commit()
        return True
    finally:
        conn.close()


def asegurar_tabla(db_path):
    """Crea la tabla de aprobaciones si no existe y la migra si es de una
    version anterior (agrega columnas postura, emocion,
    intensidad_postura, emociones).

    Si la tabla tiene columnas obsoletas (subtema_especifico,
    relevancia_al_post), las elimina via reconstruccion."""
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
                intensidad_postura TEXT DEFAULT 'moderada',
                emociones TEXT
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
        if "intensidad_postura" not in cols:
            conn.execute(
                f"ALTER TABLE {TABLA} ADD COLUMN intensidad_postura TEXT DEFAULT 'moderada'"
            )
        if "emociones" not in cols:
            conn.execute(
                f"ALTER TABLE {TABLA} ADD COLUMN emociones TEXT"
            )
        conn.commit()
    finally:
        conn.close()

    _reconstruir_tabla(db_path)


def guardar_aprobacion(db_path, comment_id, tema, texto="",
                       tema_sugerido=None, tono=None, confianza=None,
                       postura=None, emocion=None, emociones=None,
                       intensidad_postura=None):
    """Guarda (o actualiza) la aprobacion de un comentario.

    Devuelve True si se guardo. En la aprobacion MANUAL validamos de forma
    estricta: solo se aceptan categorias englobantes validas o claves legacy
    conocidas (que luego se remapean a su englobante). Cualquier otro tema
    inexistente -o falta comment_id/tema- no guarda y devuelve False.

    `postura` se calcula automaticamente a partir de la emoción via
    derivar_aprobacion(). Si se pasa explicitamente, se ignora — la postura
    SIEMPRE se deriva de la emoción.

    `intensidad_postura` (leve/moderada/fuerte): solo aplica a apoyo y critica.
    Para neutral se usa "moderada" por defecto. Lanza ValueError si no es
    reconocida.

    `emociones` (Punto 3): lista de 1+ claves de emoción. Se guarda como JSON.
    Si se provee `emocion` (legacy) en vez de `emociones`, se envuelve en lista.

    `emocion` (legacy) se normaliza con normalizar_emocion(); lanza ValueError
    si no es reconocida. Si no se provee `emocion` ni `emociones`, se auto-detecta
    desde el texto usando classify_emotion().

    Raises:
        ValueError: si intensidad_postura o emociones no son reconocidas.
    """
    if not comment_id or not tema:
        return False
    if tema not in CATEGORIAS_VALIDAS and tema not in REMAP_LEGACY:
        return False
    tema = remapear(tema)

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

    # Auto-detectar emocion/tono desde el texto si no se proveyeron
    emociones_lista = None
    if emociones is not None:
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
        emociones_lista = [emocion]
    else:
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

    emocion_dominante = emociones_normalizadas[0]
    emociones_json = json.dumps(emociones_normalizadas, ensure_ascii=False)

    # Derivar postura a partir de la emoción dominante (tabla de valencia fija)
    postura = derivar_postura(emocion_dominante)
    # Neutral siempre "moderada" (no tiene dirección que intensificar)
    if postura == "neutral":
        intensidad_postura = INTENSIDAD_POSTURA_DEFAULT

    asegurar_tabla(db_path)
    conn = _conectar(db_path)
    try:
        conn.execute(
            f"""
            INSERT OR REPLACE INTO {TABLA}
            (comment_id, tema, tema_sugerido, tono, postura, confianza, texto,
             estado, fecha, emocion, intensidad_postura, emociones)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'aprobado', ?, ?, ?, ?)
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
                intensidad_postura,
                emociones_json,
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
    emociones, intensidad_postura, confianza, texto, ...}}.

    `emociones` es una lista de claves (JSON parseado). `emocion` es la dominante
    (primera de la lista, o la legacy si la fila es anterior a la migración).
    """
    asegurar_tabla(db_path)
    conn = _conectar(db_path)
    try:
        rows = conn.execute(
            f"SELECT comment_id, tema, tema_sugerido, tono, postura, emocion, "
            f"confianza, texto, estado, fecha, "
            f"intensidad_postura, emociones FROM {TABLA}"
        ).fetchall()
    finally:
        conn.close()
    salida = {}
    for (cid, tema, sug, tono, postura, emocion, conf, texto, estado, fecha,
         ipost, emociones_raw) in rows:
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
        if emociones_raw:
            try:
                emociones_lista = json.loads(emociones_raw)
                if not isinstance(emociones_lista, list):
                    emociones_lista = [emociones_raw]
            except (json.JSONDecodeError, TypeError):
                emociones_lista = [emociones_raw]
        else:
            emociones_lista = [emocion_norm]
        salida[cid] = {
            "tema": tema,
            "tema_sugerido": sug,
            "tono": tono,
            "postura": postura_norm,
            "emocion": emocion_norm,
            "emociones": emociones_lista,
            "intensidad_postura": ipost or INTENSIDAD_POSTURA_DEFAULT,
            "confianza": conf,
            "texto": texto,
            "estado": estado,
            "fecha": fecha,
        }
    return salida


def _agregar_desde_filas(filas):
    """filas: iterable de (tema, texto, postura, emocion_legacy, emociones_raw, intensidad_postura).
    Contiene la lógica de conteo/agregación ya existente en agregar_por_tema.
    """
    _PESOS_INTENSIDAD = {"leve": 1, "moderada": 2, "fuerte": 3}

    conteo = defaultdict(int)
    posturas = defaultdict(lambda: {"apoyo": 0, "critica": 0, "neutral": 0})
    pesos = defaultdict(float)
    emociones_conteo = defaultdict(lambda: defaultdict(int))
    ejemplos = {}
    ejemplos_critica = {}
    total_con_tema = 0

    for tema, texto, postura, emocion_legacy, emociones_raw, ipost in filas:
        if not tema or tema == "no_aplica":
            continue

        try:
            post = normalizar_postura(postura)
        except ValueError:
            post = POSTURA_DEFAULT

        if emociones_raw:
            try:
                emociones_lista = json.loads(emociones_raw)
                if not isinstance(emociones_lista, list):
                    emociones_lista = [emociones_raw]
            except (json.JSONDecodeError, TypeError):
                emociones_lista = [emociones_raw]
        else:
            try:
                emociones_lista = [normalizar_emocion(emocion_legacy)]
            except ValueError:
                if "_nueva_" in emocion_legacy or emocion_legacy.startswith("nueva_"):
                    emociones_lista = [emocion_legacy]
                else:
                    emociones_lista = [EMOCION_DEFAULT]

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

        peso = _PESOS_INTENSIDAD.get(ipost or INTENSIDAD_POSTURA_DEFAULT, 2)
        if post == "apoyo":
            pesos[tema] += peso
        elif post == "critica":
            pesos[tema] -= peso

        for emo in emociones_norm:
            emociones_conteo[tema][emo] += 1

        total_con_tema += 1

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
        emo_dominante = max(EMOCIONES_VALIDAS, key=lambda e: (emo_counts.get(e, 0), e)) if emo_counts else "calma"

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
        })
    temas.sort(key=lambda x: -x["doc_count"])
    return temas


def agregar_por_tema(db_path):
    """Agrega los comentarios APROBADOS por tema (para las tarjetas).

    Excluye 'no_aplica'. El porcentaje es sobre el total de comentarios con un
    tema aprobado (no sobre el total analizado). Cada tema se divide ademas por
    POSTURA (apoyo/critica/neutral) para que una critica no se lea como impulso
    positivo. Se incluye ademas desglose por EMOCION con soporte para seleccion
    multiple (Punto 3): cada comentario contribuye a TODAS sus emociones
    seleccionadas, no solo a la dominante.

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
            f"intensidad_postura "
            f"FROM {TABLA} WHERE estado='aprobado'"
        ).fetchall()
    finally:
        conn.close()
    return _agregar_desde_filas(rows)


def agregar_por_tema_automatico(db_path, tabla="fb_comments", col_id="comment_id", col_texto="message"):
    """Cuenta temas automáticamente vía clasificación léxica (classify_topic),
    sin aprobación manual. Cada comentario con texto se clasifica y se cuenta
    bajo el tema detectado (excluye 'no_aplica'/sin coincidencias). La postura
    se deriva de la columna 'emocion' persistida en el comentario, si existe;
    si no existe la columna, se usa EMOCION_DEFAULT. La intensidad de postura
    usa siempre INTENSIDAD_POSTURA_DEFAULT ('moderada'), porque no hay revisión
    humana que la ajuste.
    """
    from analytics.topic import classify_topic
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({tabla})").fetchall()]
        tiene_emocion = "emocion" in cols
        if tiene_emocion:
            rows_raw = conn.execute(
                f"SELECT {col_texto}, emocion FROM {tabla} "
                f"WHERE {col_texto} IS NOT NULL AND {col_texto} != ''"
            ).fetchall()
        else:
            rows_raw = [
                (r[0], None) for r in conn.execute(
                    f"SELECT {col_texto} FROM {tabla} "
                    f"WHERE {col_texto} IS NOT NULL AND {col_texto} != ''"
                ).fetchall()
            ]
    finally:
        conn.close()

    filas = []
    for texto, emocion in rows_raw:
        resultado = classify_topic(texto)
        if not resultado.tema or resultado.tema == "no_aplica":
            continue
        emo = emocion or EMOCION_DEFAULT
        filas.append((
            resultado.tema, texto, derivar_postura(emo), emo, None,
            INTENSIDAD_POSTURA_DEFAULT,
        ))

    return _agregar_desde_filas(filas)


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


def _asegurar_columnas_emocion(conn, tabla):
    """Agrega columnas emocion/intensidad/confianza_emocion/tema_sugerido
    a una tabla de comentarios si no existen. Idempotente."""
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({tabla})").fetchall()}
    migraciones = [
        ("emocion", "TEXT"),
        ("intensidad", "TEXT"),
        ("confianza_emocion", "TEXT"),
        ("tema_sugerido", "TEXT"),
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
