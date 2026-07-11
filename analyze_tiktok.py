import sqlite3

DB = "/Users/new/Desktop/scrap-main/data/tiktok.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row  # so we can iterate over rows as dict-like
c = conn.cursor()

def fmt(row, cols):
    return " | ".join(str(row[c]) if row[c] is not None else "NULL" for c in cols)

print("=" * 120)
print("1. BASIC COUNTS")
print("=" * 120)
total_videos = c.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
total_comments = c.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
min_c, max_c = c.execute("SELECT MIN(created_at), MAX(created_at) FROM videos").fetchone()
print(f"  Total videos:   {total_videos}")
print(f"  Total comments: {total_comments}")
print(f"  Date range:     {min_c}  →  {max_c}")

print()
print("=" * 120)
print("2. VIDEO METRICS (sums across all videos)")
print("=" * 120)
row = c.execute("""
    SELECT COALESCE(SUM(views),0),
           COALESCE(SUM(likes),0),
           COALESCE(SUM(shares),0),
           COALESCE(SUM(favorites_count),0),
           COALESCE(SUM(comments_count),0)
    FROM videos
""").fetchone()
print(f"  Total views:           {row[0]:,}")
print(f"  Total likes:           {row[1]:,}")
print(f"  Total shares:          {row[2]:,}")
print(f"  Total favorites_count: {row[3]:,}")
print(f"  Total comments_count:  {row[4]:,}")

print()
print("=" * 120)
print("3. PER-ACCOUNT BREAKDOWN")
print("=" * 120)
rows = c.execute("""
    SELECT account_id,
           COUNT(*)        AS cnt,
           COALESCE(SUM(views),0),
           COALESCE(SUM(likes),0),
           COALESCE(SUM(shares),0),
           COALESCE(SUM(comments_count),0),
           COALESCE(SUM(favorites_count),0)
    FROM videos
    GROUP BY account_id
    ORDER BY account_id
""").fetchall()
cols = ["account_id","cnt","SUM(views)","SUM(likes)","SUM(shares)","SUM(comments_count)","SUM(favorites_count)"]
print("  " + "  |  ".join(cols))
print("  " + "-" * len("  ".join(cols)))
for r in rows:
    vals = [str(r[0] if r[0] is not None else "NULL"),
            str(r[1]),
            f"{r[2]:,}", f"{r[3]:,}", f"{r[4]:,}", f"{r[5]:,}", f"{r[6]:,}"]
    print("  " + "  |  ".join(vals))

print()
print("=" * 120)
print("4. COMMENTS TABLE")
print("=" * 120)
print("  4a. All comment rows (video_id, text, likes, created_at, replies_count)")
rows = c.execute("SELECT video_id, text, likes, created_at, replies_count FROM comments ORDER BY video_id, created_at").fetchall()
hdr = ["video_id", "text", "likes", "created_at", "replies_count"]
print("  " + "  |  ".join(hdr))
print("  " + "-" * len("  ".join(hdr)))
for r in rows:
    d = dict(r)
    text = d["text"].replace("\n", "\\n") if d["text"] else "NULL"
    if len(text) > 120:
        text = text[:120] + "..."
    vals = [str(d["video_id"]), text, str(d["likes"]), str(d["created_at"]), str(d["replies_count"])]
    print("  " + "  |  ".join(vals))
print(f"  [Total comment rows: {len(rows)}]")

print()
print("  4b. Count of comments per video_id")
rows = c.execute("SELECT video_id, COUNT(*) AS cnt FROM comments GROUP BY video_id ORDER BY cnt DESC").fetchall()
print("  video_id  |  comment_count")
print("  " + "-" * 30)
for r in rows:
    print(f"  {r['video_id']}  |  {r['cnt']}")

print()
print("=" * 120)
print("5. TIKTOK_ENGAGEMENT — ALL ROWS")
print("=" * 120)
c2 = conn.cursor()
c2.execute("SELECT * FROM tiktok_engagement")
eng_cols = [d[0] for d in c2.description]
print("  Columns: " + ", ".join(eng_cols))
rows = c2.fetchall()
for r in rows:
    print("  " + "  |  ".join(str(r[i] if r[i] is not None else "NULL") for i in range(len(eng_cols))))
print(f"  [Total engagement rows: {len(rows)}]")

print()
print("=" * 120)
print("6. TIKTOK_SENTIMIENTO — ALL ROWS")
print("=" * 120)
c3 = conn.cursor()
c3.execute("SELECT * FROM tiktok_sentimiento")
sent_cols = [d[0] for d in c3.description]
print("  Columns: " + ", ".join(sent_cols))
rows = c3.fetchall()
for r in rows:
    print("  " + "  |  ".join(str(r[i] if r[i] is not None else "NULL") for i in range(len(sent_cols))))
print(f"  [Total sentimiento rows: {len(rows)}]")

conn.close()
