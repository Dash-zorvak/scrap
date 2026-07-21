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


PLATAFORMA_TABLAS = {
    "facebook": ("", "fb_comments", "comment_id", "message"),
    "tiktok": ("", "comments", "id", "text"),
    "externos": ("", "external_comments", "comment_id", "message"),
}


def cmd_generar(args):
    """Genera y publica analysis.json."""
    from dashboard.tema_aprobaciones import agregar_por_tema_automatico
    from analytics.queries import (
        get_fb_stats, get_tk_stats, get_externos_stats,
        get_fb_daily_volumes, get_tk_daily_volumes,
        get_fb_monthly_sentiment, get_fb_per_theme_controversy,
        get_fb_posts_with_sentiment, get_fb_controversial_posts,
        get_fb_anger_by_zone, get_fb_monthly_controversy,
        get_fb_monthly_theme_controversy,
        get_fb_monthly_er, get_tk_monthly_er,
    )

    # Combinar aprobaciones de las 3 DBs (clasificación automática)
    if args.db:
        aprobaciones = agregar_por_tema_automatico(args.db)
        if aprobaciones:
            for a in aprobaciones:
                a.setdefault("plataforma", "override")
    else:
        aprobaciones = []
        for label, (db_placeholder, tabla, col_id, col_texto) in PLATAFORMA_TABLAS.items():
            db = {
                "facebook": _cfg.FACEBOOK_DB,
                "tiktok": _cfg.TIKTOK_DB,
                "externos": _cfg.EXTERNOS_DB,
            }[label]
            try:
                parcial = agregar_por_tema_automatico(db, tabla=tabla, col_id=col_id, col_texto=col_texto)
                for a in parcial:
                    a.setdefault("plataforma", label)
                aprobaciones.extend(parcial)
            except Exception:
                pass
        aprobaciones.sort(key=lambda x: -x.get("doc_count", 0))
        for i, a in enumerate(aprobaciones):
            a["id"] = i + 1

    if not aprobaciones:
        print("No hay aprobaciones para generar el reporte.")
        return 1

    from analytics.queries import (
        get_fb_comments_with_context, get_tk_comments_with_context,
        get_ext_comments_with_context,
    )

    # ÚNICA fuente de verdad: comentarios con contexto.
    # texts se deriva de ella para garantizar alineación de índices
    # con topic_results_by_text y la clasificación de emoción.
    comentarios_con_contexto = []
    for ctx_fetcher in (get_fb_comments_with_context, get_tk_comments_with_context,
                        get_ext_comments_with_context):
        try:
            ctx_comments = ctx_fetcher()
            comentarios_con_contexto.extend(ctx_comments)
        except Exception:
            pass
    texts = [c["texto"] for c in comentarios_con_contexto if c.get("texto")]

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
        comentarios_con_contexto=comentarios_con_contexto if comentarios_con_contexto else None,
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


def cmd_narrar(args):
    """Redacta narrativas de analysis.json usando Claude (Anthropic API).

    Lee el analysis.json YA publicado y el archivo de evidencia del pipeline.
    Para cada seccion narrativa, construye contexto JSON con cifras calculadas
    y evidencia resuelta, llama a Claude, y escribe el resultado en narrativa
    y enlaces_referencia. No modifica ningun campo numerico/calculado.
    """
    import logging
    from analytics.narrator_claude import redactar_narrativa
    from analytics.evidence import (
        resolver_evidencia_tema, resolver_evidencia_emocion,
        resolver_evidencia_friccion, resolver_evidencia_voz,
        resolver_evidencia_alertas,
    )

    log = logging.getLogger(__name__)

    # Leer analysis.json existente
    data_path = args.path or os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "analysis.json"
    )
    if not os.path.exists(data_path):
        print(f"No se encontro {data_path}. Ejecuta 'generar' primero.")
        return 1
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Leer evidencia del pipeline
    evidencia_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "_evidencia_periodo.json"
    )
    evidencia = {}
    if os.path.exists(evidencia_path):
        with open(evidencia_path, "r", encoding="utf-8") as f:
            evidencia = json.load(f)

    evidencia_por_tema = evidencia.get("por_tema", {})
    evidencia_por_emocion = evidencia.get("por_emocion", {})
    periodo = data.get("meta", {}).get("periodo", "")
    fecha_hasta = data.get("meta", {}).get("fecha_datos_hasta", "")

    modified = False

    # ── Bloque 1 ──
    b1 = data.get("bloque1", {})
    for sec_key in ["clima_narrativo", "indice_emociones", "intensidad",
                    "concentracion_tematica", "pulso_iq", "metricas_rendimiento"]:
        sec = b1.get(sec_key)
        if not isinstance(sec, dict):
            continue
        contexto = _construir_contexto_seccion(sec, meta={"periodo": periodo,
                                                          "fecha_datos_hasta": fecha_hasta})
        try:
            narrativa = redactar_narrativa(_SYSTEM_PROMPT_BLOQUE1, contexto,
                                          section_code=f"b1.{sec_key}")
            enlaces = _resolver_enlaces_seccion(sec_key, evidencia, data)
            sec["narrativa"] = narrativa
            sec["enlaces_referencia"] = enlaces
            modified = True
        except Exception as e:
            log.warning("Fallo narrar seccion b1.%s: %s", sec_key, e)

    # ── Bloque 2: voces individuales + polarizacion ──
    b2 = data.get("bloque2", {})
    for i, voz in enumerate(b2.get("voces_influencia", [])):
        if not isinstance(voz, dict):
            continue
        contexto = _construir_contexto_seccion(voz, meta={"periodo": periodo,
                                                          "fecha_datos_hasta": fecha_hasta})
        contexto["pagina"] = voz.get("pagina", "")
        try:
            narrativa = redactar_narrativa(_SYSTEM_PROMPT_BLOQUE2_VOZ, contexto,
                                          section_code=f"b2.voz[{i}]")
            enlaces = resolver_evidencia_voz(voz.get("pagina", ""), evidencia)
            voz["narrativa"] = narrativa
            voz["enlaces_referencia"] = enlaces
            modified = True
        except Exception as e:
            log.warning("Fallo narrar voz[%d] (%s): %s", i, voz.get("pagina", ""), e)

    pol = b2.get("polarizacion")
    if isinstance(pol, dict):
        contexto = _construir_contexto_seccion(pol, meta={"periodo": periodo,
                                                          "fecha_datos_hasta": fecha_hasta})
        try:
            narrativa = redactar_narrativa(_SYSTEM_PROMPT_BLOQUE2_POL, contexto,
                                          section_code="b2.polarizacion")
            pol["narrativa"] = narrativa
            modified = True
        except Exception as e:
            log.warning("Fallo narrar polarizacion: %s", e)

    # ── Bloque 3 ──
    b3 = data.get("bloque3", {})
    for i, fr in enumerate(b3.get("puntos_friccion", [])):
        if not isinstance(fr, dict):
            continue
        contexto = _construir_contexto_seccion(fr, meta={"periodo": periodo,
                                                          "fecha_datos_hasta": fecha_hasta})
        contexto["tema"] = fr.get("tema", "")
        try:
            narrativa = redactar_narrativa(_SYSTEM_PROMPT_BLOQUE3_FRICCION, contexto,
                                          section_code=f"b3.friccion[{i}]")
            enlaces = resolver_evidencia_friccion(fr.get("tema", ""), evidencia)
            fr["narrativa"] = narrativa
            fr["enlaces_relacionados"] = enlaces
            modified = True
        except Exception as e:
            log.warning("Fallo narrar friccion[%d] (%s): %s", i, fr.get("tema", ""), e)

    for sec_key in ["autenticidad", "velocidad_propagacion"]:
        sec = b3.get(sec_key)
        if not isinstance(sec, dict):
            continue
        contexto = _construir_contexto_seccion(sec, meta={"periodo": periodo,
                                                          "fecha_datos_hasta": fecha_hasta})
        try:
            narrativa = redactar_narrativa(_SYSTEM_PROMPT_BLOQUE3_SECCIONES, contexto,
                                          section_code=f"b3.{sec_key}")
            sec["narrativa"] = narrativa
            modified = True
        except Exception as e:
            log.warning("Fallo narrar b3.%s: %s", sec_key, e)

    nivel = b3.get("nivel_alerta")
    if isinstance(nivel, dict):
        contexto = _construir_contexto_seccion(nivel, meta={"periodo": periodo,
                                                            "fecha_datos_hasta": fecha_hasta})
        alertas = nivel.get("alertas_cambridge", [])
        contexto["alertas_cambridge"] = alertas
        try:
            narrativa = redactar_narrativa(_SYSTEM_PROMPT_BLOQUE3_NIVEL, contexto,
                                          section_code="b3.nivel_alerta")
            enlaces = resolver_evidencia_alertas(alertas, evidencia)
            nivel["narrativa"] = narrativa
            nivel["enlaces_referencia"] = enlaces
            modified = True
        except Exception as e:
            log.warning("Fallo narrar nivel_alerta: %s", e)

    # ── Bloque 4: 8 secciones fijas ──
    b4 = data.get("bloque4", {})
    bloque4_secciones = [
        "eco_historico", "leccion_aprendida", "brecha_percepcion_realidad",
        "contexto_no_visible", "correlacion_contenido_reaccion",
        "comparativa_sectorial", "proyeccion_escenario", "recomendacion_estrategica",
    ]
    for sec_key in bloque4_secciones:
        sec = b4.get(sec_key)
        if not isinstance(sec, dict):
            continue
        contexto = _construir_contexto_seccion_b4(data, sec_key)
        try:
            narrativa = redactar_narrativa(_SYSTEM_PROMPT_BLOQUE4, contexto,
                                          section_code=f"b4.{sec_key}")
            sec["narrativa"] = narrativa
            modified = True
        except Exception as e:
            log.warning("Fallo narrar b4.%s: %s", sec_key, e)

    if not modified:
        print("No se genero ninguna narrativa (todas las secciones fallaron).")
        return 1

    if args.dry_run:
        print("=== DRY RUN: Narrativas generadas (sin escribir) ===\n")
        _imprimir_narrativas(data)
        return 0

    # Publicar con render_narrativas=False (Claude ya entrega texto final)
    from analytics.publish import publicar_analysis
    resultado_pub = publicar_analysis(data, path=data_path, render_narrativas=False)
    if resultado_pub.es_publicable:
        print(f"Narrativas actualizadas: {data_path}")
        if resultado_pub.advertencias():
            print(f"  ({len(resultado_pub.advertencias())} advertencias)")
        return 0
    else:
        print("Error al publicar narrativas:")
        for e in resultado_pub.bloqueantes():
            print(f"  [{e.codigo}] {e.mensaje_humano}")
        return 1


def _construir_contexto_seccion(seccion: dict, meta: dict | None = None) -> dict:
    """Extrae campos numericos/categoricos de una seccion para contexto de Claude."""
    ctx = dict(meta) if meta else {}
    for key, val in seccion.items():
        if key in ("narrativa", "enlaces_referencia", "enlaces_relacionados",
                    "formula_usada", "postura_nota", "alcance_nota"):
            continue
        if isinstance(val, (int, float, str, bool)):
            ctx[key] = val
        elif isinstance(val, list) and key in ("alertas_cambridge",):
            ctx[key] = val
    return ctx


def _construir_contexto_seccion_b4(analysis: dict, sec_key: str) -> dict:
    """Construye contexto para una seccion de bloque4 con datos de otros bloques."""
    meta = analysis.get("meta", {})
    ctx = {
        "periodo": meta.get("periodo", ""),
        "fecha_datos_hasta": meta.get("fecha_datos_hasta", ""),
        "seccion": sec_key,
    }
    # Datos de bloque1
    b1 = analysis.get("bloque1", {})
    cn = b1.get("clima_narrativo", {})
    ctx["tono_dominante"] = cn.get("tono_dominante", "")
    ctx["pct_favorable"] = cn.get("pct_favorable", 0)
    ctx["pct_critico"] = cn.get("pct_critico", 0)
    ctx["n_total_comentarios"] = cn.get("n_total_comentarios", 0)
    ie = b1.get("indice_emociones", {})
    ctx["emocion_dominante"] = ie.get("emocion_dominante", "")
    ct = b1.get("concentracion_tematica", {})
    ctx["top_tema"] = ct.get("top_tema", "")
    ctx["hhi"] = ct.get("hhi", 0)
    mr = b1.get("metricas_rendimiento", {})
    ctx["engagement_rate"] = mr.get("engagement_rate", 0)
    # Datos de bloque3
    b3 = analysis.get("bloque3", {})
    na = b3.get("nivel_alerta", {})
    ctx["semaforo"] = na.get("semaforo", "")
    ctx["indice_riesgo"] = na.get("indice_riesgo", 0)
    fricciones = b3.get("puntos_friccion", [])
    ctx["temas_friccion"] = [fr.get("tema", "") for fr in fricciones if isinstance(fr, dict)]
    return ctx


def _resolver_enlaces_seccion(sec_key: str, evidencia: dict, data: dict) -> list:
    """Resuelve enlaces de referencia para una seccion de bloque1."""
    from analytics.evidence import (
        resolver_evidencia_tema, resolver_evidencia_emocion,
    )
    enlaces = []
    evidencia_por_tema = evidencia.get("por_tema", {})
    evidencia_por_emocion = evidencia.get("por_emocion", {})

    if sec_key in ("concentracion_tematica",):
        for tema in list(evidencia_por_tema.keys()):
            enlaces.extend(resolver_evidencia_tema(tema, evidencia_por_tema))
    elif sec_key in ("indice_emociones",):
        for emo in list(evidencia_por_emocion.keys()):
            enlaces.extend(resolver_evidencia_emocion(emo, evidencia_por_emocion))
    elif sec_key == "clima_narrativo":
        cn = data.get("bloque1", {}).get("clima_narrativo", {})
        if cn.get("pct_critico", 0) > 0:
            for tema in list(evidencia_por_tema.keys()):
                enlaces.extend(resolver_evidencia_tema(tema, evidencia_por_tema))
    return list(dict.fromkeys(enlaces))


def _imprimir_narrativas(data: dict):
    """Imprime todas las narrativas del analysis para revision manual."""
    for bloque_key in ["bloque1", "bloque2", "bloque3", "bloque4"]:
        bloque = data.get(bloque_key, {})
        if not isinstance(bloque, dict):
            continue
        for sec_key, sec_val in bloque.items():
            if isinstance(sec_val, dict):
                narr = sec_val.get("narrativa", "")
                if narr:
                    enl = sec_val.get("enlaces_referencia",
                                      sec_val.get("enlaces_relacionados", []))
                    print(f"[{bloque_key}.{sec_key}]")
                    print(f"  {narr[:200]}{'...' if len(narr) > 200 else ''}")
                    if enl:
                        print(f"  Enlaces: {len(enl)}")
                    print()
            elif isinstance(sec_val, list):
                for i, item in enumerate(sec_val):
                    if isinstance(item, dict):
                        narr = item.get("narrativa", "")
                        if narr:
                            print(f"[{bloque_key}.{sec_key}[{i}]]")
                            print(f"  {narr[:200]}{'...' if len(narr) > 200 else ''}")
                            print()


_SYSTEM_PROMPT_BLOQUE1 = (
    "Eres el redactor de narrativas de analisis de comunicacion para un "
    "gobierno municipal. Escribe narrativas sobrias, directas, sin adjetivos "
    "vagos. REGLAS OBLIGATORIAS:\n"
    "- RG-0: El sentimiento fue calculado por reglas lexicas, NUNCA mencionar IA.\n"
    "- RG-1: No usar siglas tecnicas (HHI, NSI, IR, PI, ER) en la narrativa. "
    "Solo van en formula_usada.\n"
    "- RG-2: Solo datos del periodo analizado.\n"
    "- RG-3: Nunca usar censura/autocensura. Usar 'limitacion metodologica'.\n"
    "- RG-4: Engagement != Impresiones.\n"
    "- RG-5: Toda afirmacion con cifra debe tener enlace real.\n"
    "- No calcules ni inventes ninguna cifra que no este en el JSON de contexto. "
    "Si falta un dato, dilo explicitamente en vez de inventarlo.\n"
    "- Para Clima Narrativo: seguir la plantilla exacta del ANALYST_GUIDE.md "
    "(cifras crudas, comparacion, ancla con tema, Conclusión, "
    "= NOMBRE CONTUNDENTE EN MAYUSCULAS).\n"
)

_SYSTEM_PROMPT_BLOQUE2_VOZ = (
    "Redacta la narrativa para una voz de influencia en el analisis de "
    "comunicacion municipal. Describe su engagement y relevancia sin "
    "inventar cifras. No usar siglas tecnicas. Solo datos del periodo.\n"
    "- No calcules ni inventes ninguna cifra que no este en el JSON de contexto.\n"
)

_SYSTEM_PROMPT_BLOQUE2_POL = (
    "Redacta la narrativa de polarizacion. Describe el nivel de division "
    "o consenso sin usar 'censura' ni 'autocensura'. "
    "Usar 'limitacion metodologica' si aplica.\n"
    "- No calcules ni inventes ninguna cifra que no este en el JSON de contexto.\n"
)

_SYSTEM_PROMPT_BLOQUE3_FRICCION = (
    "Redacta la narrativa para un punto de friccion. Describe la tension "
    "especifica citando el tema, numero de criticas y emocion dominante. "
    "No inventar cifras.\n"
)

_SYSTEM_PROMPT_BLOQUE3_SECCIONES = (
    "Redacta la narrativa para esta seccion del bloque de Riesgo y "
    "Autenticidad. Si hay datos concretos, usarlos directamente. "
    "Si no hay datos suficientes, decirlo explicitamente.\n"
    "- No calcules ni inventes ninguna cifra que no este en el JSON de contexto.\n"
)

_SYSTEM_PROMPT_BLOQUE3_NIVEL = (
    "Redacta la narrativa del nivel de alerta general. Describe el "
    "semaforo de riesgo y las alertas activas sin inventar datos. "
    "Cada alerta debe mencionar su tipo y descripcion.\n"
    "- No calcules ni inventes ninguna cifra que no este en el JSON de contexto.\n"
)

_SYSTEM_PROMPT_BLOQUE4 = (
    "Eres el estratega que redacta el Memorandum Estrategico (Bloque IV) "
    "del analisis de comunicacion de un gobierno municipal. "
    "REGLAS OBLIGATORIAS:\n"
    "- RG-0: Sentimiento calculado por reglas lexicas, nunca mencionar IA.\n"
    "- RG-1: No usar siglas tecnicas en la narrativa.\n"
    "- RG-2: Solo datos del periodo analizado.\n"
    "- RG-3: No usar censura/autocensura.\n"
    "- RG-5: Toda afirmacion con cifra debe tener enlace real.\n"
    "- Integrar numeros/porcentajes reales dentro de la prosa.\n"
    "- No calcules ni inventes ninguna cifra que no este en el JSON de contexto.\n"
    "- Si falta un dato, decirlo explicitamente.\n"
)


def cmd_verificar(args):
    """Valida un analysis.json existente."""
    from scripts.verificar import verificar
    result = verificar(args.path)
    if result and not result.es_publicable:
        return 1
    return 0


def cmd_resumen(args):
    """Muestra estadisticas basicas."""
    from dashboard.tema_aprobaciones import agregar_por_tema_automatico, resumen_revision

    db_path = args.db or _cfg.EXTERNOS_DB
    aprob = agregar_por_tema_automatico(db_path)
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

    p_nar = sub.add_parser("narrar", help="Redactar narrativas con Claude")
    p_nar.add_argument("--path", default="data/analysis.json",
                       help="Ruta a analysis.json")
    p_nar.add_argument("--dry-run", action="store_true",
                       help="Imprimir narrativas sin escribir")

    args = parser.parse_args()

    if args.comando == "generar":
        sys.exit(cmd_generar(args))
    elif args.comando == "verificar":
        sys.exit(cmd_verificar(args))
    elif args.comando == "resumen":
        sys.exit(cmd_resumen(args))
    elif args.comando == "narrar":
        sys.exit(cmd_narrar(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
