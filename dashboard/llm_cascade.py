"""Cascada de verificación cruzada para clasificación de temas.

Idea: un modelo primario potente (p. ej. DeepSeek V3.2) clasifica TODOS los
comentarios. Solo los casos difíciles —baja confianza o tono sarcástico, donde
los modelos suelen equivocarse— se re-evalúan con un segundo modelo potente y
distinto (p. ej. GLM 5.1). Luego se reconcilia:

  - Si ambos coinciden en la categoría  -> alta confianza (acuerdo).
  - Si difieren                         -> se degrada la confianza y se marca el
                                          desacuerdo, de modo que el dashboard lo
                                          trate como "dudoso" en vez de asignar
                                          un tema con poca certeza.

Este módulo es PURO: no llama a ninguna API. Recibe una función clasificadora
inyectada `clasificar_fn(textos, model=None) -> list[dict]`, lo que lo hace
fácil de probar sin red.

Cada dict de entrada/salida sigue el formato de topic_llm:
  {"categoria", "tono", "confianza", "motor", ...}
La reconciliación añade campos extra no destructivos: "verificado" (bool),
"acuerdo" (bool), "categoria_primario", "categoria_verificador".
"""

import os

# Por debajo de esta confianza, el resultado primario se re-verifica.
UMBRAL_VERIFICAR = float(os.environ.get("LLM_CASCADA_UMBRAL", "0.75"))

# Confianza máxima que se asigna cuando los dos modelos NO coinciden. Debe quedar
# por debajo del umbral de "dudoso" del dashboard (TEMAS_UMBRAL_DUDOSO, 0.55 por
# defecto) para que un desacuerdo se trate efectivamente como dudoso.
CONFIANZA_DESACUERDO = float(os.environ.get("LLM_CASCADA_CONF_DESACUERDO", "0.4"))


def debe_verificar(resultado, umbral=None):
    """Decide si un resultado primario necesita segunda opinión."""
    if not isinstance(resultado, dict):
        return False
    u = UMBRAL_VERIFICAR if umbral is None else umbral
    # El sarcasmo es la principal fuente de error: siempre se re-verifica.
    if resultado.get("tono") == "sarcastico":
        return True
    try:
        conf = float(resultado.get("confianza", 0.0))
    except (TypeError, ValueError):
        conf = 0.0
    return conf < u


def reconciliar(primario, verificador):
    """Combina el resultado primario con el del verificador.

    La categoría efectiva siempre es la del primario; la del verificador se
    conserva como referencia. Acuerdo refuerza la confianza; desacuerdo la
    degrada (-> dudoso).
    """
    if not isinstance(primario, dict):
        return primario
    if not isinstance(verificador, dict):
        return primario

    base = dict(primario)
    cat_p = primario.get("categoria")
    cat_v = verificador.get("categoria")

    # Tono: si cualquiera detecta sarcasmo, gana sarcasmo (criterio sensible).
    if "sarcastico" in (primario.get("tono"), verificador.get("tono")):
        tono = "sarcastico"
    else:
        tono = "literal"

    try:
        conf_p = float(primario.get("confianza", 0.0))
    except (TypeError, ValueError):
        conf_p = 0.0
    try:
        conf_v = float(verificador.get("confianza", 0.0))
    except (TypeError, ValueError):
        conf_v = 0.0

    if cat_p == cat_v:
        conf = min(0.99, max(conf_p, conf_v) + 0.1)
        acuerdo = True
    else:
        conf = CONFIANZA_DESACUERDO
        if conf_p and conf_v:
            conf = min(CONFIANZA_DESACUERDO, conf_p, conf_v)
        acuerdo = False

    base.update({
        "categoria": cat_p,
        "tono": tono,
        "confianza": round(conf, 3),
        "verificado": True,
        "acuerdo": acuerdo,
        "categoria_primario": cat_p,
        "categoria_verificador": cat_v,
    })
    return base


def clasificar_con_cascada(textos, clasificar_fn, umbral=None, verificador_model=None):
    """Clasifica con cascada primario -> verificador.

    `clasificar_fn(textos, model=None) -> list[dict]` debe devolver una lista
    alineada 1 a 1 con `textos`. El primario se invoca con model=None; el
    verificador con model=verificador_model y solo sobre los casos dudosos.
    """
    if not textos:
        return []
    primarios = clasificar_fn(textos, model=None)
    if not verificador_model:
        return primarios

    indices = [i for i, r in enumerate(primarios) if debe_verificar(r, umbral)]
    if not indices:
        return primarios

    sub_textos = [textos[i] for i in indices]
    try:
        verificados = clasificar_fn(sub_textos, model=verificador_model)
    except Exception:
        # Si el verificador falla, se conserva el resultado primario.
        return primarios

    salida = list(primarios)
    for k, i in enumerate(indices):
        if k < len(verificados):
            salida[i] = reconciliar(primarios[i], verificados[k])
    return salida
