"""Bloque I - Pulso general: calculos puros (sin Streamlit ni IO).

Cada funcion recibe DataFrames o estructuras ya cargadas y devuelve un dict
listo para renderizar. Al no depender de Streamlit ni de la base de datos, son
unidades testeables por CI.

Indices que alimentan:
  - Clima Narrativo: tono dominante del dia + tendencia vs el dia anterior.
  - Intensidad: volumen de interaccion del ultimo dia vs el promedio diario
    de la semana.
  - Concentracion tematica: proporcion del tema principal vs el resto.
"""

import pandas as pd


def calcular_clima_diario(df_sent):
    """Tono ciudadano del ultimo dia con datos y su tendencia vs el dia previo.

    df_sent: columnas pct_positivo, pct_negativo, total_comentarios, created_time
    (una fila por publicacion). El sentimiento de cada publicacion se pondera
    por su volumen de comentarios y se agrega al dia de la publicacion.

    Devuelve dict con porcentajes favorable/neutro/adverso del ultimo dia, la
    variacion en puntos de lo favorable frente al dia anterior, el conteo de
    comentarios y el numero de dias observados. None si no hay datos.
    """
    if df_sent is None or len(df_sent) == 0:
        return None
    df = df_sent.copy()
    if "created_time" not in df.columns:
        return None
    df["created_time"] = pd.to_datetime(df["created_time"], errors="coerce")
    df = df.dropna(subset=["created_time"])
    for c in ["pct_positivo", "pct_negativo", "total_comentarios"]:
        df[c] = pd.to_numeric(df.get(c), errors="coerce").fillna(0)
    df = df[df["total_comentarios"] > 0]
    if df.empty:
        return None
    df["fecha"] = df["created_time"].dt.normalize()
    df["w_pos"] = df["pct_positivo"] * df["total_comentarios"]
    df["w_neg"] = df["pct_negativo"] * df["total_comentarios"]
    g = (
        df.groupby("fecha")
        .agg(w_pos=("w_pos", "sum"), w_neg=("w_neg", "sum"), n=("total_comentarios", "sum"))
        .reset_index()
        .sort_values("fecha")
    )
    g = g[g["n"] > 0]
    if g.empty:
        return None
    g["fav"] = (g["w_pos"] / g["n"]).clip(0, 100)
    g["adv"] = (g["w_neg"] / g["n"]).clip(0, 100)
    g["neu"] = (100 - g["fav"] - g["adv"]).clip(lower=0)
    ult = g.iloc[-1]
    delta = float(ult["fav"] - g.iloc[-2]["fav"]) if len(g) >= 2 else None
    return {
        "fecha": ult["fecha"].date().isoformat(),
        "pct_favorable": round(float(ult["fav"]), 1),
        "pct_neutro": round(float(ult["neu"]), 1),
        "pct_adverso": round(float(ult["adv"]), 1),
        "delta_favorable": round(delta, 1) if delta is not None else None,
        "n_comentarios": int(ult["n"]),
        "n_dias": int(len(g)),
    }


def calcular_intensidad_vs_promedio(df_fb, df_tk):
    """Volumen de interaccion del ultimo dia con datos vs el promedio diario
    de los 7 dias previos. Devuelve None si no hay al menos un dia previo.
    """
    frames = []
    if (
        df_fb is not None and len(df_fb) > 0
        and "created_time" in df_fb.columns and "engagement_total" in df_fb.columns
    ):
        frames.append(pd.DataFrame({
            "fecha": pd.to_datetime(df_fb["created_time"], errors="coerce").dt.normalize(),
            "eng": pd.to_numeric(df_fb["engagement_total"], errors="coerce"),
        }))
    if (
        df_tk is not None and len(df_tk) > 0
        and "created_at" in df_tk.columns and "engagement_total" in df_tk.columns
    ):
        frames.append(pd.DataFrame({
            "fecha": pd.to_datetime(df_tk["created_at"], errors="coerce").dt.normalize(),
            "eng": pd.to_numeric(df_tk["engagement_total"], errors="coerce"),
        }))
    if not frames:
        return None
    alld = pd.concat(frames, ignore_index=True).dropna(subset=["fecha"])
    if alld.empty:
        return None
    alld["eng"] = alld["eng"].fillna(0)
    diario = alld.groupby("fecha")["eng"].sum().sort_index()
    if len(diario) == 0:
        return None
    vol_hoy = float(diario.iloc[-1])
    previos = diario.iloc[:-1].tail(7)
    if len(previos) == 0:
        return None
    promedio = float(previos.mean())
    ratio = vol_hoy / promedio if promedio > 0 else 1.0
    return {
        "fecha_hoy": diario.index[-1].date().isoformat(),
        "vol_hoy": vol_hoy,
        "promedio": promedio,
        "ratio": ratio,
        "pct_dif": (ratio - 1) * 100,
        "n_ref": int(len(previos)),
    }


def calcular_concentracion(conteo):
    """Proporcion del tema principal vs el resto, con el desglose completo.

    conteo: dict o pd.Series de categoria -> conteo. Devuelve share del tema
    principal, share del resto, HHI (0-1), numero de temas, un estado
    (dominado / liderado / fragmentado) y `ramas`: la lista COMPLETA de temas
    con su conteo y proporcion (ordenada de mayor a menor), para no dejar el
    resto agrupado como una sola barra opaca. None si no hay datos.
    """
    if conteo is None:
        return None
    s = pd.Series(conteo, dtype="float64")
    s = s[s > 0].sort_values(ascending=False)
    if s.empty:
        return None
    total = float(s.sum())
    top_tema = str(s.index[0])
    share_top = float(s.iloc[0] / total * 100)
    hhi = float(sum((c / total * 100) ** 2 for c in s) / 10000)
    ramas = [
        {
            "tema": str(idx),
            "n": int(round(float(val))),
            "share": round(float(val / total * 100), 1),
        }
        for idx, val in s.items()
    ]
    if share_top >= 50:
        estado, nivel = f"Dominado por \u00ab{top_tema}\u00bb", "dominado"
    elif share_top >= 33:
        estado, nivel = f"Liderado por \u00ab{top_tema}\u00bb, sin dominar", "liderado"
    else:
        estado, nivel = "Conversaci\u00f3n fragmentada en varios temas", "fragmentado"
    return {
        "top_tema": top_tema,
        "share_top": round(share_top, 1),
        "share_resto": round(100 - share_top, 1),
        "hhi": round(hhi, 2),
        "n_temas": int(len(s)),
        "ramas": ramas,
        "estado": estado,
        "nivel": nivel,
    }
