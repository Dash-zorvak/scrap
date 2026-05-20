#!/usr/bin/env python3
"""
Test de validación antes de correr la Fase 1 completa.
Verifica: BD, conexión a TikTok, bootstrap de usuario.

Uso:
    python test_phase1.py
    python test_phase1.py --account acevedogustavo_
"""
import argparse
import json
import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ── Colores para terminal ──────────────────────
OK   = "\033[92m✅\033[0m"
FAIL = "\033[91m❌\033[0m"
WARN = "\033[93m⚠️\033[0m"
INFO = "\033[94mℹ️\033[0m"


def check_dependencies() -> bool:
    print("\n── 1. Dependencias de Python ──────────────")
    ok = True
    for pkg in ["requests", "sqlalchemy", "psycopg2"]:
        try:
            __import__(pkg)
            print(f"  {OK}  {pkg}")
        except ImportError:
            print(f"  {FAIL}  {pkg}  →  pip install {pkg}")
            ok = False
    return ok


def check_database(db_url: str) -> bool:
    print("\n── 2. Conexión a PostgreSQL ────────────────")
    try:
        from src.tiktok_scraper.db_local import LocalDB
        db = LocalDB(db_url)
        stats = db.get_stats()
        print(f"  {OK}  Conectado: {db_url}")
        print(f"  {INFO}  Videos actuales : {stats['total_videos']:,}")
        print(f"  {INFO}  Comentarios     : {stats['total_comments']:,}")
        return True
    except Exception as e:
        print(f"  {FAIL}  No se pudo conectar: {e}")
        print(f"\n  Para crear la base de datos ejecuta:")
        print(f"  createdb tiktok_scraper")
        return False


def check_tiktok_connection() -> bool:
    print("\n── 3. Conectividad con TikTok ──────────────")
    try:
        import requests
        resp = requests.get(
            "https://www.tiktok.com",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0"},
            timeout=10
        )
        if resp.status_code == 200:
            print(f"  {OK}  TikTok accesible (HTTP {resp.status_code})")
            return True
        else:
            print(f"  {WARN}  TikTok respondió HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"  {FAIL}  Sin conexión: {e}")
        return False


def check_bootstrap(account: str) -> bool:
    print(f"\n── 4. Bootstrap de @{account} ──────────────")
    try:
        from src.tiktok_scraper.db_local import LocalDB
        from src.tiktok_scraper.scraper_v2 import TikTokScraperV2

        db = LocalDB()
        scraper = TikTokScraperV2(db)

        print(f"  {INFO}  Cargando perfil de @{account}...")
        sec_uid = scraper.bootstrap_user(account)

        if sec_uid:
            print(f"  {OK}  secUid obtenido: {sec_uid[:30]}...")
            if scraper._ms_token:
                print(f"  {OK}  msToken obtenido: {scraper._ms_token[:20]}...")
            else:
                print(f"  {WARN}  msToken no obtenido (puede seguir funcionando)")
            return True, scraper, sec_uid
        else:
            print(f"  {FAIL}  No se pudo obtener secUid para @{account}")
            return False, None, None

    except Exception as e:
        print(f"  {FAIL}  Error en bootstrap: {e}")
        return False, None, None


def check_first_page(scraper, sec_uid: str, account: str) -> bool:
    print(f"\n── 5. Primera página de videos ─────────────")
    try:
        import requests as req
        time.sleep(2)

        data = scraper._get(
            "https://www.tiktok.com/api/post/item_list/",
            {
                "secUid": sec_uid,
                "count": "5",
                "cursor": "0",
                "aid": "1988",
                "app_name": "tiktok_web",
                "device_platform": "web_pc",
            }
        )

        if not data:
            print(f"  {FAIL}  No se obtuvo respuesta del API")
            return False

        videos = data.get("itemList", [])
        has_more = data.get("hasMore", False)

        if videos:
            print(f"  {OK}  {len(videos)} videos obtenidos en la primera página")
            print(f"  {INFO}  Hay más páginas: {has_more}")
            print(f"\n  Preview de los primeros videos:")
            for i, v in enumerate(videos[:3], 1):
                stats = v.get("stats", {})
                desc = (v.get("desc", "") or "")[:60]
                print(f"    {i}. [{v.get('id')}] {desc}")
                print(f"       👁 {stats.get('playCount',0):,}  ❤️ {stats.get('diggCount',0):,}  💬 {stats.get('commentCount',0):,}")
            return True
        else:
            print(f"  {WARN}  API respondió pero sin videos")
            print(f"  Respuesta: {json.dumps(data, indent=2)[:300]}")
            return False

    except Exception as e:
        print(f"  {FAIL}  Error obteniendo videos: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Validación pre-scraping Fase 1")
    parser.add_argument("--account", default="alcaldiasa")
    parser.add_argument(
        "--db-url",
        default="postgresql://localhost/tiktok_scraper"
    )
    args = parser.parse_args()

    print("=" * 50)
    print("  TEST DE VALIDACIÓN — FASE 1")
    print(f"  Cuenta: @{args.account}")
    print("=" * 50)

    results = {}

    results["deps"]   = check_dependencies()
    results["db"]     = check_database(args.db_url)
    results["tiktok"] = check_tiktok_connection()

    if not all([results["deps"], results["db"], results["tiktok"]]):
        print(f"\n{FAIL}  Hay problemas previos. Resuelve los {FAIL} antes de continuar.\n")
        sys.exit(1)

    bootstrap_ok, scraper, sec_uid = check_bootstrap(args.account)
    results["bootstrap"] = bootstrap_ok

    if bootstrap_ok:
        results["api"] = check_first_page(scraper, sec_uid, args.account)
    else:
        results["api"] = False

    # Resumen
    print("\n" + "=" * 50)
    print("  RESUMEN")
    print("=" * 50)
    all_ok = True
    checks = {
        "deps":      "Dependencias Python",
        "db":        "PostgreSQL",
        "tiktok":    "Conectividad TikTok",
        "bootstrap": f"Bootstrap @{args.account}",
        "api":       "Primera página de videos",
    }
    for key, label in checks.items():
        icon = OK if results.get(key) else FAIL
        print(f"  {icon}  {label}")
        if not results.get(key):
            all_ok = False

    print()
    if all_ok:
        print(f"  {OK}  Todo listo. Ejecuta la Fase 1 con:")
        print(f"\n      python run.py --phase 1\n")
    else:
        print(f"  {FAIL}  Hay checks fallidos. Resuelve antes de ejecutar.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()