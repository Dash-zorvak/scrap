#!/usr/bin/env python3
"""CLI para el pipeline de analisis.

Permite ejecutar las operaciones del pipeline desde linea de comandos:
- generar: genera analysis.json desde las aprobaciones
- verificar: valida un analysis.json existente
- resumen: muestra estadisticas del estado actual

Uso:
    python -m analytics.cli generar --periodo 2026-04 --fecha-hasta 2026-04-30
    python -m analytics.cli verificar
    python -m analytics.cli resumen
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.config import Config
from analytics.report import construir_analysis, generar_reporte_completo
from analytics.publish import publicar_analysis
from analytics.schema_validator import validar


def cmd_generar(args):
    """Genera y publica analysis.json."""
    from dashboard.tema_aprobaciones import agregar_por_tema

    db_path = args.db or Config.EXTERNOS_DB
    aprobaciones = agregar_por_tema(db_path)

    if not aprobaciones:
        print("No hay aprobaciones para generar el reporte.")
        return 1

    data, resultado = generar_reporte_completo(
        aprobaciones, args.periodo, args.fecha_hasta
    )

    if not resultado.es_publicable:
        print(f"ERRORES ({len(resultado.bloqueantes())}):")
        for e in resultado.bloqueantes():
            print(f"  [{e.codigo}] {e.seccion}: {e.mensaje_humano}")
        return 1

    out_path = args.output or os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "analysis.json"
    )
    resultado_pub = publicar_analysis(data, path=out_path)
    if resultado_pub.es_publicable:
        print(f"Analysis generado: {out_path}")
        if resultado_pub.advertencias():
            print(f"  ({len(resultado_pub.advertencias())} advertencias)")
        return 0
    else:
        print("Error al escribir:")
        for e in resultado_pub.bloqueantes():
            print(f"  [{e.codigo}] {e.mensaje_humano}")
        return 1


def cmd_verificar(args):
    """Valida un analysis.json existente."""
    from scripts.verificar import verificar
    result = verificar(args.path)
    if result and not result.es_publicable:
        return 1
    return 0


def cmd_resumen(args):
    """Muestra estadisticas basicas."""
    from dashboard.tema_aprobaciones import agregar_por_tema, resumen_revision

    db_path = args.db or Config.EXTERNOS_DB
    aprob = agregar_por_tema(db_path)
    resumen = resumen_revision(db_path)

    print(f"Aprobados con tema: {resumen.get('aprobados', 0)}")
    print(f"Sin tema (no_aplica): {resumen.get('sin_tema', 0)}")
    print(f"Total aprobaciones: {resumen.get('total_aprobaciones', 0)}")
    if "pendientes" in resumen:
        print(f"Pendientes: {resumen['pendientes']}")

    if aprob:
        print(f"\nTemas ({len(aprob)}):")
        for t in aprob[:10]:
            print(f"  {t['label']}: {t['doc_count']} docs ({t['pct']}%) "
                  f"[apoyo={t['apoyo']}, critica={t['critica']}]")
    return 0


def main():
    parser = argparse.ArgumentParser(description="CLI del pipeline de analisis")
    sub = parser.add_subparsers(dest="comando")

    p_gen = sub.add_parser("generar", help="Generar analysis.json")
    p_gen.add_argument("--periodo", required=True, help="Periodo (ej. 2026-04)")
    p_gen.add_argument("--fecha-hasta", required=True, help="Fecha corte (ISO)")
    p_gen.add_argument("--db", help="Ruta a DB de aprobaciones")
    p_gen.add_argument("--output", help="Ruta de salida")

    p_ver = sub.add_parser("verificar", help="Validar analysis.json")
    p_ver.add_argument("--path", default="data/analysis.json")

    p_res = sub.add_parser("resumen", help="Mostrar estadisticas")
    p_res.add_argument("--db", help="Ruta a DB")

    args = parser.parse_args()

    if args.comando == "generar":
        sys.exit(cmd_generar(args))
    elif args.comando == "verificar":
        sys.exit(cmd_verificar(args))
    elif args.comando == "resumen":
        sys.exit(cmd_resumen(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
