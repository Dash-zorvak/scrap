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

from src.config import Config
from analytics.report import construir_analysis, generar_reporte_completo
from analytics.publish import publicar_analysis
from analytics.schema_validator import validar

_cfg = Config()


def _periodo_anterior(periodo: str) -> str:
    """Dado 'YYYY-MM', retorna el mes anterior 'YYYY-MM'."""
    y, m = map(int, periodo.split("-"))
    m -= 1
    if m == 0:
        m = 12
        y -= 1
    return f"{y:04d}-{m:02d}"


def _calcular_er_previo(
    periodo_prev: str,
    fb_monthly: list[tuple],
    tk_monthly: list[tuple],
) -> float | None:
    """Calcula er_previo con la misma metodología ponderado_volumen.

    Retorna None si no hay datos de ambas plataformas para el período
    previo (para no comparar bases distintas).
    """
    fb_prev = next((row for row in fb_monthly if row[0] == periodo_prev), None)
    tk_prev = next((row for row in tk_monthly if row[0] == periodo_prev), None)

    if fb_prev is None or tk_prev is None:
        return None

    er_fb_prev, vol_fb_prev = fb_prev[1], fb_prev[2]
    er_tk_prev, vol_tk_prev = tk_prev[1], tk_prev[2]

    vol_total = vol_fb_prev + vol_tk_prev
    if vol_total <= 0:
        return None

    return round(
        er_fb_prev * (vol_fb_prev / vol_total) + er_tk_prev * (vol_tk_prev / vol_total),
        2,
    )


def cmd_generar(args):
    """Genera y publica analysis.json."""
    from dashboard.tema_aprobaciones import agregar_por_tema
    from analytics.queries import (
        get_fb_comments_with_messages, get_tk_comments_with_messages,
        get_ext_comments_with_messages,
        get_fb_stats, get_tk_stats, get_externos_stats,
        get_fb_daily_volumes, get_tk_daily_volumes,
        get_fb_monthly_sentiment, get_fb_per_theme_controversy,
        get_fb_posts_with_sentiment, get_fb_controversial_posts,
        get_fb_anger_by_zone, get_fb_monthly_controversy,
        get_fb_monthly_theme_controversy,
        get_fb_monthly_er, get_tk_monthly_er,
    )

    # Combinar aprobaciones de las 3 DBs
    if args.db:
        aprobaciones = agregar_por_tema(args.db)
        if aprobaciones:
            for a in aprobaciones:
                a.setdefault("plataforma", "override")
    else:
        aprobaciones = []
        for label, db in [("facebook", _cfg.FACEBOOK_DB),
                          ("tiktok", _cfg.TIKTOK_DB),
                          ("externos", _cfg.EXTERNOS_DB)]:
            try:
                parcial = agregar_por_tema(db)
                for a in parcial:
                    a.setdefault("plataforma", label)
                aprobaciones.extend(parcial)
            except Exception:
                pass
        # Re-ordenar por doc_count descendente y renumerar ids
        aprobaciones.sort(key=lambda x: -x.get("doc_count", 0))
        for i, a in enumerate(aprobaciones):
            a["id"] = i + 1

    if not aprobaciones:
        print("No hay aprobaciones para generar el reporte.")
        return 1

    # Obtener textos crudos de comentarios de las 3 plataformas
    texts = []
    for fetcher in (get_fb_comments_with_messages, get_tk_comments_with_messages,
                    get_ext_comments_with_messages):
        try:
            comments = fetcher()
            texts.extend(msg for _, msg in comments if msg)
        except Exception:
            pass

    # Obtener stats de plataformas desde las DBs
    fb_stats = None
    tk_stats = None
    try:
        fb = get_fb_stats()
        if fb and fb.get("posts", 0) > 0:
            fb_stats = fb
            fb_stats["daily_volumes"] = get_fb_daily_volumes()
    except Exception:
        pass
    try:
        tk = get_tk_stats()
        if tk and tk.get("videos", 0) > 0:
            tk_stats = tk
            tk_stats["daily_volumes"] = get_tk_daily_volumes()
    except Exception:
        pass
    externos_stats = None
    try:
        ext = get_externos_stats()
        if ext and ext.get("posts", 0) > 0:
            externos_stats = ext
    except Exception:
        pass

    # Datos históricos para §F/§H
    fb_monthly_sentiment = None
    fb_per_theme_controversy = None
    fb_posts_with_sentiment = None
    fb_controversial_posts = None
    fb_anger_by_zone = None
    fb_monthly_controversy = None
    fb_monthly_theme_controversy = None
    try:
        fb_monthly_sentiment = get_fb_monthly_sentiment()
    except Exception:
        pass
    try:
        fb_per_theme_controversy = get_fb_per_theme_controversy()
    except Exception:
        pass
    try:
        fb_posts_with_sentiment = get_fb_posts_with_sentiment()
    except Exception:
        pass
    try:
        fb_controversial_posts = get_fb_controversial_posts()
    except Exception:
        pass
    try:
        fb_anger_by_zone = get_fb_anger_by_zone()
    except Exception:
        pass
    try:
        fb_monthly_controversy = get_fb_monthly_controversy()
    except Exception:
        pass
    try:
        fb_monthly_theme_controversy = get_fb_monthly_theme_controversy()
    except Exception:
        pass

    # §F EFI: Compute er_previo from previous month, same methodology as er_display
    er_previo = None
    try:
        periodo_prev = _periodo_anterior(args.periodo)
        fb_monthly = get_fb_monthly_er()
        tk_monthly = get_tk_monthly_er()
        er_previo = _calcular_er_previo(periodo_prev, fb_monthly, tk_monthly)
    except Exception:
        pass

    data, resultado = generar_reporte_completo(
        aprobaciones, args.periodo, args.fecha_hasta,
        comentarios_texts=texts if texts else None,
        fb_stats=fb_stats,
        tk_stats=tk_stats,
        externos_stats=externos_stats,
        er_previo=er_previo,
        fb_monthly_sentiment=fb_monthly_sentiment,
        fb_per_theme_controversy=fb_per_theme_controversy,
        fb_posts_with_sentiment=fb_posts_with_sentiment,
        fb_controversial_posts=fb_controversial_posts,
        fb_anger_by_zone=fb_anger_by_zone,
        fb_monthly_controversy=fb_monthly_controversy,
        fb_monthly_theme_controversy=fb_monthly_theme_controversy,
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

    db_path = args.db or _cfg.EXTERNOS_DB
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
