import sqlite3
import json
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import *
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize


STOPWORDS = {
    "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las", "por",
    "un", "para", "con", "no", "una", "su", "al", "lo", "como", "mas", "pero",
    "sus", "le", "ya", "o", "este", "si", "porque", "esta", "entre", "cuando",
    "muy", "sin", "sobre", "tambien", "me", "hasta", "hay", "donde", "quien",
    "desde", "todo", "nos", "durante", "todos", "uno", "les", "ni", "contra",
    "otros", "ese", "eso", "ante", "ellos", "e", "esto", "mi", "antes", "algunos",
    "que", "unos", "yo", "otro", "otras", "otra", "el", "tanto", "esa", "estos",
    "mucho", "quienes", "nada", "muchos", "cual", "poco", "ella", "estar", "estas",
    "algunas", "algo", "nosotros",
}


def limpiar_texto(texto):
    if not texto:
        return ""
    texto = str(texto).lower()
    tokens = [t for t in texto.split() if len(t) > 2 and t not in STOPWORDS]
    if len(tokens) < 3:
        return ""
    return " ".join(tokens)


def generar_embeddings(textos, batch_size=64):
    """Genera embeddings con SentenceTransformer (carga perezosa del modelo)."""
    from sentence_transformers import SentenceTransformer
    modelo = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    vecs = []
    for i in range(0, len(textos), batch_size):
        lote = textos[i:i + batch_size]
        vecs.append(modelo.encode(lote, show_progress_bar=False))
    return np.vstack(vecs)


# ---------------------------------------------------------------------------
# Cache de embeddings
# ---------------------------------------------------------------------------
# El paso mas caro del pipeline NO es KMeans, sino generar los embeddings
# (cargar un modelo de ~120MB y codificar cada texto). Antes se recomputaban
# TODOS los embeddings en cada lote aunque el contenido no hubiera cambiado.
# Ahora se cachean por (item_id, plataforma) y solo se generan para items
# nuevos o cuyo texto haya cambiado.

def _asegurar_tabla_emb(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS item_embeddings (
            item_id TEXT,
            plataforma TEXT,
            texto_limpio TEXT,
            embedding TEXT,
            PRIMARY KEY (item_id, plataforma)
        )
        """
    )
    conn.commit()


def _cargar_cache_embeddings(conn):
    """Devuelve {(item_id, plataforma): (texto_limpio, np.ndarray)}."""
    _asegurar_tabla_emb(conn)
    cache = {}
    for item_id, plataforma, texto, emb_json in conn.execute(
        "SELECT item_id, plataforma, texto_limpio, embedding FROM item_embeddings"
    ):
        try:
            vec = np.array(json.loads(emb_json), dtype=float)
        except Exception:
            continue
        cache[(item_id, plataforma)] = (texto, vec)
    return cache


def _guardar_cache_embeddings(conn, filas):
    """Upsert de (item_id, plataforma, texto_limpio, embedding)."""
    _asegurar_tabla_emb(conn)
    conn.executemany(
        """
        INSERT INTO item_embeddings (item_id, plataforma, texto_limpio, embedding)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(item_id, plataforma) DO UPDATE SET
            texto_limpio = excluded.texto_limpio,
            embedding = excluded.embedding
        """,
        filas,
    )
    conn.commit()


def _items_en_post_categorias(conn):
    try:
        rows = conn.execute(
            "SELECT item_id, plataforma FROM post_categorias"
        ).fetchall()
        return {(r[0], r[1]) for r in rows}
    except Exception:
        return set()


def categorizar_posts(fb_db=None, tk_db=None):
    if fb_db is None:
        fb_db = FACEBOOK_DB
    if tk_db is None:
        tk_db = TIKTOK_DB

    # --- Cargar items oficiales de FB ---
    conn_fb = sqlite3.connect(fb_db)
    placeholders = ",".join(repr(p) for p in FB_PAGES_OFICIALES)
    df_fb = pd.read_sql_query(
        f"""
        SELECT post_id as item_id, 'facebook' as plataforma,
               message as texto, created_time as fecha
        FROM fb_posts
        WHERE page_name IN ({placeholders})
        """,
        conn_fb,
    )
    conn_fb.close()

    # --- Cargar videos de TikTok ---
    conn_tk = sqlite3.connect(tk_db)
    df_tk = pd.read_sql_query(
        """
        SELECT id as item_id, 'tiktok' as plataforma,
               description as texto, created_at as fecha
        FROM videos
        """,
        conn_tk,
    )
    conn_tk.close()

    df = pd.concat([df_fb, df_tk], ignore_index=True)
    df["texto_limpio"] = df["texto"].apply(limpiar_texto)
    df = df[df["texto_limpio"] != ""].reset_index(drop=True)

    # post_categorias y el cache de embeddings viven en la BD de FB.
    conn = sqlite3.connect(fb_db)

    if len(df) == 0:
        # Sin items: persistir tabla vacia para no romper lectores aguas abajo.
        pd.DataFrame(
            columns=["item_id", "plataforma", "cluster_id", "texto_limpio"]
        ).to_sql("post_categorias", conn, if_exists="replace", index=False)
        conn.close()
        print("  Categorias: 0 items con texto util")
        return

    cache = _cargar_cache_embeddings(conn)
    items_actuales = {(r.item_id, r.plataforma) for r in df.itertuples()}

    # Determinar que items necesitan (re)generar embedding: nuevos o con
    # texto modificado respecto al cache.
    necesitan_idx = []
    for i, row in df.iterrows():
        clave = (row["item_id"], row["plataforma"])
        cacheado = cache.get(clave)
        if cacheado is None or cacheado[0] != row["texto_limpio"]:
            necesitan_idx.append(i)

    # Si no hay nada nuevo y post_categorias ya cubre exactamente estos items,
    # no hay nada que recomputar: el paso se omite por completo.
    if not necesitan_idx and _items_en_post_categorias(conn) == items_actuales:
        conn.close()
        print(f"  Categorias: sin cambios, {len(df)} items ya categorizados (omitido)")
        return

    # Generar embeddings SOLO para los items nuevos / modificados.
    if necesitan_idx:
        textos_nuevos = df.loc[necesitan_idx, "texto_limpio"].tolist()
        print(f"  Embeddings: generando {len(textos_nuevos)} nuevos (cache: {len(cache)})")
        nuevos_emb = generar_embeddings(textos_nuevos)
        filas_cache = []
        for j, i in enumerate(necesitan_idx):
            clave = (df.at[i, "item_id"], df.at[i, "plataforma"])
            vec = np.asarray(nuevos_emb[j], dtype=float)
            cache[clave] = (df.at[i, "texto_limpio"], vec)
            filas_cache.append(
                (clave[0], clave[1], df.at[i, "texto_limpio"], json.dumps(vec.tolist()))
            )
        _guardar_cache_embeddings(conn, filas_cache)
    else:
        print(f"  Embeddings: 0 nuevos (cache: {len(cache)}), re-clustering por cambio de items")

    # Construir matriz X completa desde el cache (orden de df).
    X = np.vstack([cache[(r["item_id"], r["plataforma"])][1] for _, r in df.iterrows()])
    X = normalize(X)

    k = min(8, len(df))
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    df["cluster_id"] = km.fit_predict(X)

    df[["item_id", "plataforma", "cluster_id", "texto_limpio"]].to_sql(
        "post_categorias", conn, if_exists="replace", index=False
    )
    conn.close()

    print(f"  Categorias: {len(df)} items en {k} clusters")


def guardar_nombres_clusters(fb_db=None):
    if fb_db is None:
        fb_db = FACEBOOK_DB
    nombres = {
        0: "Obras y proyectos",
        1: "Servicios municipales",
        2: "Eventos y cultura",
        3: "Seguridad",
        4: "Salud y medio ambiente",
        5: "Educacion y juventud",
        6: "Transparencia y gestion",
        7: "Comunicados generales",
    }
    conn = sqlite3.connect(fb_db)
    try:
        conn.execute("ALTER TABLE post_categorias ADD COLUMN categoria_nombre TEXT")
    except Exception:
        pass
    for cid, nombre in nombres.items():
        conn.execute(
            "UPDATE post_categorias SET categoria_nombre = ? WHERE cluster_id = ?",
            (nombre, cid),
        )
    conn.commit()
    conn.close()
    print("  Nombres de categorias guardados")


if __name__ == "__main__":
    print("\u25b6 Categorizando contenido...")
    categorizar_posts()
    guardar_nombres_clusters()
    print("\u2713 M\u00f3dulo 1 completo.")
