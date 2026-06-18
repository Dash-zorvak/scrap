import sqlite3
import pandas as pd
import numpy as np
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import *
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize
import re


STOPWORDS = {
    "de","la","el","en","y","a","los","las","un","una","un","es","se",
    "que","por","con","del","al","su","sus","para","como","más",
    "pero","o","si","le","lo","ya","fue","son","hay","este","esta",
    "no","ni","lo","les","las","dos","muy","cada","todo","todos",
    "una","uno","sin","ha","han","he","has","han","haber",
    "ser","sido","siendo","está","están","estaba","estado",
    "tiene","tener","tenido","tuvo","tenia","tenían","tengan",
    "hace","hacen","hacer","hecho","hicieron","hacia",
    "puede","pueden","poder","pudo","podido","podría",
    "dice","dijo","decir","dicho","dicen",
    "ver","vio","visto","ve","ven","vemos",
    "saber","sabe","sabía","sabido",
    "dar","dio","dado","da","dan",
    "ir","fue","ido","va","van","vaya",
    "otro","otros","otra","otras","mismo","mismos","misma","mismas",
    "entre","sino","tanto","poco","poca","pocos","pocas",
    "siempre","nunca","también","porque","cuando","donde",
    "solo","sólo","bien","gran","mayor","menor","mejor","peor",
    "ante","bajo","cabe","contra","durante","excepto","hasta",
    "mediante","para","segun","sobre","tras","versus","via",
}


def limpiar_texto(texto):
    if not texto:
        return None
    texto = texto.lower()
    texto = re.sub(r"http\S+", "", texto)
    texto = re.sub(r"@\w+", "", texto)
    texto = re.sub(r"#\w+", "", texto)
    texto = re.sub(r"[^a-záéíóúüñ0-9\s]", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    palabras = [p for p in texto.split() if p not in STOPWORDS and len(p) > 2]
    if len(palabras) < 3:
        return None
    return " ".join(palabras)


def generar_embeddings(textos, batch_size=64):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    todos = []
    for i in range(0, len(textos), batch_size):
        batch = textos[i:i+batch_size]
        emb = model.encode(batch, show_progress_bar=True)
        todos.append(emb)
        print(f"  Embeddings: {min(i+batch_size, len(textos))}/{len(textos)}")
    return np.vstack(todos)


def categorizar_posts(fb_db=None, tk_db=None):
    if fb_db is None:
        fb_db = FACEBOOK_DB
    if tk_db is None:
        tk_db = TIKTOK_DB

    placeholders = ",".join(repr(p) for p in FB_PAGES_OFICIALES)
    conn = sqlite3.connect(fb_db)
    df_fb = pd.read_sql_query(
        f"SELECT post_id as item_id, 'facebook' as plataforma, "
        f"message as texto, created_time as fecha "
        f"FROM fb_posts WHERE page_name IN ({placeholders}) "
        f"AND created_time IS NOT NULL AND message IS NOT NULL AND message != ''",
        conn
    )
    conn.close()

    conn = sqlite3.connect(tk_db)
    df_tt = pd.read_sql_query(
        "SELECT id as item_id, 'tiktok' as plataforma, "
        "description as texto, created_at as fecha "
        "FROM videos WHERE description IS NOT NULL AND description != ''",
        conn
    )
    conn.close()

    print(f"  FB posts: {len(df_fb)}")
    print(f"  TT videos: {len(df_tt)}")

    df = pd.concat([df_fb, df_tt], ignore_index=True)
    print(f"  Total items: {len(df)}")

    df["texto_limpio"] = df["texto"].apply(limpiar_texto)
    df = df[df["texto_limpio"].notna()].copy()
    print(f"  Después de limpieza: {len(df)}")

    if len(df) == 0:
        print("  ⚠️ No hay textos válidos para categorizar; se omite KMeans.")
        conn = sqlite3.connect(fb_db)
        pd.DataFrame(columns=["item_id", "plataforma", "cluster_id", "texto_limpio"]).to_sql(
            "post_categorias", conn, if_exists="replace", index=False
        )
        conn.close()
        return

    textos = df["texto_limpio"].tolist()
    print("  Generando embeddings...")
    X = generar_embeddings(textos)
    X = normalize(X)

    k = min(8, len(df))
    print(f"  Corriendo KMeans con k={k}...")
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    df["cluster_id"] = km.fit_predict(X)
    centroides = km.cluster_centers_

    print("\n" + "="*60)
    print("CLUSTERS DETECTADOS")
    print("="*60)

    distancias = km.transform(X)

    for c in range(k):
        mask = df["cluster_id"] == c
        n_items = mask.sum()
        print(f"\n--- Cluster {c} ({n_items} items) ---")

        idx_in_cluster = np.where(mask)[0]
        dists_in_cluster = distancias[idx_in_cluster, c]
        closest_5 = idx_in_cluster[np.argsort(dists_in_cluster)[:5]]

        for rank, idx in enumerate(closest_5, 1):
            row = df.iloc[idx]
            txt = row["texto_limpio"][:100]
            plat = row["plataforma"]
            print(f"  {rank}. [{plat}] {txt}")

    conn = sqlite3.connect(fb_db)
    df[["item_id", "plataforma", "cluster_id", "texto_limpio"]].to_sql(
        "post_categorias", conn, if_exists="replace", index=False
    )
    conn.close()
    print(f"\n✓ {len(df)} items categorizados guardados en post_categorias")


def guardar_nombres_clusters(fb_db=None):
    if fb_db is None:
        fb_db = FACEBOOK_DB
    nombres = {
        0: "Obras viales y calles",
        1: "Contenido promocional",
        2: "Logros del alcalde",
        3: "Gestión municipal",
        4: "Beneficios comunitarios",
        5: "Eventos y cultura",
        6: "Proyectos urbanos Santa Ana",
        7: "Deporte",
    }

    conn = sqlite3.connect(fb_db)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(post_categorias)")
    cols = [r[1] for r in cur.fetchall()]
    if "categoria_nombre" not in cols:
        cur.execute("ALTER TABLE post_categorias ADD COLUMN categoria_nombre TEXT")

    for cid, nombre in nombres.items():
        cur.execute(
            "UPDATE post_categorias SET categoria_nombre = ? WHERE cluster_id = ?",
            (nombre, cid),
        )
    conn.commit()

    cur.execute(
        "SELECT categoria_nombre, COUNT(*) as cnt FROM post_categorias "
        "GROUP BY categoria_nombre ORDER BY cnt DESC"
    )
    rows = cur.fetchall()
    print("\n=== DISTRIBUCIÓN POR CATEGORÍA ===")
    for nombre, cnt in rows:
        print(f"  {nombre}: {cnt}")
    conn.close()


if __name__ == "__main__":
    print("▶ Generando embeddings y categorizando posts...")
    print("  (descarga modelo ~120MB primera vez)")
    categorizar_posts()
    print("\n▶ Asignando nombres a clusters...")
    guardar_nombres_clusters()
    print("✓ Módulo 1 completo.")
