import sqlite3
import os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "facebook.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

def p(label, val=""):
    print(f"{label}: {val}")

def sep(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")

# ─── 1. Basic counts ─────────────────────────────────────────────
sep("1. BASIC COUNTS")

cur.execute("SELECT COUNT(*) FROM fb_posts")
p("Total posts", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM fb_comments")
p("Total comments", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM fb_comments WHERE message IS NOT NULL")
p("Comments with non-null message", cur.fetchone()[0])

cur.execute("SELECT MIN(created_time), MAX(created_time) FROM fb_posts")
r = cur.fetchone()
p("Date range of posts (created_time)", f"{r[0]}  to  {r[1]}")

cur.execute("SELECT page_name, COUNT(*) AS cnt FROM fb_posts GROUP BY page_name ORDER BY cnt DESC")
rows = cur.fetchall()
print("\nPosts per page_name:")
for r in rows:
    print(f"  {r[0]}: {r[1]}")

# ─── 2. Reaction counts (all posts) ──────────────────────────────
sep("2. REACTION COUNTS (sums across all posts)")

for col in ["likes_count","loves_count","cares_count","hahas_count","wows_count",
            "sads_count","angrys_count","comments_count","shares_count","views_count"]:
    cur.execute(f"SELECT COALESCE(SUM({col}),0) FROM fb_posts")
    p(f"Total {col}", cur.fetchone()[0])

# ─── 3. Per-page breakdown ───────────────────────────────────────
sep("3. PER-PAGE BREAKDOWN")

reaction_cols = ["likes_count","loves_count","cares_count","hahas_count","wows_count",
                 "sads_count","angrys_count","comments_count","shares_count","views_count"]
sum_expr = ", ".join([f"COALESCE(SUM({c}),0) AS {c}" for c in reaction_cols])
engagement_expr = "+".join(reaction_cols[:7] + ["comments_count","shares_count"])

cur.execute(f"""
    SELECT page_name,
           COUNT(*) AS cnt,
           {sum_expr},
           COALESCE(SUM({engagement_expr}),0) AS total_engagement
    FROM fb_posts
    GROUP BY page_name
    ORDER BY cnt DESC
""")
rows = cur.fetchall()
for r in rows:
    d = dict(r)
    print(f"\n  page_name: {d['page_name']}")
    print(f"    posts: {d['cnt']}")
    for c in reaction_cols:
        print(f"    {c}: {d[c]}")
    print(f"    total_engagement: {d['total_engagement']}")

# ─── 4. Daily volume ─────────────────────────────────────────────
sep("4. DAILY VOLUME")

cur.execute("""
    SELECT DATE(created_time) AS d, COUNT(*) AS cnt
    FROM fb_posts
    GROUP BY d ORDER BY d
""")
print("\nPosts per day:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

cur.execute("""
    SELECT DATE(created_time) AS d, COUNT(*) AS cnt
    FROM fb_comments
    GROUP BY d ORDER BY d
""")
print("\nComments per day:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

# ─── 5. Sentiment from fb_sentimiento ────────────────────────────
sep("5. fb_sentimiento")

cur.execute("SELECT * FROM fb_sentimiento")
rows = cur.fetchall()
print(f"\nTotal rows in fb_sentimiento: {len(rows)}")
print("\nAll rows:")
for r in rows:
    print(dict(r))

cur.execute("SELECT AVG(pct_positivo), AVG(pct_negativo), AVG(pct_neutral) FROM fb_sentimiento")
r = cur.fetchone()
print(f"\nAverages:  pct_positivo={r[0]:.4f}  pct_negativo={r[1]:.4f}  pct_neutral={r[2]:.4f}")

# ─── 6. Engagement from fb_engagement ────────────────────────────
sep("6. fb_engagement")

cur.execute("SELECT * FROM fb_engagement")
rows = cur.fetchall()
print(f"\nTotal rows in fb_engagement: {len(rows)}")
print("\nAll rows:")
for r in rows:
    print(dict(r))

cur.execute("SELECT COALESCE(SUM(engagement_total),0), COALESCE(AVG(engagement_total),0), COALESCE(SUM(score_emocional),0), COALESCE(AVG(score_emocional),0) FROM fb_engagement")
r = cur.fetchone()
print(f"\nengagement_total: sum={r[0]:.4f}  avg={r[1]:.4f}")
print(f"score_emocional: sum={r[2]:.4f}  avg={r[3]:.4f}")

# ─── 7. tema_aprobaciones ────────────────────────────────────────
sep("7. tema_aprobaciones")

cur.execute("SELECT tema, COUNT(*) AS cnt FROM tema_aprobaciones GROUP BY tema ORDER BY cnt DESC")
print("\nCount per topic (tema):")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

cur.execute("SELECT emocion, COUNT(*) AS cnt FROM tema_aprobaciones GROUP BY emocion ORDER BY cnt DESC")
print("\nCount per emotion (emocion):")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

cur.execute("SELECT postura, COUNT(*) AS cnt FROM tema_aprobaciones GROUP BY postura ORDER BY cnt DESC")
print("\nCount per postura:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

cur.execute("SELECT tono, COUNT(*) AS cnt FROM tema_aprobaciones GROUP BY tono ORDER BY cnt DESC")
print("\nCount per tone (tono):")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

cur.execute("""
    SELECT tema, postura, COUNT(*) AS cnt
    FROM tema_aprobaciones
    GROUP BY tema, postura
    ORDER BY tema, postura
""")
print("\nCross-tab: topic × postura:")
for r in cur.fetchall():
    print(f"  tema={r[0]!r}  postura={r[1]!r}  cnt={r[2]}")

cur.execute("""
    SELECT emocion, postura, COUNT(*) AS cnt
    FROM tema_aprobaciones
    GROUP BY emocion, postura
    ORDER BY emocion, postura
""")
print("\nCross-tab: emotion × postura:")
for r in cur.fetchall():
    print(f"  emocion={r[0]!r}  postura={r[1]!r}  cnt={r[2]}")

# ─── 8. tema_clasificaciones_ia ──────────────────────────────────
sep("8. tema_clasificaciones_ia")

cur.execute("SELECT tema, COUNT(*) AS cnt FROM tema_clasificaciones_ia GROUP BY tema ORDER BY cnt DESC")
print("\nCount per topic:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

cur.execute("SELECT postura, COUNT(*) AS cnt FROM tema_clasificaciones_ia GROUP BY postura ORDER BY cnt DESC")
print("\nCount per postura:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

cur.execute("SELECT tono, COUNT(*) AS cnt FROM tema_clasificaciones_ia GROUP BY tono ORDER BY cnt DESC")
print("\nCount per tone (tono):")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

# ─── 9. post_categorias ──────────────────────────────────────────
sep("9. post_categorias")

cur.execute("SELECT * FROM post_categorias")
print("\nAll rows:")
for r in cur.fetchall():
    print(dict(r))

# Also per cluster if cluster_id exists
cur.execute("SELECT cluster_id, categoria_nombre, COUNT(*) AS cnt FROM post_categorias GROUP BY cluster_id, categoria_nombre ORDER BY cnt DESC")
print("\nCount per cluster_id / categoria_nombre:")
for r in cur.fetchall():
    print(f"  cluster_id={r[0]}  categoria_nombre={r[1]!r}  cnt={r[2]}")

# ─── 10. item_embeddings ─────────────────────────────────────────
sep("10. item_embeddings")

# Check columns
cur.execute("PRAGMA table_info(item_embeddings)")
cols = [r[1] for r in cur.fetchall()]
print(f"Columns: {cols}")

if "cluster" in cols:
    group_cols = "cluster, plataforma"
elif "cluster_id" in cols:
    group_cols = "cluster_id, plataforma"
else:
    group_cols = "plataforma"

cur.execute(f"SELECT {group_cols}, COUNT(*) AS cnt FROM item_embeddings GROUP BY {group_cols} ORDER BY cnt DESC")
print(f"\nCount per {group_cols}:")
for r in cur.fetchall():
    print(dict(r))

# Also show total count
cur.execute("SELECT COUNT(*) FROM item_embeddings")
p("\nTotal rows in item_embeddings", cur.fetchone()[0])

conn.close()
