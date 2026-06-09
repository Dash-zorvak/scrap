"""Verify database integrity for externos.db and facebook.db.

Usage:
    python scripts/verify_db.py                         # both DBs
    python scripts/verify_db.py --db externos           # only externos.db
    python scripts/verify_db.py --db facebook           # only facebook.db
"""
import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

DB_PATHS = {
    "externos": DATA / "externos.db",
    "facebook": DATA / "facebook.db",
}


def fmt(val):
    return str(val) if val is not None else "NULL"


def verify_db(label: str, db_path: Path):
    print(f"\n{'='*60}")
    print(f"  {label}: {db_path}")
    print(f"{'='*60}")

    if not db_path.exists():
        print(f"  FILE NOT FOUND")
        return

    size = db_path.stat().st_size
    print(f"  Size: {size:,} bytes ({size/1024:.0f} KB)")

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # List tables
    tables = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    table_names = [t[0] for t in tables]
    print(f"  Tables: {', '.join(table_names) if table_names else 'NONE'}")

    for tbl in table_names:
        print(f"\n  --- {tbl} ---")

        # Row count
        count = cur.execute(f"SELECT COUNT(*) FROM \"{tbl}\"").fetchone()[0]
        print(f"    Rows: {count}")

        if count == 0:
            continue

        # Columns & null analysis
        col_info = cur.execute(f"PRAGMA table_info(\"{tbl}\")").fetchall()
        col_names = [c[1] for c in col_info]

        print(f"    Columns ({len(col_names)}): {', '.join(col_names)}")
        print(f"    NULL counts:")

        nulls = []
        for c in col_names:
            null_count = cur.execute(
                f"SELECT COUNT(*) FROM \"{tbl}\" WHERE \"{c}\" IS NULL"
            ).fetchone()[0]
            if null_count > 0:
                pct = null_count / count * 100
                nulls.append(f"      {c}: {null_count}/{count} ({pct:.1f}%)")

        if nulls:
            print("\n".join(nulls))
        else:
            print("      (none)")

        # Duplicates by post_url if column exists
        if "post_url" in col_names:
            dupes = cur.execute(f"""
                SELECT post_url, COUNT(*) as cnt FROM \"{tbl}\"
                WHERE post_url IS NOT NULL AND post_url != ''
                GROUP BY post_url HAVING cnt > 1
                ORDER BY cnt DESC LIMIT 5
            """).fetchall()
            if dupes:
                print(f"    Duplicate post_url (top 5):")
                for url, cnt in dupes:
                    print(f"      {cnt}x: {url[:80]}")
            else:
                print(f"    No duplicate post_url")

        # Duplicate post_id
        if "post_id" in col_names:
            dupes = cur.execute(f"""
                SELECT post_id, COUNT(*) as cnt FROM \"{tbl}\"
                GROUP BY post_id HAVING cnt > 1
                ORDER BY cnt DESC LIMIT 5
            """).fetchall()
            if dupes:
                print(f"    Duplicate post_id (WARNING!):")
                for pid, cnt in dupes:
                    print(f"      {cnt}x: {pid[:60]}")

        # Date range
        for date_col in ["created_time", "scraped_at"]:
            if date_col in col_names:
                range_row = cur.execute(
                    f"SELECT MIN({date_col}), MAX({date_col}) FROM \"{tbl}\""
                ).fetchone()
                if range_row and range_row[0]:
                    print(f"    {date_col} range: {fmt(range_row[0])} → {fmt(range_row[1])}")

        # Out-of-range posts (before SCRAPE_SINCE)
        if "created_time" in col_names:
            before = cur.execute(f"""
                SELECT COUNT(*) FROM \"{tbl}\"
                WHERE created_time IS NOT NULL
                AND created_time < '2025-01-01'
            """).fetchone()[0]
            if before > 0:
                print(f"    ⚠ Posts before 2025-01-01: {before}")
            else:
                print(f"    No posts before 2025-01-01 ✓")

        # SIM_EXT rows
        if "post_id" in col_names:
            sim = cur.execute(
                f"SELECT COUNT(*) FROM \"{tbl}\" WHERE post_id LIKE 'SIM_EXT%'"
            ).fetchone()[0]
            if sim > 0:
                print(f"    ⚠ SIM_EXT (simulated) rows: {sim}")
            else:
                print(f"    No SIM_EXT rows ✓")

    # % posts with comments (for external_posts)
    if "external_posts" in table_names and "external_comments" in table_names:
        pc = cur.execute("""
            SELECT COUNT(DISTINCT post_id) FROM external_comments
        """).fetchone()[0]
        tp = cur.execute("SELECT COUNT(*) FROM external_posts").fetchone()[0]
        pct = pc / tp * 100 if tp > 0 else 0
        print(f"\n    Posts with comments: {pc}/{tp} ({pct:.1f}%)")

    # external_sentimiento check
    if "external_sentimiento" in table_names:
        sent_count = cur.execute("SELECT COUNT(*) FROM external_sentimiento").fetchone()[0]
        print(f"\n    ⚠ external_sentimiento still exists: {sent_count} rows (simulated data)")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Verify database integrity")
    parser.add_argument("--db", choices=["externos", "facebook"], help="Which DB to verify (default: both)")
    args = parser.parse_args()

    if args.db:
        verify_db(args.db, DB_PATHS[args.db])
    else:
        for name, path in DB_PATHS.items():
            verify_db(name, path)

    print(f"\n{'='*60}")
    print("  Done.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
