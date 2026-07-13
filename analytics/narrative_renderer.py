"""Renderizador de narrativas con placeholders.

Las narrativas en analysis.json pueden contener placeholders como
{tema_share_seguridad} o {emocion_dominante} que se rellenan con valores
reales calculados.  Esto permite que la IA genere narrativas con la estructura
correcta sin tener que calcular exactamente los numeros.

Placeholders soportados:
  {tema_share_<tema>}       - Share porcentual de un tema
  {tema_doc_count_<tema>}   - Numero de documentos de un tema
  {tema_apoyo_<tema>}       - Conteo de apoyo de un tema
  {tema_critica_<tema>}     - Conteo de critica de un tema
  {emocion_dominante}       - Emocion dominante global
  {emocion_<emo>_pct}       - Porcentaje de una emocion especifica
  {total_aprobados}         - Total de comentarios aprobados
  {total_apoyo}             - Total de apoyos
  {total_critica}           - Total de criticas
  {periodo}                 - Periodo del analisis
  {fecha_hasta}             - Fecha de corte
  {concentracion_nivel}     - Nivel de concentracion tematica
  {polarizacion_nivel}      - Nivel de polarizacion
"""
import re
from analytics.compute import n


_PLACEHOLDER_RE = re.compile(r"\{([a-z_]+)\}")


def renderizar_narrativa(texto: str, contexto: dict) -> str:
    """Reemplaza placeholders {nombre} con valores del contexto.

    Args:
        texto: plantilla con placeholders.
        contexto: dict con los valores disponibles.

    Returns:
        Texto con placeholders reemplazados.
    """
    if not isinstance(texto, str) or not texto:
        return texto

    def _reemplazar(match):
        key = match.group(1)
        val = contexto.get(key)
        if val is None:
            return match.group(0)  # dejar placeholder si no hay valor
        if isinstance(val, float):
            return f"{val:.1f}"
        return str(val)

    return _PLACEHOLDER_RE.sub(_reemplazar, texto)


def renderizar_narrativas_seccion(seccion: dict, contexto: dict) -> dict:
    """Renderiza la narrativa de una seccion completa.

    Si la seccion tiene campo 'narrativa', la renderiza.
    Tambien renderiza 'narrativa' en sub-dict como 'citas_moderadas'.
    """
    if not isinstance(seccion, dict):
        return seccion

    resultado = dict(seccion)
    if "narrativa" in resultado:
        resultado["narrativa"] = renderizar_narrativa(resultado["narrativa"], contexto)

    # Renderizar citas_moderadas si existen
    if "citas_moderadas" in resultado and isinstance(resultado["citas_moderadas"], list):
        resultado["citas_moderadas"] = [
            renderizar_narrativa(cita, contexto) if isinstance(cita, str) else cita
            for cita in resultado["citas_moderadas"]
        ]

    return resultado


def construir_contexto(analysis: dict) -> dict:
    """Construye el dict de contexto para renderizar placeholders.

    Extrae todos los valores calculables del analysis.json para usar como
    placeholders en las narrativas.
    """
    ctx = {}

    meta = analysis.get("meta", {})
    ctx["periodo"] = meta.get("periodo", "")
    ctx["fecha_hasta"] = meta.get("fecha_datos_hasta", "")

    # Bloque 1
    b1 = analysis.get("bloque1", {})

    # Emociones
    ie = b1.get("indice_emociones", {})
    ctx["emocion_dominante"] = ie.get("emocion_dominante", "")
    for key, val in ie.items():
        if key.startswith("pct_"):
            emo_name = key[4:]
            ctx[f"emocion_{emo_name}_pct"] = n(val)

    # Concentracion tematica
    ct = b1.get("concentracion_tematica", {})
    ctx["concentracion_nivel"] = ct.get("nivel", "")
    ramas = ct.get("ramas", [])
    for r in ramas:
        if isinstance(r, dict):
            tema = r.get("tema", "")
            if tema:
                ctx[f"tema_share_{tema}"] = n(r.get("share", 0))
                ctx[f"tema_emocion_{tema}"] = r.get("emocion_dominante", "")

    # Bloque 2
    b2 = analysis.get("bloque2", {})
    ctx["polarizacion_nivel"] = b2.get("polarizacion", {}).get("nivel", "")

    # Totales calculados de voces_influencia
    voces = b2.get("voces_influencia", [])
    total_apoyo = sum(n(v.get("reacciones_totales", 0)) for v in voces)
    total_critica = sum(n(v.get("comentarios_totales", 0)) for v in voces)
    total_aprobados = sum(n(v.get("engagement", 0)) for v in voces)
    ctx["total_aprobados"] = total_aprobados
    ctx["total_apoyo"] = total_apoyo
    ctx["total_critica"] = total_critica

    # Totales por tema de voces
    for v in voces:
        if isinstance(v, dict):
            pagina = v.get("pagina", "")
            if pagina:
                ctx[f"voz_{pagina}_engagement"] = n(v.get("engagement", 0))

    # Bloque 3
    b3 = analysis.get("bloque3", {})
    fricciones = b3.get("puntos_friccion", [])
    for fr in fricciones:
        if isinstance(fr, dict):
            tema = fr.get("tema", "")
            if tema:
                ctx[f"friccion_{tema}_negativos"] = n(fr.get("n_negativos", 0))
                ctx[f"friccion_{tema}_total"] = n(fr.get("n_comentarios_total", 0))

    return ctx


def renderizar_analysis(analysis: dict) -> dict:
    """Renderiza todas las narrativas de un analysis.json completo.

    Returns:
        Nuevo dict con narrativas renderizadas.
    """
    ctx = construir_contexto(analysis)
    result = dict(analysis)

    # Bloque 1
    b1 = dict(analysis.get("bloque1", {}))
    for key in ["clima_narrativo", "indice_emociones", "intensidad",
                "concentracion_tematica", "pulso_iq", "metricas_rendimiento"]:
        if key in b1:
            b1[key] = renderizar_narrativas_seccion(b1[key], ctx)
    result["bloque1"] = b1

    # Bloque 2
    b2 = dict(analysis.get("bloque2", {}))
    voces = b2.get("voces_influencia", [])
    b2["voces_influencia"] = [
        renderizar_narrativas_seccion(v, ctx) if isinstance(v, dict) else v
        for v in voces
    ]
    if "polarizacion" in b2:
        b2["polarizacion"] = renderizar_narrativas_seccion(b2["polarizacion"], ctx)
    result["bloque2"] = b2

    # Bloque 3
    b3 = dict(analysis.get("bloque3", {}))
    for key in ["autenticidad", "velocidad_propagacion", "nivel_alerta"]:
        if key in b3:
            b3[key] = renderizar_narrativas_seccion(b3[key], ctx)
    fricciones = b3.get("puntos_friccion", [])
    b3["puntos_friccion"] = [
        renderizar_narrativas_seccion(fr, ctx) if isinstance(fr, dict) else fr
        for fr in fricciones
    ]
    result["bloque3"] = b3

    # Bloque 4
    b4 = dict(analysis.get("bloque4", {}))
    for key in b4:
        if isinstance(b4[key], dict):
            b4[key] = renderizar_narrativas_seccion(b4[key], ctx)
    result["bloque4"] = b4

    return result
