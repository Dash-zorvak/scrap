#!/usr/bin/env python3
"""Verificacion del pipeline de analisis.

Lee data/analysis.json, lo valida con schema_validator y muestra un reporte
de errores/advertencias.  Se puede ejecutar como standalone script o importar
como modulo.

Uso:
    python scripts/verificar.py
    python scripts/verificar.py --path data/analysis.json
"""
import argparse
import json
import sys
import os

# Allow running from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from analytics.schema_validator import validar


def verificar(path="data/analysis.json"):
    """Valida un archivo analysis.json y retorna el resultado."""
    if not os.path.exists(path):
        print(f"ERROR: Archivo no encontrado: {path}")
        return None

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    resultado = validar(data)

    if resultado.es_publicable:
        print(f"OK: {path} es publicable ({len(resultado.errores)} advertencias)")
    else:
        bloq = resultado.bloqueantes()
        print(f"FALLO: {len(bloq)} error(es) bloqueante(s):")
        for e in bloq:
            print(f"  [{e.codigo}] {e.seccion}: {e.mensaje_humano}")

    advs = resultado.advertencias()
    if advs:
        print(f"ADVERTENCIAS ({len(advs)}):")
        for e in advs:
            print(f"  [{e.codigo}] {e.seccion}: {e.mensaje_humano}")

    return resultado


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Valida analysis.json")
    parser.add_argument("--path", default="data/analysis.json")
    args = parser.parse_args()
    result = verificar(args.path)
    if result and not result.es_publicable:
        sys.exit(1)
