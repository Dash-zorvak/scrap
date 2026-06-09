"""Collapse existing duplicate posts in externos.db.

Deduplicates by post_url: finds groups with the same canonical URL,
keeps the best row (non-null created_time, most reactions, best data),
reassigns comments from duplicate rows, and removes the extras.

Handles artificial post_ids from old dup_counter bug (e.g. pfbid_2).

Usage:
    python scripts/dedupe_existing.py              # backup + confirm + execute
    python scripts/dedupe_existing.py --dry-run     # preview only
    python scripts/dedupe_existing.py --yes         # skip confirmation
    python scripts/dedupe_existing.py --no-backup   # skip backup
"""
import argparse
import os
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

EXTERNAL_DB = Path(os.getenv("EXTERNAL_DB",
    str(Path(__file__).resolve().parent.parent / "data" / "externos.db")))
BACKUP_DIR = Path(__file__).resolve().parent.parent / "data"


def has_artificial_suffix(pid: str) -> bool:
    """Detect artificial post_id suffixes like _1, _2 added by old dup_counter bug."""
    return bool(re.search(r'_\d+$', pid))


def canonical_post_id(pid: str) -> str:
    """Strip artificial suffix. E.g. 'pfbidABC_2' -> 'pfbidABC'."""
    return re.sub(r'_\d+$', '', pid)


def backup_db() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"externos.backup_{ts}.db"
    shutil.copy2(str(EXTERNAL_DB), str(backup_path))
    print(f"  Backup created: {backup_path}")
    return backup_path


def find_duplicate_groups(cur) -> list:
    """Return list of (post_url, [row_dict, ...]) for groups with >1 row."""
    groups = cur.execute("""
        SELECT post_url
        FROM external_posts
        WHERE post_url IS NOT NULL AND post_url != ''
        GROUP BY post_url
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC
    """).fetchall()

    result = []
    for (url,) in groups:
        rows = cur.execute("""
            SELECT rowid, post_id, created_time, total_reactions, comments_count, message, page_name
            FROM external_posts
            WHERE post_url = ?
            ORDER BY
                (CASE WHEN created_time IS NOT NULL THEN 0 ELSE 1 END),
                total_reactions DESC,
                LENGTH(message) DESC
        """, (url,)).fetchall()

        parsed = []
        for r in rows:
            parsed.append({
                "rowid": r[0],
                "post_id": r[1],
                "created_time": r[2],
                "total_reactions": r[3] or 0,
                "comments_count": r[4] or 0,
                "message": r[5] or "",
                "page_name": r[6] or "",
                "has_suffix": has_artificial_suffix(r[1]),
            })
        result.append((url, parsed))

    return result


def count_artificial_singletons(cur) -> int:
    """Count non-SIM rows with artificial _1/_2 suffix that are singletons."""
    return cur.execute(
        "SELECT COUNT(*) FROM external_posts WHERE post_id NOT LIKE 'SIM_EXT%' AND (post_id LIKE '%_1' OR post_id LIKE '%_2' OR post_id LIKE '%_3' OR post_id LIKE '%_4' OR post_id LIKE '%_5')"
    ).fetchone()[0]


def dedupe(dry_run: bool = False, skip_backup: bool = False, skip_confirm: bool = False):
    if not EXTERNAL_DB.exists():
        print(f"Database not found: {EXTERNAL_DB}")
        return

    conn = sqlite3.connect(str(EXTERNAL_DB))
    cur = conn.cursor()

    groups = find_duplicate_groups(cur)
    total_groups = len(groups)
    total_extra_rows = sum(len(g[1]) - 1 for g in groups)
    artificial_singletons = count_artificial_singletons(cur)

    print(f"Externos DB: {EXTERNAL_DB}")
    print(f"  Duplicate groups:  {total_groups} ({total_extra_rows} extra rows to remove)")
    print(f"  Artificial suffix singletons: {artificial_singletons}")
    print()

    if total_groups == 0 and artificial_singletons == 0:
        print("  Nothing to fix. DB is clean.")
        conn.close()
        return

    # Show detail for each group
    for url, rows in groups[:5]:
        print(f"  URL: {url[:70]}")
        for r in rows:
            flag = " ARTIFICIAL" if r["has_suffix"] else " KEEP(candidate)"
            print(f"    rowid={r['rowid']:>5}  post_id={r['post_id'][:40]:<40}"
                  f"  created={str(r['created_time'])[:20]:<20}"
                  f"  reactions={r['total_reactions']:>4}{flag}")
        if len(rows) > 2:
            print(f"    ... {len(rows)-2} more rows")
        print()

    if total_groups > 5:
        print(f"  ... and {total_groups - 5} more groups")
        print()

    if artificial_singletons > 0:
        print(f"  Will normalize {artificial_singletons} singletons with artificial _1/_2 suffix")
        print()

    if dry_run:
        print(f"Mode: DRY RUN — no changes.")
        if total_groups > 0:
            print(f"Would remove {total_extra_rows} extra rows, keep {len(groups)} canonical rows.")
        if artificial_singletons > 0:
            print(f"Would normalize {artificial_singletons} post_id(s).")
        conn.close()
        return

    # Backup
    if not skip_backup:
        backup_path = backup_db()
    else:
        backup_path = None
        print("  Backup skipped (--no-backup)")

    # Confirmation
    if not skip_confirm:
        msg = []
        if total_extra_rows > 0:
            msg.append(f"remove {total_extra_rows} duplicate rows")
        if artificial_singletons > 0:
            msg.append(f"normalize {artificial_singletons} post_id suffixes")
        question = f"  {' and '.join(msg)}? [y/N] "
        answer = input(question).strip().lower()
        if answer != "y":
            print("  Aborted.")
            conn.close()
            return

    # Execute collapse
    removed = 0
    comments_reassigned = 0

    for url, rows in groups:
        keep = rows[0]
        to_remove = rows[1:]
        canon_id = canonical_post_id(keep["post_id"])

        for dup in to_remove:
            dup_id = dup["post_id"]
            reassigned = cur.execute(
                "UPDATE external_comments SET post_id = ? WHERE post_id = ?",
                (canon_id, dup_id)
            ).rowcount
            comments_reassigned += reassigned
            cur.execute("DELETE FROM external_posts WHERE rowid = ?", (dup["rowid"],))
            removed += 1
            if keep["post_id"] != canon_id:
                cur.execute(
                    "UPDATE external_posts SET post_id = ? WHERE rowid = ?",
                    (canon_id, keep["rowid"])
                )

    # Normalize artificial suffixes on singleton rows
    normalized_singletons = 0
    if artificial_singletons > 0:
        rows_to_fix = cur.execute(
            "SELECT rowid, post_id FROM external_posts WHERE post_id NOT LIKE 'SIM_EXT%' AND (post_id LIKE '%_1' OR post_id LIKE '%_2' OR post_id LIKE '%_3' OR post_id LIKE '%_4' OR post_id LIKE '%_5')"
        ).fetchall()
        for rowid, pid in rows_to_fix:
            if has_artificial_suffix(pid):
                canon = canonical_post_id(pid)
                # If canonical ID already exists, reassign comments + delete suffix row
                existing = cur.execute(
                    "SELECT rowid FROM external_posts WHERE post_id = ? AND rowid != ?",
                    (canon, rowid)
                ).fetchone()
                if existing:
                    reassigned = cur.execute(
                        "UPDATE external_comments SET post_id = ? WHERE post_id = ?",
                        (canon, pid)
                    ).rowcount
                    comments_reassigned += reassigned
                    cur.execute("DELETE FROM external_posts WHERE rowid = ?", (rowid,))
                    removed += 1
                else:
                    cur.execute(
                        "UPDATE external_posts SET post_id = ? WHERE rowid = ?",
                        (canon, rowid)
                    )
                    normalized_singletons += 1

    conn.commit()
    conn.close()

    print(f"  Removed {removed} duplicate rows")
    print(f"  Reassigned {comments_reassigned} comments to canonical posts")
    print(f"  Normalized {normalized_singletons} post_id(s) (removed artificial _N suffix)")
    if backup_path:
        print(f"  Backup: {backup_path}")


def main():
    parser = argparse.ArgumentParser(description="Collapse duplicate posts in externos.db")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without executing")
    parser.add_argument("--no-backup", action="store_true", help="Skip automatic DB backup")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    dedupe(
        dry_run=args.dry_run,
        skip_backup=args.no_backup,
        skip_confirm=args.yes,
    )


if __name__ == "__main__":
    main()
