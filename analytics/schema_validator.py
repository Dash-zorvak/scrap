"""Validador estructural y de negocio de data/analysis.json.

Unica fuente de verdad de que hace que un analysis.json sea PUBLICABLE.
No calcula nada (eso es analytics/compute.py, Fase 5). No conoce Streamlit.
Se usa desde el pipeline de generacion (bloquea antes de guardar) y desde
el dashboard (para decidir que tarjetas puede mostrar sin datos rotos).
"""
from dataclasses import dataclass, field


@dataclass
class ValidationError:
    codigo: str          # ej. "V01_ENGAGEMENT_SIN_SUBMETRICAS"
    seccion: str         # ej. "bloque2.voces_influencia[2]"
    severidad: str       # "bloqueante" | "advertencia"
    mensaje_tecnico: str
    mensaje_humano: str


@dataclass
class ValidationResult:
    errores: list = field(default_factory=list)

    @property
    def es_publicable(self) -> bool:
        return not any(e.severidad == "bloqueante" for e in self.errores)

    def bloqueantes(self):
        return [e for e in self.errores if e.severidad == "bloqueante"]

    def advertencias(self):
        return [e for e in self.errores if e.severidad == "advertencia"]


def _get(d, *keys, default=None):
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, default)
        else:
            return default
    return d


def validar(data: dict) -> ValidationResult:
    """Valida un dict de analysis.json contra todas las reglas V01-V08."""
    result = ValidationResult()

    if not isinstance(data, dict):
        result.errores.append(ValidationError(
            codigo="V00_NO_ES_DICT",
            seccion="raiz",
            severidad="bloqueante",
            mensaje_tecnico="analysis.json no es un dict",
            mensaje_humano="El archivo de analisis no tiene la estructura correcta.",
        ))
        return result

    b1 = data.get("bloque1", {})
    b2 = data.get("bloque2", {})
    b3 = data.get("bloque3", {})
    b4 = data.get("bloque4", {})

    # ── V01: Voces de influencia — engagement vs submetricas ──
    for i, voz in enumerate(b2.get("voces_influencia", [])):
        if not isinstance(voz, dict):
            continue
        eng = voz.get("engagement", 0) or 0
        sum_sub = (
            (voz.get("reacciones_totales") or 0)
            + (voz.get("comentarios_totales") or 0)
            + (voz.get("compartidos_totales") or 0)
        )
        if eng > 0 and sum_sub == 0:
            pagina = voz.get("pagina", "desconocida")
            result.errores.append(ValidationError(
                codigo="V01_ENGAGEMENT_SIN_SUBMETRICAS",
                seccion=f"bloque2.voces_influencia[{i}]",
                severidad="bloqueante",
                mensaje_tecnico=f"'{pagina}' tiene engagement={eng} pero reacciones+comentarios+compartidos=0",
                mensaje_humano=f"Los datos de '{pagina}' son inconsistentes.",
            ))

    # ── V02: Concentracion tematica — shares deben sumar 100 ──
    ramas = _get(b1, "concentracion_tematica", "ramas", default=[])
    if isinstance(ramas, list) and ramas:
        suma = sum(
            r.get("share", 0) for r in ramas
            if isinstance(r, dict) and isinstance(r.get("share"), (int, float))
        )
        if abs(suma - 100) > 1.5:
            result.errores.append(ValidationError(
                codigo="V02_SHARES_TEMATICA_NO_SUMAN_100",
                seccion="bloque1.concentracion_tematica",
                severidad="bloqueante",
                mensaje_tecnico=f"Shares suman {suma:.1f}% (esperado 100%)",
                mensaje_humano="La distribucion tematica no suma 100%.",
            ))

    # ── V03: Puntos de friccion — emocion_dominante vacia con n_negativos > 0 ──
    for i, fr in enumerate(b3.get("puntos_friccion", [])):
        if not isinstance(fr, dict):
            continue
        n_neg = fr.get("n_negativos", 0) or 0
        emo = (fr.get("emocion_dominante") or "").strip()
        if n_neg > 0 and not emo:
            tema = fr.get("tema", "desconocido")
            result.errores.append(ValidationError(
                codigo="V03_FRICCION_SIN_EMOCION",
                seccion=f"bloque3.puntos_friccion[{i}]",
                severidad="bloqueante",
                mensaje_tecnico=f"Punto '{tema}' tiene n_negativos={n_neg} pero emocion_dominante vacia",
                mensaje_humano=f"El punto de friccion '{tema}' necesita una emocion dominante.",
            ))

    # ── V04: alertas_cambridge — descripcion debe ser string, no dict ──
    for i, alerta in enumerate(_get(b3, "nivel_alerta", "alertas_cambridge", default=[])):
        if isinstance(alerta, dict):
            desc = alerta.get("descripcion")
            if isinstance(desc, dict):
                tipo = alerta.get("tipo", "desconocido")
                result.errores.append(ValidationError(
                    codigo="V04_ALERTA_DESCRIPCION_MAL_TIPADA",
                    seccion=f"bloque3.nivel_alerta.alertas_cambridge[{i}]",
                    severidad="bloqueante",
                    mensaje_tecnico=f"Alerta '{tipo}': 'descripcion' es dict en vez de string",
                    mensaje_humano=f"La alerta '{tipo}' tiene un formato incorrecto.",
                ))

    # ── V05: Secciones de bloque4 deben ser dict con narrativa ──
    secciones_b4 = [
        "eco_historico", "leccion_aprendida", "brecha_percepcion_realidad",
        "contexto_no_visible", "correlacion_contenido_reaccion",
        "comparativa_sectorial", "proyeccion_escenario", "recomendacion_estrategica",
    ]
    for sec in secciones_b4:
        val = b4.get(sec)
        if val is not None and not isinstance(val, dict):
            result.errores.append(ValidationError(
                codigo="V05_BLOQUE4_MAL_TIPADO",
                seccion=f"bloque4.{sec}",
                severidad="bloqueante",
                mensaje_tecnico=f"bloque4.{sec} debe ser dict con campo 'narrativa'",
                mensaje_humano=f"La seccion '{sec}' no tiene el formato correcto.",
            ))

    # ── V06: meta.periodo obligatorio y coherente (H-DS4) ──
    meta = data.get("meta", {})
    if not meta.get("periodo"):
        result.errores.append(ValidationError(
            codigo="V06_META_PERIODO_INCOMPLETO",
            seccion="meta.periodo",
            severidad="bloqueante",
            mensaje_tecnico="meta.periodo esta vacio o ausente",
            mensaje_humano="Falta el periodo del analisis.",
        ))
    if not meta.get("fecha_datos_hasta"):
        result.errores.append(ValidationError(
            codigo="V06_META_PERIODO_INCOMPLETO",
            seccion="meta.fecha_datos_hasta",
            severidad="bloqueante",
            mensaje_tecnico="meta.fecha_datos_hasta esta vacio o ausente",
            mensaje_humano="Falta la fecha de corte de datos.",
        ))
    if not meta.get("generado_en"):
        result.errores.append(ValidationError(
            codigo="V06_META_PERIODO_INCOMPLETO",
            seccion="meta.generado_en",
            severidad="bloqueante",
            mensaje_tecnico="meta.generado_en esta vacio o ausente",
            mensaje_humano="Falta la marca de tiempo de generacion.",
        ))

    # ── V07: Categoria/postura/emocion desconocida (H-DS1) ──
    _validar_categorias_json(data, result)

    # ── V08: Narrativas sin enlaces de referencia (advertencia) ──
    _validar_narrativas_sin_enlaces(data, result)

    # ── V09: Narrativas con placeholders sin resolver (advertencia) ──
    _validar_placeholders_sin_resolver(data, result)

    # ── V10: Coherencia de totales con DB de aprobaciones ──
    _validar_coherencia_totales(data, result)

    # ── V11: Temas en analysis.json existen en aprobaciones ──
    _validar_temas_en_aprobaciones(data, result)

    return result


def _validar_categorias_json(data: dict, result: ValidationResult):
    """V07: categorías no canónicas.

    - Emoción/postura/tema en catálogo → OK.
    - Emoción/postura/tema registrado como propuesta en taxonomias_pendientes → advertencia.
    - Emoción/postura/tema no registrado en ningún lado → bloqueante.
    """
    try:
        from dashboard.tema_taxonomia import EMOCIONES_VALIDAS, POSTURAS_VALIDAS, CATEGORIAS_VALIDAS
    except ImportError:
        return  # si la taxonomia no esta disponible, skip V07

    # Cargar propuestas pendientes para distinguir advertencia vs bloqueante
    import json as _json
    import os as _os
    _pendientes_path = _os.path.join(
        _os.path.dirname(__file__), _os.pardir, "data", "taxonomias_pendientes.json"
    )
    pendientes_keys: set[str] = set()
    try:
        with open(_pendientes_path, "r", encoding="utf-8") as _f:
            for _entry in _json.load(_f):
                if _entry.get("estado") == "pendiente":
                    pendientes_keys.add(_entry.get("clave_propuesta", ""))
    except (FileNotFoundError, _json.JSONDecodeError, OSError):
        pass

    # Verificar emociones en indice_emociones
    ie = _get(data, "bloque1", "indice_emociones", default={})
    if isinstance(ie, dict):
        emocion_dom = (ie.get("emocion_dominante") or "").strip()
        if emocion_dom and emocion_dom not in EMOCIONES_VALIDAS:
            es_propuesta = emocion_dom in pendientes_keys
            result.errores.append(ValidationError(
                codigo="V07_CATEGORIA_DESCONOCIDA",
                seccion="bloque1.indice_emociones.emocion_dominante",
                severidad="advertencia" if es_propuesta else "bloqueante",
                mensaje_tecnico=f"emocion_dominante '{emocion_dom}' no esta en el catalogo"
                + (" (propuesta pendiente)" if es_propuesta else ""),
                mensaje_humano=f"La emocion '{emocion_dom}' no es reconocida."
                + (" Está registrada como propuesta pendiente." if es_propuesta else ""),
            ))

    # Verificar emociones en concentracion_tematica.ramas
    ramas = _get(data, "bloque1", "concentracion_tematica", "ramas", default=[])
    if isinstance(ramas, list):
        for i, r in enumerate(ramas):
            if not isinstance(r, dict):
                continue
            tema = (r.get("tema") or "").strip()
            if tema and tema not in CATEGORIAS_VALIDAS:
                result.errores.append(ValidationError(
                    codigo="V07_CATEGORIA_DESCONOCIDA",
                    seccion=f"bloque1.concentracion_tematica.ramas[{i}].tema",
                    severidad="bloqueante",
                    mensaje_tecnico=f"tema '{tema}' no esta en el catalogo de categorias",
                    mensaje_humano=f"El tema '{tema}' no es reconocido.",
                ))
            emo = (r.get("emocion_dominante") or "").strip()
            if emo and emo not in EMOCIONES_VALIDAS:
                es_propuesta = emo in pendientes_keys
                result.errores.append(ValidationError(
                    codigo="V07_CATEGORIA_DESCONOCIDA",
                    seccion=f"bloque1.concentracion_tematica.ramas[{i}].emocion_dominante",
                    severidad="advertencia" if es_propuesta else "bloqueante",
                    mensaje_tecnico=f"emocion '{emo}' no esta en el catalogo"
                    + (" (propuesta pendiente)" if es_propuesta else ""),
                    mensaje_humano=f"La emocion '{emo}' no es reconocida."
                    + (" Está registrada como propuesta pendiente." if es_propuesta else ""),
                ))

    # Verificar posturas en voces_influencia
    for i, v in enumerate(_get(data, "bloque2", "voces_influencia", default=[])):
        if not isinstance(v, dict):
            continue
        postura = (v.get("postura") or "").strip()
        if postura and postura not in POSTURAS_VALIDAS:
            result.errores.append(ValidationError(
                codigo="V07_CATEGORIA_DESCONOCIDA",
                seccion=f"bloque2.voces_influencia[{i}].postura",
                severidad="bloqueante",
                mensaje_tecnico=f"postura '{postura}' no esta en el catalogo",
                mensaje_humano=f"La postura '{postura}' no es reconocida.",
            ))

    # Verificar emociones en puntos_friccion
    for i, fr in enumerate(_get(data, "bloque3", "puntos_friccion", default=[])):
        if not isinstance(fr, dict):
            continue
        emo = (fr.get("emocion_dominante") or "").strip()
        if emo and emo not in EMOCIONES_VALIDAS:
            es_propuesta = emo in pendientes_keys
            result.errores.append(ValidationError(
                codigo="V07_CATEGORIA_DESCONOCIDA",
                seccion=f"bloque3.puntos_friccion[{i}].emocion_dominante",
                severidad="advertencia" if es_propuesta else "bloqueante",
                mensaje_tecnico=f"emocion '{emo}' no esta en el catalogo"
                + (" (propuesta pendiente)" if es_propuesta else ""),
                mensaje_humano=f"La emocion '{emo}' no es reconocida."
                + (" Está registrada como propuesta pendiente." if es_propuesta else ""),
            ))


def _validar_narrativas_sin_enlaces(data: dict, result: ValidationResult):
    """V08: narrativas que citan cifras pero no tienen enlaces (advertencia)."""
    import re
    patron = re.compile(r'\d+%|\d+\s*(comentarios|posts|publicaciones)')

    def _checar_narrativa(texto, enlaces, seccion):
        if not isinstance(texto, str) or not isinstance(enlaces, list):
            return
        if patron.search(texto) and not enlaces:
            result.errores.append(ValidationError(
                codigo="V08_NARRATIVA_SIN_ENLACES",
                seccion=seccion,
                severidad="advertencia",
                mensaje_tecnico=f"Narrativa en {seccion} cita cifras pero enlaces_referencia esta vacio",
                mensaje_humano=f"La narrativa de {seccion} referencia datos sin fuentes.",
            ))

    # Chequear narrativas de bloque1
    for key in ["clima_narrativo", "indice_emociones", "intensidad",
                "concentracion_tematica", "pulso_iq", "metricas_rendimiento"]:
        sec = _get(data, "bloque1", key, default={})
        if isinstance(sec, dict):
            narr = sec.get("narrativa", "")
            enl = sec.get("enlaces_referencia", [])
            _checar_narrativa(narr, enl, f"bloque1.{key}")

    # Chequear narrativas de bloque2
    for i, v in enumerate(_get(data, "bloque2", "voces_influencia", default=[])):
        if isinstance(v, dict):
            _checar_narrativa(v.get("narrativa", ""), v.get("enlaces_referencia", []),
                              f"bloque2.voces_influencia[{i}]")

    # Chequear narrativas de bloque3
    for key in ["autenticidad", "velocidad_propagacion"]:
        sec = _get(data, "bloque3", key, default={})
        if isinstance(sec, dict):
            _checar_narrativa(sec.get("narrativa", ""), sec.get("enlaces_referencia", []),
                              f"bloque3.{key}")
    for i, fr in enumerate(_get(data, "bloque3", "puntos_friccion", default=[])):
        if isinstance(fr, dict):
            _checar_narrativa(fr.get("narrativa", ""), fr.get("enlaces_relacionados", []),
                              f"bloque3.puntos_friccion[{i}]")


def _validar_placeholders_sin_resolver(data: dict, result: ValidationResult):
    """V09: narrativas que contienen placeholders {xxx} sin resolver (advertencia).

    Esto indica que el narrative_renderer no fue ejecutado o fallo.
    """
    import re
    patron = re.compile(r"\{[a-z_]+\}")

    def _checar(texto, seccion):
        if not isinstance(texto, str):
            return
        placeholders = patron.findall(texto)
        if placeholders:
            result.errores.append(ValidationError(
                codigo="V09_PLACEHOLDER_SIN_RESOLVER",
                seccion=seccion,
                severidad="advertencia",
                mensaje_tecnico=f"Narrativa contiene placeholders sin resolver: {', '.join(placeholders[:3])}",
                mensaje_humano=f"La narrativa de {seccion} tiene datos sin completar.",
            ))

    # Recorrer todas las narrativas del analysis
    for bloque_key in ["bloque1", "bloque2", "bloque3", "bloque4"]:
        bloque = data.get(bloque_key, {})
        if not isinstance(bloque, dict):
            continue
        for sec_key, sec_val in bloque.items():
            if isinstance(sec_val, dict):
                _checar(sec_val.get("narrativa", ""), f"{bloque_key}.{sec_key}")
                for i, item in enumerate(sec_val.get("citas_moderadas", [])):
                    _checar(item, f"{bloque_key}.{sec_key}.citas_moderadas[{i}]")
            elif isinstance(sec_val, list):
                for i, item in enumerate(sec_val):
                    if isinstance(item, dict):
                        _checar(item.get("narrativa", ""), f"{bloque_key}.{sec_key}[{i}]")


def _validar_coherencia_totales(data: dict, result: ValidationResult):
    """V10: Verifica que los totales en analysis.json sean coherentes.

    Compara el total de voces_influencia con la suma de sus sub-metricas
    y verifica que no haya valores negativos donde no corresponden.
    """
    voces = _get(data, "bloque2", "voces_influencia", default=[])
    for i, v in enumerate(voces):
        if not isinstance(v, dict):
            continue
        eng = _n(v.get("engagement", 0))
        reco = _n(v.get("reacciones_totales", 0))
        comp = _n(v.get("comentarios_totales", 0))
        compa = _n(v.get("compartidos_totales", 0))

        # Valores negativos son sospechosos
        for campo, val in [("engagement", eng), ("reacciones_totales", reco),
                           ("comentarios_totales", comp), ("compartidos_totales", compa)]:
            if val < 0:
                result.errores.append(ValidationError(
                    codigo="V10_VALOR_NEGATIVO",
                    seccion=f"bloque2.voces_influencia[{i}].{campo}",
                    severidad="bloqueante",
                    mensaje_tecnico=f"{campo}={val} es negativo",
                    mensaje_humano=f"El campo {campo} tiene un valor negativo inesperado.",
                ))

        # Si engagement > 0, al menos una submetrica debe ser > 0
        if eng > 0 and reco == 0 and comp == 0 and compa == 0:
            result.errores.append(ValidationError(
                codigo="V10_ENGAGEMENT_SIN_SUBMETRICAS",
                seccion=f"bloque2.voces_influencia[{i}]",
                severidad="advertencia",
                mensaje_tecnico=f"engagement={eng} pero todas las submetricas son 0",
                mensaje_humano=f"Los datos de engagement en la voz {i} parecen incompletos.",
            ))

    # Verificar shares de concentracion tematica
    ramas = _get(data, "bloque1", "concentracion_tematica", "ramas", default=[])
    for i, r in enumerate(ramas):
        if not isinstance(r, dict):
            continue
        share = _n(r.get("share", 0))
        if share < 0:
            result.errores.append(ValidationError(
                codigo="V10_SHARE_NEGATIVO",
                seccion=f"bloque1.concentracion_tematica.ramas[{i}]",
                severidad="bloqueante",
                mensaje_tecnico=f"share={share} es negativo",
                mensaje_humano=f"El share del tema {r.get('tema', i)} es negativo.",
            ))


def _validar_temas_en_aprobaciones(data: dict, result: ValidationResult):
    """V11: Verifica que los temas mencionados en analysis.json sean validos.

    Los temas en concentracion_tematica.ramas y puntos_friccion deben
    pertenecer al catalogo de categorias validas.
    """
    try:
        from dashboard.tema_taxonomia import CATEGORIAS_VALIDAS, REMAP_LEGACY
    except ImportError:
        return

    validas = CATEGORIAS_VALIDAS | set(REMAP_LEGACY.keys())

    # Temas en concentracion_tematica
    ramas = _get(data, "bloque1", "concentracion_tematica", "ramas", default=[])
    for i, r in enumerate(ramas):
        if not isinstance(r, dict):
            continue
        tema = (r.get("tema") or "").strip()
        if tema and tema not in validas and tema != "no_aplica":
            result.errores.append(ValidationError(
                codigo="V11_TEMA_NO_VALIDO",
                seccion=f"bloque1.concentracion_tematica.ramas[{i}]",
                severidad="advertencia",
                mensaje_tecnico=f"tema '{tema}' no esta en el catalogo de aprobaciones",
                mensaje_humano=f"El tema '{tema}' no esta en el catalogo oficial.",
            ))

    # Temas en puntos_friccion
    fricciones = _get(data, "bloque3", "puntos_friccion", default=[])
    for i, fr in enumerate(fricciones):
        if not isinstance(fr, dict):
            continue
        tema = (fr.get("tema") or "").strip()
        if tema and tema not in validas and tema != "no_aplica":
            result.errores.append(ValidationError(
                codigo="V11_TEMA_NO_VALIDO",
                seccion=f"bloque3.puntos_friccion[{i}]",
                severidad="advertencia",
                mensaje_tecnico=f"tema '{tema}' no esta en el catalogo de aprobaciones",
                mensaje_humano=f"El tema '{tema}' en friccion no esta en el catalogo oficial.",
            ))


def _n(v, default=0):
    """Helper: coerce to number."""
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default
