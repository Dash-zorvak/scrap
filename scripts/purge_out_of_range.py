"""Purge posts with created_time < SCRAPE_SINCE from externos.db and facebook.db.

Safe: backup, dry-run, confirm, idempotent. NULL created_time are KEPT by default
(use --purge-null to also delete posts with NULL created_time).

Usage:
    python scripts/purge_out_of_range.py              # backup + confirm + execute
    python scripts/purge_out_of_range.py --dry-run     # preview only
    python scripts/purge_out_of_range.py --yes         # skip confirmation
    python scripts/purge_out_of_range.py --no-backup   # skip backup
    python scripts/purge_out_of_range.py --purge-null  # also delete NULL-date posts
"""
import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONFIG_PATH = ROOT / "src" / "config.py"


def get_scratch_since() -> str:
    """Load SCRAPE_SINCE from Config class default: 2025-01-01."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("config", CONFIG_PATH)
    if spec is None:
        return "2025-01-01"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod.Config, "SCRAPE_SINCE", "2025-01-01") or "2025-01-01"


DB_CONFIG: list[dict] = []


def _build_db_config(since: str):
    global DB_CONFIG
    DB_CONFIG = [
        {
            "label": "externos",
            "path": DATA / "externos.db",
            "posts_table": "external_posts",
            "comments_table": "external_comments",
            "extra_tables": ["external_sentimiento"],
            "post_id_col": "post_id",
            "date_col": "created_time",
        },
        {
            "label": "facebook",
            "path": DATA / "facebook.db",
            "posts_table": "fb_posts",
            "comments_table": "fb_comments",
            "extra_tables": ["fb_engagement", "fb_sentimiento", "post_categorias", "problematicas", "insights", "nlp_results"],
            "post_id_col": "post_id",
            "date_col": "created_time",
        },
    ]
    return DB_CONFIG


def fmt(n):
    return f"{n:,}"


def backup_db(path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{path.stem}.purge_backup_{ts}{path.suffix}"
    backup_path = path.parent / name
    shutil.copy2(str(path), str(backup_path))
    print(f"  Backup: {backup_path}")
    return backup_path


def count_out_of_range(cur, table: str, date_col: str, since: str, purge_null: bool) -> dict:
    """Return dict with total, oor (before since), null-count."""
    total = cur.execute(f"SELECT COUNT(*) FROM \"{table}\"").fetchone()[0]
    oor = cur.execute(
        f"SELECT COUNT(*) FROM \"{table}\" WHERE {date_col} IS NOT NULL AND {date_col} < ?",
        (since,),
    ).fetchone()[0]
    nulls = cur.execute(
        f"SELECT COUNT(*) FROM \"{table}\" WHERE {date_col} IS NULL"
    ).fetchone()[0]
    return {"total": total, "oor": oor, "nulls": nulls}


def delete_out_of_range(cur, table: str, date_col: str, since: str, purge_null: bool) -> int:
    """Delete out-of-range rows. Returns number deleted."""
    cond = f"{date_col} IS NOT NULL AND {date_col} < ?"
    params: list = [since]
    if purge_null:
        cond = f"({cond} OR {date_col} IS NULL)"
    cur.execute(f"DELETE FROM \"{table}\" WHERE {cond}", params)
    return cur.rowcount


def purge(dry_run: bool = False, skip_backup: bool = False, skip_confirm: bool = False, purge_null: bool = False):
    since = get_scratch_since()
    dbs = _build_db_config(since)

    print(f"SCRAPE_SINCE: {since}  (--purge-null: {purge_null})")
    print()

    # Phase 1: count (no modifications)
    counts: list[dict] = []
    for cfg in dbs:
        if not cfg["path"].exists():
            print(f"  {cfg['label']}: {cfg['path']} — NOT FOUND, skipping")
            continue

        conn = sqlite3.connect(str(cfg["path"]))
        cur = conn.cursor()

        entry = {"label": cfg["label"], "post_stats": {}, "comment_stats": {}, "extra_stats": {}}

        # Posts
        entry["post_stats"] = count_out_of_range(cur, cfg["posts_table"], cfg["date_col"], since, purge_null)

        # Comments
        if cfg["comments_table"]:
            entry["comment_stats"] = count_out_of_range(cur, cfg["comments_table"], cfg["date_col"], since, purge_null)

        # Extra tables (only count rows referencing out-of-range posts)
        extra = {}
        for tbl in cfg.get("extra_tables", []):
            exists = cur.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
                (tbl,),
            ).fetchone()[0]
            if not exists:
                continue
            has_pid = any(r[0] == "post_id" for r in cur.execute(f"PRAGMA table_info(\"{tbl}\")").fetchall())
            if not has_pid:
                continue
            cnt = cur.execute(
                f"SELECT COUNT(*) FROM \"{tbl}\" t "
                f"WHERE t.post_id IN (SELECT post_id FROM \"{cfg['posts_table']}\" "
                f"WHERE {cfg['date_col']} IS NOT NULL AND {cfg['date_col']} < ?)",
                (since,),
            ).fetchone()[0]
            extra[tbl] = cnt
        entry["extra_stats"] = extra

        conn.close()
        counts.append(entry)

    # Print report
    for entry in counts:
        lbl = entry["label"]
        ps = entry["post_stats"]
        cs = entry["comment_stats"]
        ex = entry["extra_stats"]

        print(f"  {lbl}: {cfg['path']}")
        print(f"    Posts: {fmt(ps['total'])} total, "
              f"{fmt(ps['oor'])} pre-{since} to delete, "
              f"{fmt(ps['nulls'])} with NULL date (KEPT{' unless --purge-null' if not purge_null else ''})")
        if cs:
            print(f"    Comments: {fmt(cs['total'])} total, {fmt(cs['oor'])} to delete")
        for tbl, cnt in ex.items():
            if cnt:
                print(f"    {tbl}: {fmt(cnt)} rows referencing out-of-range posts")
        print()

    if dry_run:
        print(f"Mode: DRY RUN — no changes made.")
        return

    # Phase 2: backup
    if not skip_backup:
        backup_paths = []
        for cfg in dbs:
            if cfg["path"].exists():
                backup_paths.append(backup_db(cfg["path"]))
        if backup_paths:
            print()
    else:
        print("  Backup skipped (--no-backup)\n")

    # Phase 3: confirmation
    if not skip_confirm:
        total_oor_posts = sum(e["post_stats"]["oor"] for e in counts)
        question = f"  Delete {fmt(total_oor_posts)} out-of-range posts across {len(counts)} DB(s)? [y/N] "
        answer = input(question).strip().lower()
        if answer != "y":
            print("  Aborted.")
            return

    # Phase 4: execute
    for entry in counts:
        cfg = next(c for c in dbs if c["label"] == entry["label"])
        if not cfg["path"].exists():
            continue

        conn = sqlite3.connect(str(cfg["path"]))
        cur = conn.cursor()

        # Delete comments referencing OOR posts
        if cfg["comments_table"]:
            pid_col = cfg["post_id_col"]
            subq = (
                f"SELECT {pid_col} FROM \"{cfg['posts_table']}\" "
                f"WHERE {cfg['date_col']} IS NOT NULL AND {cfg['date_col']} < ?"
            )
            params: list = [since]
            if purge_null:
                subq = (
                    f"SELECT {pid_col} FROM \"{cfg['posts_table']}\" "
                    f"WHERE ({cfg['date_col']} IS NOT NULL AND {cfg['date_col']} < ?) OR {cfg['date_col']} IS NULL"
                )
            cur.execute(
                f"DELETE FROM \"{cfg['comments_table']}\" WHERE {pid_col} IN ({subq})",
                params,
            )
            del_comments = cur.rowcount
            print(f"  {cfg['label']}: deleted {fmt(del_comments)} comments")

        # Delete extra table rows referencing OOR posts
        for tbl, cnt in entry["extra_stats"].items():
            if cnt == 0:
                continue
            cond = f"WHERE post_id IN (SELECT post_id FROM \"{cfg['posts_table']}\" WHERE {cfg['date_col']} IS NOT NULL AND {cfg['date_col']} < ?)"
            params = [since]
            if purge_null:
                cond = f"WHERE post_id IN (SELECT post_id FROM \"{cfg['posts_table']}\" WHERE ({cfg['date_col']} IS NOT NULL AND {cfg['date_col']} < ?) OR {cfg['date_col']} IS NULL)"
            cur.execute(f"DELETE FROM \"{tbl}\" {cond}", params)
            print(f"  {cfg['label']}: deleted {cur.rowcount} rows from {tbl}")

        # Delete OOR posts
        del_posts = delete_out_of_range(cur, cfg["posts_table"], cfg["date_col"], since, purge_null)
        print(f"  {cfg['label']}: deleted {fmt(del_posts)} posts")

        conn.commit()
        conn.close()

    print(f"\n  Done. Purged rows with created_time < {since}.")
    if not purge_null:
        print("  NULL-date rows preserved (use --purge-null to delete).")


def main():
    parser = argparse.ArgumentParser(description="Purge pre-SCRAPE_SINCE posts from databases")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without executing")
    parser.add_argument("--no-backup", action="store_true", help="Skip automatic DB backup")
    parser.add_argument("--purge-null", action="store_true", help="Also delete posts with NULL created_time")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    purge(
        dry_run=args.dry_run,
        skip_backup=args.no_backup,
        skip_confirm=args.yes,
        purge_null=args.purge_null,
    )


if __name__ == "__main__":
    main()
