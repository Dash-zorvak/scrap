"""Clean simulated data from externos.db.

Safe cleanup with backup, dry-run, and confirmation prompts.
Idempotent.

Usage:
    python scripts/clean_simulated.py              # backup + confirm + execute
    python scripts/clean_simulated.py --dry-run     # preview only, no changes
    python scripts/clean_simulated.py --yes         # skip confirmation
    python scripts/clean_simulated.py --no-backup   # skip backup
    python scripts/clean_simulated.py --dry-run --no-backup
"""
import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

EXTERNAL_DB = Path(__file__).resolve().parent.parent / "data" / "externos.db"
BACKUP_DIR = Path(__file__).resolve().parent.parent / "data"


def backup_db() -> Path:
    """Copy externos.db to data/externos.backup_TIMESTAMP.db."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"externos.backup_{ts}.db"
    shutil.copy2(str(EXTERNAL_DB), str(backup_path))
    print(f"  Backup created: {backup_path}")
    return backup_path


def clean(dry_run: bool = False, skip_backup: bool = False, skip_confirm: bool = False):
    if not EXTERNAL_DB.exists():
        print(f"Database not found: {EXTERNAL_DB}")
        return

    conn = sqlite3.connect(str(EXTERNAL_DB))
    cur = conn.cursor()

    # Count rows to be affected
    total_posts = cur.execute("SELECT COUNT(*) FROM external_posts").fetchone()[0]
    total_comments = cur.execute("SELECT COUNT(*) FROM external_comments").fetchone()[0]
    sim_posts = cur.execute(
        "SELECT COUNT(*) FROM external_posts WHERE post_id LIKE 'SIM_EXT%'"
    ).fetchone()[0]
    sim_comments = cur.execute(
        "SELECT COUNT(*) FROM external_comments WHERE post_id LIKE 'SIM_EXT%'"
    ).fetchone()[0]
    real_posts_pre = total_posts - sim_posts
    has_sentimiento = cur.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='external_sentimiento'"
    ).fetchone()[0] > 0
    sent_rows = 0
    if has_sentimiento:
        sent_rows = cur.execute("SELECT COUNT(*) FROM external_sentimiento").fetchone()[0]

    conn.close()

    print(f"Externos DB:   {EXTERNAL_DB}")
    print(f"  SIM_EXT posts:              {sim_posts}")
    print(f"  SIM_EXT comments:           {sim_comments}")
    print(f"  external_sentimiento rows:  {sent_rows}")
    print(f"  external_sentimiento table: {'exists' if has_sentimiento else 'does not exist'}")

    if sim_posts == 0 and sim_comments == 0 and sent_rows == 0:
        print("  Nothing to clean. DB is already clean.")
        return

    if dry_run:
        print(f"\nMode: DRY RUN — no changes made.")
        print(f"Would delete {sim_posts} posts, {sim_comments} comments, "
              f"{'drop external_sentimiento table' if has_sentimiento else 'no table to drop'}.")
        return

    # Backup
    if not skip_backup:
        backup_path = backup_db()
    else:
        backup_path = None
        print("  Backup skipped (--no-backup)")

    # Confirmation
    if not skip_confirm:
        print()
        answer = input("  Delete all simulated data and drop external_sentimiento? [y/N] ").strip().lower()
        if answer != "y":
            print("  Aborted.")
            return

    # Execute
    conn = sqlite3.connect(str(EXTERNAL_DB))
    cur = conn.cursor()

    cur.execute("DELETE FROM external_comments WHERE post_id LIKE 'SIM_EXT%'")
    deleted_comments = cur.rowcount
    cur.execute("DELETE FROM external_posts WHERE post_id LIKE 'SIM_EXT%'")
    deleted_posts = cur.rowcount

    # Defensive: verify no real posts were harmed
    remaining_real = cur.execute(
        "SELECT COUNT(*) FROM external_posts WHERE post_id NOT LIKE 'SIM_EXT%'"
    ).fetchone()[0]
    if remaining_real != real_posts_pre:
        conn.rollback()
        conn.close()
        print(f"\n  ❌ CRITICAL: Real posts changed from {real_posts_pre} to {remaining_real}!")
        print(f"  Rolling back — no changes applied.")
        print(f"  This should never happen. The DELETE filter may be wrong.")
        return

    if has_sentimiento:
        cur.execute("DROP TABLE IF EXISTS external_sentimiento")
        print(f"  Dropped external_sentimiento table ({sent_rows} rows)")

    conn.commit()
    conn.close()

    print(f"  Done: removed {deleted_posts} simulated posts, {deleted_comments} comments")
    if remaining_real > 0:
        print(f"  Real posts preserved: {remaining_real}")
    if backup_path:
        print(f"  Backup: {backup_path}")
    print("  externos.db now contains only real deep-scraper data.")


def main():
    parser = argparse.ArgumentParser(description="Clean simulated data from externos.db")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without executing")
    parser.add_argument("--no-backup", action="store_true", help="Skip automatic DB backup")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    clean(
        dry_run=args.dry_run,
        skip_backup=args.no_backup,
        skip_confirm=args.yes,
    )


if __name__ == "__main__":
    main()
