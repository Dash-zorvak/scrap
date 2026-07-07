"""Periodos del dashboard: una sola fuente para el rango de fechas activo.

Antes cada bloque interpretaba el periodo a su manera (o lo ignoraba). Aqui se
define la lista oficial de periodos y una funcion unica que traduce el periodo
elegido a un rango [inicio, fin] concreto. Todos los bloques deben filtrar sus
datos con ESTE rango para que los numeros coincidan entre si.

Los periodos relativos se anclan a la fecha mas reciente con datos (no al reloj
del servidor), para que la ventana muestre siempre informacion y nunca aparezca
vacia por falta de actualizacion. Se usan ventanas moviles (p. ej. "Esta
semana" = los ultimos 7 dias con datos) porque las ventanas de calendario muy
cortas dejaban tramos sin comentarios y arruinaban los porcentajes.
"""

import logging
import os
from datetime import datetime, timedelta

import pandas as pd

logger = logging.getLogger(__name__)

_CORTE_RAW = os.environ.get("DASHBOARD_FECHA_CORTE_MINIMA", "2020-01-01")
try:
    DASHBOARD_FECHA_CORTE_MINIMA = datetime.strptime(_CORTE_RAW, "%Y-%m-%d")
except (ValueError, TypeError):
    DASHBOARD_FECHA_CORTE_MINIMA = datetime(2020, 1, 1, 0, 0, 0)
    logger.warning("DASHBOARD_FECHA_CORTE_MINIMA inválida '%s', usando 2020-01-01", _CORTE_RAW)

# Opciones oficiales (mismas que el panel usaba originalmente).
OPCIONES_PERIODO = [
    "Esta semana",
    "Ultimos 15 dias",
    "Ultimo mes",
    "Ultimos 3 meses",
    "Todo el periodo",
]

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

    `fecha_ref` es la fecha mas reciente con datos; ancla las ventanas
    moviles. Si no se pasa, se usa la fecha actual.
    """
    if fecha_ref is None:
        fecha_ref = datetime.now()
    fecha_ref = pd.Timestamp(fecha_ref).to_pydatetime()
    ref = fecha_ref.date()
    fin = _fin_dia(ref)

    if periodo == "Esta semana":
        return _inicio_dia(ref - timedelta(days=6)), fin
    if periodo == "Ultimos 15 dias":
        return _inicio_dia(ref - timedelta(days=14)), fin
    if periodo == "Ultimo mes":
        return _inicio_dia(ref - timedelta(days=29)), fin
    if periodo == "Ultimos 3 meses":
        return _inicio_dia(ref - timedelta(days=89)), fin
    if periodo == "Todo el periodo":
        return DASHBOARD_FECHA_CORTE_MINIMA, fin

    # --- Compatibilidad con nombres antiguos (no se muestran en el panel) ---
    if periodo == "Hoy":
        return _inicio_dia(ref), fin
    if periodo == "Ayer":
        ayer = ref - timedelta(days=1)
        return _inicio_dia(ayer), _fin_dia(ayer)
    if periodo == "Este mes":
        return _inicio_dia(ref.replace(day=1)), fin
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
    return DASHBOARD_FECHA_CORTE_MINIMA, fin


def filtrar_por_fecha(df, col, inicio, fin):
    """Filtra un DataFrame por una columna de fecha al rango [inicio, fin]."""
    if df is None or len(df) == 0 or col not in df.columns:
        return pd.DataFrame()
    fechas = pd.to_datetime(df[col], errors="coerce")
    mask = (fechas >= pd.Timestamp(inicio)) & (fechas <= pd.Timestamp(fin))
    return df[mask].copy()
