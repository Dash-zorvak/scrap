"""Re-puebla fb_comments.sentiment / sentiment_score usando pysentimiento (BERT español).
Uso: python scripts/repoblar_sentiment_comentarios.py"""
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import src.analyzer.sentiment as s
from src.analyzer.sentiment import SentimentAnalyzer

DB = ROOT / "data" / "facebook.db"
BATCH = 200


def main():
    if hasattr(s, "_init_pysentimiento"):
        s._init_pysentimiento()
    activo = getattr(s, "HAS_PYSENTIMIENTO", False)
    print(f"pysentimiento activo: {activo}")
    if not activo:
        print("ABORTADO: pysentimiento no se activó. No se escriben labels rule-based en 5,336 filas.")
        print("Revisá que el modelo BERT cargue (Issue 5) antes de re-poblar.")
        sys.exit(1)

    an = SentimentAnalyzer()
    lbl, sc = an.analyze("Esta alcaldía es una vergüenza, pésimo servicio y pura corrupción")
    print(f"smoke test → {lbl} ({sc:.2f})  [debería ser negativo/muy_negativo]")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT comment_id, message FROM fb_comments "
        "WHERE message IS NOT NULL AND TRIM(message) <> ''"
    ).fetchall()
    print(f"comentarios a analizar: {len(rows)}")

    t0 = time.time()
    n = 0
    for i, (cid, msg) in enumerate(rows, 1):
        try:
            label, score = an.analyze(msg)
        except Exception:
            label, score = "neutral", 0.0
        cur.execute(
            "UPDATE fb_comments SET sentiment = ?, sentiment_score = ? WHERE comment_id = ?",
            (label, float(score), cid),
        )
        n += 1
        if i % BATCH == 0:
            conn.commit()
            print(f"  {i}/{len(rows)} ({time.time()-t0:.0f}s)")

    conn.commit()
    dist = cur.execute(
        "SELECT sentiment, COUNT(*) FROM fb_comments WHERE sentiment IS NOT NULL "
        "GROUP BY sentiment ORDER BY 2 DESC"
    ).fetchall()
    conn.close()
    print(f"LISTO: {n} comentarios actualizados en {time.time()-t0:.0f}s")
    print("Distribución:", dist)


if __name__ == "__main__":
    main()
