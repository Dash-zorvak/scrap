#!/usr/bin/env python3
"""
CLI para el scraper de TikTok V2.
Ejecuta las 3 fases de forma independiente o secuencial.

Uso:
    python run.py --phase all          # Todo en secuencia
    python run.py --phase 1            # Solo videos
    python run.py --phase 2            # Solo comentarios
    python run.py --phase 3            # Solo hilos
    python run.py --status             # Ver estadísticas
    python run.py --accounts alcaldiasa acevedogustavo_  # cuentas específicas
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime

from src.tiktok_scraper.db_local import LocalDB
from src.tiktok_scraper.scraper_v2 import TikTokScraperV2

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────

DEFAULT_ACCOUNTS = [
    "alcaldiasa",
    "acevedogustavo_",
]

DEFAULT_DB_URL = os.getenv(
    "TIKTOK_DB_URL",
    "postgresql://localhost/tiktok_scraper"
)

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"


def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"scraper_{datetime.now().strftime('%Y%m%d')}.log"),
        ]
    )


# ─────────────────────────────────────────────
# COMANDOS
# ─────────────────────────────────────────────

def cmd_status(db: LocalDB):
    """Muestra estadísticas actuales de la base de datos."""
    stats = db.get_stats()

    print("\n" + "═" * 55)
    print("  ESTADÍSTICAS DEL SCRAPER")
    print("═" * 55)
    print(f"  📹 Videos totales       : {stats['total_videos']:>10,}")
    print(f"  💬 Comentarios raíz     : {stats['total_comments']:>10,}")
    print(f"  🔁 Replies              : {stats['total_replies']:>10,}")
    print(f"  📊 Total comentarios    : {stats['total_comments'] + stats['total_replies']:>10,}")
    print("─" * 55)
    for account, count in stats["by_account"].items():
        print(f"  @{account:<25}: {count:>10,} videos")
    print("═" * 55 + "\n")

    # Checkpoints
    print("  CHECKPOINTS:")
    for account in DEFAULT_ACCOUNTS:
        print(f"\n  @{account}")
        for phase in ["videos", "comments", "replies"]:
            ckpt = db.get_checkpoint(account, phase)
            if ckpt:
                status = "✅ completo" if ckpt["completed"] else f"⏳ en progreso ({ckpt['items_done']})"
                print(f"    Fase {phase:<10}: {status}")
            else:
                print(f"    Fase {phase:<10}: 🔘 no iniciado")
    print()


def run_phase(phase: str, accounts: list, db: LocalDB):
    """Ejecuta una fase para todas las cuentas."""
    total_start = time.time()

    for account in accounts:
        print(f"\n{'─'*55}")
        print(f"  Procesando @{account}  —  Fase {phase}")
        print(f"{'─'*55}")

        scraper = TikTokScraperV2(db)

        try:
            if phase in ("1", "all"):
                n = scraper.run_phase1_videos(account)
                print(f"  ✅ Fase 1: {n:,} videos guardados")

            if phase in ("2", "all"):
                n = scraper.run_phase2_comments(account)
                print(f"  ✅ Fase 2: {n:,} comentarios guardados")

            if phase in ("3", "all"):
                n = scraper.run_phase3_replies(account)
                print(f"  ✅ Fase 3: {n:,} replies guardados")

        except KeyboardInterrupt:
            print("\n  ⚠️  Interrumpido por usuario. Checkpoint guardado.")
            break
        except Exception as e:
            logging.getLogger(__name__).error(f"Error en @{account}: {e}", exc_info=True)
            print(f"  ❌ Error en @{account}: {e}")
            continue

    elapsed = (time.time() - total_start) / 60
    print(f"\n  Tiempo total: {elapsed:.1f} min\n")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="TikTok Scraper V2 — Sin browser, con checkpoints"
    )
    parser.add_argument(
        "--phase",
        choices=["1", "2", "3", "all"],
        help="Fase a ejecutar (1=videos, 2=comentarios, 3=replies, all=todo)"
    )
    parser.add_argument(
        "--accounts",
        nargs="+",
        default=DEFAULT_ACCOUNTS,
        help="Usernames de TikTok a scrapear"
    )
    parser.add_argument(
        "--db-url",
        default=DEFAULT_DB_URL,
        help="URL de conexión a PostgreSQL"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Mostrar estadísticas y salir"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )

    args = parser.parse_args()
    setup_logging(args.log_level)

    print(f"\n{'═'*55}")
    print("  TIKTOK SCRAPER V2 — Iniciando")
    print(f"  Fecha : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Cuentas: {', '.join('@' + a for a in args.accounts)}")
    print(f"{'═'*55}\n")

    # Conectar a BD
    try:
        db = LocalDB(args.db_url)
        print("  ✅ Base de datos conectada\n")
    except Exception as e:
        print(f"  ❌ Error conectando a BD: {e}")
        print("\n  Asegúrate de que PostgreSQL esté corriendo y la BD exista:")
        print("  createdb tiktok_scraper\n")
        sys.exit(1)

    if args.status:
        cmd_status(db)
        return

    if not args.phase:
        parser.print_help()
        print("\n  Ejemplo: python run.py --phase all")
        return

    run_phase(args.phase, args.accounts, db)
    cmd_status(db)


if __name__ == "__main__":
    main()