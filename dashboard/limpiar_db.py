"""Limpia las bases de datos del proyecto para hacer pruebas en limpio.

Borra los archivos data/facebook.db, data/tiktok.db y data/externos.db.
Se recrean vacíos automáticamente al subir el siguiente lote desde el dashboard
(LocalStorage crea el esquema de Facebook, escritura_tiktok crea el de TikTok y
el pipeline recrea las tablas de engagement/sentimiento/categorías).

Uso:
    python dashboard/limpiar_db.py            # pide confirmación
    python dashboard/limpiar_db.py --force    # sin confirmación
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    FACEBOOK_DB,
    TIKTOK_DB,
    EXTERNOS_DB,
)


def limpiar():
    objetivos = [FACEBOOK_DB, TIKTOK_DB, EXTERNOS_DB]

    for db in objetivos:
        if os.path.exists(db):
            os.remove(db)
            print(f"\\U0001f5d1\\ufe0f  Eliminado: {db}")
        else:
            print(f"\\u2014 No existía (ok): {db}")

    print("\\u2705 Bases limpias. Se recrearán vacías al subir el próximo lote.")


if __name__ == "__main__":
    force = "--force" in sys.argv or "-f" in sys.argv

    if not force:
        resp = input("\\u26a0\\ufe0f  Esto BORRAR\\u00c1 las bases de datos. \\u00bfContinuar? (escribe 'si'): ")
        if resp.strip().lower() not in ("si", "s\\u00ed", "s", "yes", "y"):
            print("Cancelado.")
            sys.exit(0)

    limpiar()
