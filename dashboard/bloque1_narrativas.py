# -*- coding: utf-8 -*-
"""Generadores de narrativa para bloque1 (Pulso General) que insertan la
formula DENTRO del texto explicativo, con los numeros reales sustituidos.

Observacion del usuario que este modulo resuelve: no basta con mostrar
"Formula: NSI = (positivos - negativos) / total * 100" como dato aparte; la
formula debe explicarse en la oracion, con los numeros reales de ese periodo
sustituidos, tal como en el ejemplo:

    "El clima publico medido en comentarios con sentimiento disponible se
    inclina hacia la critica: 135 de 354 comentarios fueron criticos, frente
    a 86 favorables y 133 neutrales. Esto deja una diferencia negativa de
    13.84 puntos... Basado en el calculo de positivas menos las negativas
    (86-135) entre el total de los comentarios, que son 354, nos muestra que
    el resultado es -0.13 puntos negativo".

Cada funcion de aqui devuelve un dict con, al menos, las claves "narrativa"
(el texto final que va a bloque1.<seccion>.narrativa) y "explicacion_simple".
El campo "formula_usada" se conserva por trazabilidad, pero el usuario ya no
depende de leerlo aparte: la formula ya viene explicada en "narrativa".

Estas funciones son puras (no acceden a la base de datos ni a Streamlit): se
les pasan los agregados ya calculados (conteos, promedios, porcentajes) y
devuelven texto. Se conectan en el script que construye data/analysis.json,
justo donde hoy se asigna bloque1["clima_narrativo"]["narrativa"] = "..." etc.
"""

from __future__ import annotations

from typing import Dict, List, Optional


def _fmt(n, decimales=0):
    if n is None:
        return "s/d"
    if decimales == 0:
        return f"{n:,.0f}"
    return f"{n:,.{decimales}f}"


# ---------------------------------------------------------------------------
# 01 - CLIMA NARRATIVO
# ---------------------------------------------------------------------------

def narrativa_clima_narrativo(n_favorable: int, n_neutral: int, n_critico: int,
                               tendencia: Optional[float] = None,
                               periodo_label: str = "") -> Dict[str, str]:
    n_total = n_favorable + n_neutral + n_critico
    if n_total == 0:
        return {
            "narrativa": "No hay comentarios con sentimiento disponible en este periodo para calcular el clima narrativo.",
            "explicacion_simple": "Sin datos suficientes.",
            "formula_usada": "NSI = (favorables - criticos) / total * 100",
        }

    diferencia_puntos = (n_favorable - n_critico) / n_total * 100
    score = round((n_favorable - n_critico) / n_total, 2)

    if n_favorable > n_critico:
        tono_dominante, inclinacion = "favorable", "la aprobacion"
    elif n_critico > n_favorable:
        tono_dominante, inclinacion = "critico", "la critica"
    else:
        tono_dominante, inclinacion = "neutral", "un empate entre apoyo y critica"

    signo_txt = "negativa" if diferencia_puntos < 0 else ("positiva" if diferencia_puntos > 0 else "nula")

    if tono_dominante == "critico":
        cuerpo = (
            f"El clima publico medido en comentarios con sentimiento disponible se inclina hacia la critica: "
            f"{n_critico:,} de {n_total:,} comentarios fueron criticos, frente a {n_favorable:,} favorables y "
            f"{n_neutral:,} neutrales. Esto deja una diferencia {signo_txt} de {abs(diferencia_puntos):.2f} puntos "
            f"y muestra una conversacion donde la aprobacion no desaparece, pero queda por debajo del volumen de "
            f"objeciones publicas."
        )
    elif tono_dominante == "favorable":
        cuerpo = (
            f"El clima publico medido en comentarios con sentimiento disponible se inclina hacia la aprobacion: "
            f"{n_favorable:,} de {n_total:,} comentarios fueron favorables, frente a {n_critico:,} criticos y "
            f"{n_neutral:,} neutrales. Esto deja una diferencia {signo_txt} de {abs(diferencia_puntos):.2f} puntos "
            f"y muestra una conversacion donde la critica esta presente, pero por debajo del volumen de apoyo."
        )
    else:
        cuerpo = (
            f"El clima publico medido en comentarios con sentimiento disponible esta parejo: {n_favorable:,} "
            f"favorables y {n_critico:,} criticos, sobre {n_total:,} comentarios totales ({n_neutral:,} neutrales). "
            f"La diferencia es de solo {abs(diferencia_puntos):.2f} puntos, es decir, no hay un bando dominante."
        )

    formula_explicada = (
        f" Basado en el calculo de favorables menos criticos ({n_favorable:,}-{n_critico:,}) entre el total de "
        f"comentarios, que son {n_total:,}, el resultado es {score:+.2f} puntos ({'negativo' if score < 0 else 'positivo' if score > 0 else 'neutro'}), "
        f"lo que en la escala de -1 (todo critico) a +1 (todo favorable) confirma que la conversacion se inclina hacia {inclinacion}."
    )

    tendencia_txt = ""
    if tendencia is not None:
        if tendencia > 0.1:
            tendencia_txt = f" Frente al periodo anterior, el tono mejoro (tendencia {tendencia:+.2f})."
        elif tendencia < -0.1:
            tendencia_txt = f" Frente al periodo anterior, el tono empeoro (tendencia {tendencia:+.2f})."
        else:
            tendencia_txt = f" Frente al periodo anterior, el tono se mantuvo estable (tendencia {tendencia:+.2f})."

    narrativa = cuerpo + formula_explicada + tendencia_txt

    explicacion_simple = (
        f"De cada {n_total:,} comentarios con sentimiento identificado, {n_favorable:,} apoyan, {n_critico:,} "
        f"critican y {n_neutral:,} son neutrales. El numero final ({score:+.2f}) es simplemente cuantos mas "
        f"criticaron que apoyaron, dividido entre el total: mientras mas cercano a -1, mas domina la critica; "
        f"mientras mas cercano a +1, mas domina el apoyo."
    )

    return {
        "narrativa": narrativa,
        "explicacion_simple": explicacion_simple,
        "tono_dominante": tono_dominante,
        "tono_score_hoy": score,
        "formula_usada": "NSI = (favorables - criticos) / total * 100",
    }


# ---------------------------------------------------------------------------
# 02 - INDICE DE EMOCIONES
# ---------------------------------------------------------------------------

def narrativa_indice_emociones(conteos: Dict[str, int], labels: Dict[str, str]) -> Dict[str, object]:
    """conteos: {clave_emocion: n_comentarios}. labels: {clave_emocion: "Nombre"}."""
    total = sum(conteos.values())
    if total == 0:
        return {
            "narrativa": "No hay comentarios clasificados por emocion en este periodo.",
            "emocion_dominante": "",
            "pcts": {},
            "formula_usada": "% emocion = (n_emocion / total_comentarios) * 100",
        }

    pcts = {k: round(v / total * 100, 1) for k, v in conteos.items()}
    dominante = max(conteos, key=lambda k: conteos[k])
    n_dom = conteos[dominante]
    pct_dom = pcts[dominante]
    label_dom = labels.get(dominante, dominante)

    # Segunda emocion mas frecuente, para dar contraste real (no inventado).
    resto = {k: v for k, v in conteos.items() if k != dominante}
    segunda = max(resto, key=lambda k: resto[k]) if resto else None

    narrativa = (
        f"La emocion que domina la conversacion es {label_dom.lower()}, presente en {n_dom:,} de {total:,} "
        f"comentarios clasificados por emocion ({pct_dom:.1f}%). "
        f"Basado en el calculo del numero de comentarios con esa emocion entre el total clasificado "
        f"({n_dom:,} / {total:,}) por 100, el resultado es {pct_dom:.1f}%."
    )
    if segunda:
        n_seg = conteos[segunda]
        pct_seg = pcts[segunda]
        label_seg = labels.get(segunda, segunda)
        narrativa += (
            f" La segunda emocion mas frecuente es {label_seg.lower()}, con {n_seg:,} comentarios ({pct_seg:.1f}%), "
            f"lo que muestra que la conversacion no es emocionalmente uniforme."
        )

    return {
        "narrativa": narrativa,
        "emocion_dominante": dominante,
        "pcts": pcts,
        "formula_usada": "% emocion = (n_emocion / total_comentarios_clasificados) * 100",
    }


def narrativa_emocion_seleccionada(clave_emocion: str, conteos: Dict[str, int], labels: Dict[str, str]) -> str:
    """Texto que acompana la grafica cuando el usuario selecciona UNA emocion
    especifica en el selector (ver snippet de UI en app_bloque1_snippets.py).
    """
    total = sum(conteos.values())
    n = conteos.get(clave_emocion, 0)
    pct = round(n / total * 100, 1) if total else 0
    label = labels.get(clave_emocion, clave_emocion)
    dominante = max(conteos, key=lambda k: conteos[k]) if conteos else None
    es_dominante = dominante == clave_emocion
    frase_dominancia = (
        f"Esta es, ademas, la emocion mas frecuente de todo el periodo."
        if es_dominante else
        f"La emocion mas frecuente del periodo es {labels.get(dominante, dominante).lower() if dominante else 's/d'} "
        f"({conteos.get(dominante, 0):,} comentarios)."
    )
    return (
        f"{label} aparece en {n:,} de {total:,} comentarios clasificados por emocion ({pct:.1f}%). "
        f"{frase_dominancia}"
    )


# ---------------------------------------------------------------------------
# 03 - INTENSIDAD DE LA CONVERSACION
# ---------------------------------------------------------------------------

def narrativa_intensidad(vol_hoy: float, promedio_semanal: float, n_dias_referencia: int,
                          plataforma_label: str, periodo_label: str) -> Dict[str, str]:
    """plataforma_label: p.ej. 'Facebook y TikTok de la Alcaldia de Santa Ana'.
    periodo_label: p.ej. 'la ultima semana' / 'el 8 de julio de 2026'.
    """
    if promedio_semanal <= 0:
        return {
            "narrativa": f"No hay suficiente historial de {n_dias_referencia} dias para calcular un promedio de referencia.",
            "formula_usada": "delta_pct = ((vol_hoy - promedio) / promedio) * 100",
        }

    delta_pct = (vol_hoy - promedio_semanal) / promedio_semanal * 100
    diferencia_abs = vol_hoy - promedio_semanal

    if delta_pct > 15:
        etiqueta, direccion, lectura = "alta", "mas alta", (
            "lo que significa que mas gente esta reaccionando, comentando o compartiendo de lo habitual: "
            "la conversacion se aceleró y conviene revisar de que estan hablando."
        )
    elif delta_pct < -15:
        etiqueta, direccion, lectura = "baja", "mas baja", (
            "lo que significa que la gente esta viendo el contenido pero respondiendo menos que lo habitual: "
            "hay menos comentarios, reacciones y compartidos que en un dia/periodo normal, no que haya menos publicaciones."
        )
    else:
        etiqueta, direccion, lectura = "estable", "en linea con", (
            "lo que significa que el nivel de interaccion se mantiene dentro del comportamiento habitual de la cuenta."
        )

    narrativa = (
        f"La intensidad mide el volumen de interacciones (reacciones + comentarios + compartidos) que recibio "
        f"{plataforma_label} durante {periodo_label}, comparado con su propio promedio de los ultimos {n_dias_referencia} dias. "
        f"Hoy se registraron {vol_hoy:,.0f} interacciones, frente a un promedio habitual de {promedio_semanal:,.0f}; "
        f"eso es {abs(diferencia_abs):,.0f} interacciones {direccion} lo normal. "
        f"Basado en el calculo de (hoy - promedio) entre el promedio ({vol_hoy:,.0f} - {promedio_semanal:,.0f}) / {promedio_semanal:,.0f}, "
        f"multiplicado por 100, el resultado es {delta_pct:+.1f}%, es decir, intensidad {etiqueta}. "
        f"En terminos simples: {lectura}"
    )

    return {
        "narrativa": narrativa,
        "pct_diferencia": round(delta_pct, 1),
        "etiqueta": etiqueta,
        "formula_usada": "delta_pct = ((vol_hoy - promedio) / promedio) * 100",
    }


# ---------------------------------------------------------------------------
# 04 - CONCENTRACION TEMATICA (card unica y consolidada)
# ---------------------------------------------------------------------------

def narrativa_concentracion_tematica(ramas: List[Dict], n_total_clasificados: int) -> Dict[str, object]:
    """ramas: lista de dicts con al menos:
        {"tema": str, "n": int, "pct_critica": float, "pct_apoyo": float,
         "pct_cambio_semana": float, "acelerando": bool}
    Devuelve una sola narrativa consolidada (sustituye las 2-3 cards sueltas).
    """
    if not ramas or n_total_clasificados == 0:
        return {"narrativa": "No hay comentarios clasificados por tema en este periodo.", "hhi": 0}

    shares = [r["n"] / n_total_clasificados for r in ramas]
    hhi = sum(s ** 2 for s in shares)

    ramas_ordenadas = sorted(ramas, key=lambda r: r["n"], reverse=True)
    top = ramas_ordenadas[0]
    top_share = top["n"] / n_total_clasificados * 100

    acelerando = [r for r in ramas if r.get("acelerando")]
    desacelerando = [r for r in ramas if r.get("pct_cambio_semana", 0) < 0 and not r.get("acelerando")]

    if hhi > 0.35:
        nivel_txt = "dominada por un solo tema"
    elif hhi > 0.2:
        nivel_txt = "liderada por un tema, pero con varios temas activos"
    else:
        nivel_txt = "repartida entre varios temas sin un dominante claro"

    partes = [
        f"La conversacion clasificada esta {nivel_txt}: el tema \"{top['tema']}\" reune {top['n']:,} de "
        f"{n_total_clasificados:,} comentarios clasificados, equivalente al {top_share:.2f}%."
    ]

    friccion_desc = []
    for r in ramas_ordenadas:
        if r.get("pct_critica", 0) >= 30:
            friccion_desc.append(f"{r['tema']} ({r['n']:,} comentarios, {r['pct_critica']:.0f}% criticos)")
    if friccion_desc:
        partes.append("Las fricciones mas claras aparecen en " + "; ".join(friccion_desc) + ".")

    if acelerando:
        det = ", ".join(f"{r['tema']} (+{r.get('pct_cambio_semana', 0):.0f}% vs. la semana anterior, "
                          f"{r['n']:,} comentarios)" for r in acelerando)
        partes.append(f"Temas que estan acelerando: {det}.")
    else:
        partes.append("Ningun tema muestra una aceleracion clara frente a la semana anterior.")

    if desacelerando:
        det = ", ".join(f"{r['tema']} ({r.get('pct_cambio_semana', 0):.0f}% vs. la semana anterior, "
                          f"{r['n']:,} comentarios)" for r in desacelerando)
        partes.append(f"Temas que estan desacelerando: {det}.")
    else:
        partes.append("Ningun tema muestra una desaceleracion clara frente a la semana anterior.")

    partes.append(
        f"Basado en el indice de concentracion (HHI = suma de cada participacion al cuadrado; en este periodo "
        f"{' + '.join(f'{s:.2f}^2' for s in shares[:4])}{'...' if len(shares) > 4 else ''}), el resultado es "
        f"HHI={hhi:.2f} (0 = totalmente repartido, 1 = un solo tema concentra todo)."
    )

    return {
        "narrativa": " ".join(partes),
        "hhi": round(hhi, 3),
        "top_tema": top["tema"],
        "temas_acelerando": [r["tema"] for r in acelerando],
        "temas_desacelerando": [r["tema"] for r in desacelerando],
        "formula_usada": "HHI = sum(share_i^2) donde share_i = n_tema_i / total_clasificados",
    }


# ---------------------------------------------------------------------------
# 05 - METRICAS DE RENDIMIENTO
# ---------------------------------------------------------------------------

def narrativa_metricas_rendimiento(reacciones_positivas: int, reacciones_negativas: int,
                                    comentarios: int, compartidos: int,
                                    impresiones_o_vistas: Optional[int],
                                    total_posts: int,
                                    enlaces_referencia: List[str]) -> Dict[str, object]:
    interacciones = reacciones_positivas + reacciones_negativas + comentarios + compartidos

    if impresiones_o_vistas and impresiones_o_vistas > 0:
        engagement_rate = round(interacciones / impresiones_o_vistas * 100, 2)
        base_engagement = f"sobre {impresiones_o_vistas:,} impresiones/vistas registradas"
        formula_er = (
            f"ER = (reacciones + comentarios + compartidos) / impresiones * 100 = "
            f"({reacciones_positivas + reacciones_negativas:,} + {comentarios:,} + {compartidos:,}) / "
            f"{impresiones_o_vistas:,} * 100 = {engagement_rate:.2f}%"
        )
    else:
        engagement_rate = round(interacciones / max(total_posts, 1), 2)
        base_engagement = f"como interacciones promedio por publicacion, porque no hay impresiones reales para este periodo ({total_posts:,} publicaciones)"
        formula_er = (
            f"ER = (reacciones + comentarios + compartidos) / numero_de_publicaciones = "
            f"({reacciones_positivas + reacciones_negativas:,} + {comentarios:,} + {compartidos:,}) / {total_posts:,} = {engagement_rate:.2f}"
        )

    ratio_amor_enojo = round(reacciones_positivas / max(reacciones_negativas, 1), 2) if reacciones_negativas else None

    partes = [
        f"El engagement rate mide que porcentaje de quienes vieron el contenido interactuaron con el, calculado "
        f"{base_engagement}. {formula_er}."
    ]

    if ratio_amor_enojo is not None:
        partes.append(
            f"El ratio amor/enojo compara reacciones positivas ({reacciones_positivas:,}: me gusta + me encanta + "
            f"me importa) contra reacciones negativas ({reacciones_negativas:,}: me enoja + me entristece + me divierte, "
            f"esta ultima porque en publicaciones oficiales suele ser burla). Formula: R = positivas / negativas = "
            f"{reacciones_positivas:,} / {reacciones_negativas:,} = {ratio_amor_enojo:.2f}. Un ratio mayor a 1 indica "
            f"que las reacciones de afecto superan a las de rechazo."
        )
    else:
        partes.append(
            f"No se registraron reacciones negativas en este periodo ({reacciones_positivas:,} positivas / 0 negativas), "
            f"por lo que el ratio amor/enojo no es calculable de forma significativa (division por cero); se reporta "
            f"como dato informativo, no como certeza de ausencia total de enojo."
        )

    partes.append(
        f"Reacciones +/-: {reacciones_positivas:,} positivas y {reacciones_negativas:,} negativas, sobre "
        f"{reacciones_positivas + reacciones_negativas:,} reacciones totales registradas en las publicaciones del periodo."
    )

    if enlaces_referencia:
        partes.append(
            f"Estos numeros provienen de {total_posts:,} publicaciones concretas del periodo; ver enlaces de referencia "
            f"({len(enlaces_referencia)} publicaciones citadas) para verificar cada cifra en su fuente original."
        )
    else:
        partes.append(
            "Nota de trazabilidad pendiente: agregar los enlaces de las publicaciones que componen esta suma para "
            "que cada cifra pueda verificarse en su fuente."
        )

    return {
        "narrativa": " ".join(partes),
        "engagement_rate": engagement_rate,
        "ratio_amor_enojo": ratio_amor_enojo,
        "formula_usada": formula_er,
    }


# ---------------------------------------------------------------------------
# 06 - TERMOMETRO DE ZONAS
# ---------------------------------------------------------------------------

def narrativa_termometro_zona(zona: str, n_comentarios: int, pct_apoyo: float, pct_critica: float,
                               pct_objecion: float, tema_dominante: str,
                               citas_ejemplo: List[str], enlaces_referencia: List[str]) -> Dict[str, str]:
    score_zona = round((pct_apoyo - pct_critica - pct_objecion) / 100, 3)

    if score_zona > 0.15:
        nivel = "bajo"
    elif score_zona < -0.15:
        nivel = "alto"
    else:
        nivel = "medio"

    narrativa = (
        f"Esto mide el tono de los comentarios que mencionan explicitamente la zona \"{zona}\": de "
        f"{n_comentarios:,} comentarios georreferenciados a esta zona, {pct_apoyo:.0f}% son de apoyo, "
        f"{pct_critica:.0f}% son criticos y {pct_objecion:.0f}% son objeciones, sobre el tema \"{tema_dominante}\". "
        f"Basado en el calculo de apoyo menos critica menos objecion, entre 100 "
        f"({pct_apoyo:.0f} - {pct_critica:.0f} - {pct_objecion:.0f}) / 100, el resultado es {score_zona:+.3f}, "
        f"lo que ubica a esta zona en nivel de tension {nivel}."
    )

    if citas_ejemplo:
        narrativa += (
            f" Cita representativa de esta zona: \"{citas_ejemplo[0][:180]}\"."
        )
    if enlaces_referencia:
        narrativa += f" Basado en {len(enlaces_referencia)} publicaciones con comentarios geolocalizados en esta zona."
    else:
        narrativa += " Nota: faltan enlaces de referencia de las publicaciones que originan estos comentarios."

    return {
        "narrativa": narrativa,
        "score_zona": score_zona,
        "nivel_tension": nivel,
        "formula_usada": "score_zona = (pct_apoyo - pct_critica - pct_objecion) / 100",
    }


# ---------------------------------------------------------------------------
# PULSO EN UN NUMERO (pulso_iq)
# ---------------------------------------------------------------------------

DIMENSION_WEIGHTS = {
    "aprobacion": 1.0, "conexion": 1.0, "tranquilidad": 1.0,
    "diversidad_temas": 0.8, "presencia_zonas": 0.7,
    "consistencia": 0.9, "atencion": 0.6,
}

DIMENSION_LABELS = {
    "aprobacion": "aprobacion ciudadana (sentimiento neto)",
    "conexion": "conexion con la gente (engagement)",
    "tranquilidad": "tranquilidad (ausencia de enojo/friccion)",
    "diversidad_temas": "diversidad de temas gestionados",
    "presencia_zonas": "presencia territorial (cobertura de zonas)",
    "consistencia": "consistencia de publicacion",
    "atencion": "capacidad de generar conversacion",
}


def narrativa_pulso_iq(componentes: Dict[str, float], pct_critico: float, hhi: float,
                        interacciones_totales: int, impresiones_o_vistas: int) -> Dict[str, object]:
    suma_pesos = sum(DIMENSION_WEIGHTS.values())
    suma_ponderada = sum(componentes.get(k, 0) * w for k, w in DIMENSION_WEIGHTS.items())
    iq = round(suma_ponderada / suma_pesos, 1)

    detalle = "; ".join(
        f"{DIMENSION_LABELS[k]} = {componentes.get(k, 0):.1f} (peso {w})"
        for k, w in DIMENSION_WEIGHTS.items()
    )

    narrativa = (
        f"El pulso integrado queda en {iq:.1f} puntos porque combina, con distinto peso, "
        f"{len(DIMENSION_WEIGHTS)} componentes: {detalle}. "
        f"Formula: IQ = suma(componente_i * peso_i) / suma(peso_i) = {suma_ponderada:.1f} / {suma_pesos:.1f} = {iq:.1f}. "
        f"Como referencia cruzada con los otros bloques: la conversacion tuvo {pct_critico:.2f}% de comentarios criticos, "
        f"una concentracion tematica de HHI={hhi:.2f}, y {interacciones_totales:,} interacciones totales frente a "
        f"{impresiones_o_vistas:,} vistas/impresiones registradas en el periodo."
    )

    return {
        "narrativa": narrativa,
        "valor": iq,
        "componentes_detalle": componentes,
        "formula_usada": (
            "IQ = (aprobacion*1.0 + conexion*1.0 + tranquilidad*1.0 + diversidad*0.8 + presencia*0.7 "
            "+ consistencia*0.9 + atencion*0.6) / suma_pesos"
        ),
    }
