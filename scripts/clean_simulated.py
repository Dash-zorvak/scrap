"""Clean simulated data from externos.db.

Idempotent. Use --dry-run to preview.

Usage:
    python scripts/clean_simulated.py          # execute
    python scripts/clean_simulated.py --dry-run  # preview only
"""
import argparse
import sqlite3
import sys
from pathlib import Path

EXTERNAL_DB = Path(__file__).resolve().parent.parent / "data" / "externos.db"


def clean(dry_run: bool = False):
    if not EXTERNAL_DB.exists():
        print(f"Database not found: {EXTERNAL_DB}")
        return

    conn = sqlite3.connect(str(EXTERNAL_DB))
    cur = conn.cursor()

    # Count rows to be affected
    sim_posts = cur.execute(
        "SELECT COUNT(*) FROM external_posts WHERE post_id LIKE 'SIM_EXT%'"
    ).fetchone()[0]
    sim_comments = cur.execute(
        "SELECT COUNT(*) FROM external_comments WHERE post_id LIKE 'SIM_EXT%'"
    ).fetchone()[0]
    has_sentimiento = cur.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='external_sentimiento'"
    ).fetchone()[0] > 0
    sent_rows = 0
    if has_sentimiento:
        sent_rows = cur.execute("SELECT COUNT(*) FROM external_sentimiento").fetchone()[0]

    print(f"externos.db: {EXTERNAL_DB}")
    print(f"  SIM_EXT posts:     {sim_posts}")
    print(f"  SIM_EXT comments:  {sim_comments}")
    print(f"  external_sentimiento rows: {sent_rows}")
    print(f"  Mode: {'DRY RUN (no changes)' if dry_run else 'EXECUTING'}")

    if dry_run:
        conn.close()
        return

    # Delete simulated posts and their comments
    cur.execute("DELETE FROM external_comments WHERE post_id LIKE 'SIM_EXT%'")
    cur.execute("DELETE FROM external_posts WHERE post_id LIKE 'SIM_EXT%'")

    # Drop external_sentimiento entirely (it's a simulated-only table)
    if has_sentimiento:
        cur.execute("DROP TABLE IF EXISTS external_sentimiento")

    conn.commit()
    conn.close()

    remaining_posts = sim_posts - sim_posts  # 0
    print(f"  Done: removed {sim_posts} simulated posts, {sim_comments} comments")
    if has_sentimiento:
        print(f"  Dropped external_sentimiento table ({sent_rows} rows)")
    else:
        print("  external_sentimiento did not exist")

    print("  externos.db now contains only real deep-scraper data.")


def main():
    parser = argparse.ArgumentParser(description="Clean simulated data from externos.db")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without executing")
    args = parser.parse_args()
    clean(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
