"""Periodos del dashboard: una sola fuente para el rango de fechas activo.

Antes cada bloque interpretaba el periodo a su manera (o lo ignoraba). Aqui se
define la lista oficial de periodos y una funcion unica que traduce el periodo
elegido a un rango [inicio, fin] concreto. Todos los bloques deben filtrar sus
datos con ESTE rango para que los numeros coincidan entre si.

Los periodos relativos se anclan a la fecha mas reciente con datos (no al reloj
del servidor), para que "Hoy" muestre el ultimo dia con informacion y nunca
aparezca vacio por falta de actualizacion.
"""

from datetime import datetime, timedelta

import pandas as pd

OPCIONES_PERIODO = ["Hoy", "Ayer", "Esta semana", "Este mes", "Personalizado"]

_MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
    "septiembre", "octubre", "noviembre", "diciembre",
]


def etiqueta_rango(inicio, fin):
    """Texto legible del rango activo para mostrar al usuario."""
    di, dfin = inicio.date(), fin.date()
    if di == dfin:
        return f"{di.day} de {_MESES[di.month - 1]} de {di.year}"
    if di.year == dfin.year and di.month == dfin.month:
        return f"{di.day}-{dfin.day} de {_MESES[di.month - 1]} de {di.year}"
    return (
        f"{di.day} de {_MESES[di.month - 1]} - "
        f"{dfin.day} de {_MESES[dfin.month - 1]} de {dfin.year}"
    )


def _inicio_dia(d):
    return datetime(d.year, d.month, d.day, 0, 0, 0)


def _fin_dia(d):
    return datetime(d.year, d.month, d.day, 23, 59, 59)


def rango_periodo(periodo, fecha_ref=None, fecha_desde=None, fecha_hasta=None):
    """Traduce un periodo a (inicio, fin) como datetimes.

    `fecha_ref` es la fecha mas reciente con datos; ancla los periodos
    relativos. Si no se pasa, se usa la fecha actual.
    """
    if fecha_ref is None:
        fecha_ref = datetime.now()
    fecha_ref = pd.Timestamp(fecha_ref).to_pydatetime()
    ref = fecha_ref.date()

    if periodo == "Hoy":
        return _inicio_dia(ref), _fin_dia(ref)
    if periodo == "Ayer":
        ayer = ref - timedelta(days=1)
        return _inicio_dia(ayer), _fin_dia(ayer)
    if periodo == "Esta semana":
        lunes = ref - timedelta(days=ref.weekday())
        return _inicio_dia(lunes), _fin_dia(ref)
    if periodo == "Este mes":
        primero = ref.replace(day=1)
        return _inicio_dia(primero), _fin_dia(ref)
    if periodo == "Personalizado":
        d = (
            pd.Timestamp(fecha_desde).to_pydatetime().date()
            if fecha_desde else ref.replace(day=1)
        )
        h = (
            pd.Timestamp(fecha_hasta).to_pydatetime().date()
            if fecha_hasta else ref
        )
        if d > h:
            d, h = h, d
        return _inicio_dia(d), _fin_dia(h)
    # Por defecto: todo el historial.
    return datetime(2020, 1, 1, 0, 0, 0), _fin_dia(ref)


def filtrar_por_fecha(df, col, inicio, fin):
    """Filtra un DataFrame por una columna de fecha al rango [inicio, fin]."""
    if df is None or len(df) == 0 or col not in df.columns:
        return df
    fechas = pd.to_datetime(df[col], errors="coerce")
    mask = (fechas >= pd.Timestamp(inicio)) & (fechas <= pd.Timestamp(fin))
    return df[mask].copy()
