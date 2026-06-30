"""Tests de regresión para el rework de textos de las cards del dashboard.

Verifican tres cosas, leyendo los módulos como texto plano (sin Streamlit, sin
base de datos, sin spaCy):
  1. Los subtítulos/captions antiguos quedaron eliminados.
  2. Los textos y helpers nuevos están presentes (cards narrativas y
     referencias renombradas).
  3. Los módulos editados compilan (sin errores de sintaxis).

Son deliberadamente "de archivo": no importan los módulos del dashboard para no
arrastrar dependencias pesadas ni la guarda de base de datos real del conftest.
"""

import os
import py_compile

import pytest

DASH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard")


def _leer(nombre):
    with open(os.path.join(DASH, nombre), encoding="utf-8") as fh:
        return fh.read()


# ── 1. Textos antiguos eliminados ──

TEXTOS_ELIMINADOS = {
    "dash_bloque1.py": [
        "Tono dominante de los comentarios del período seleccionado",
        "Cuánto se mueve la conversación hoy frente a una semana normal",
        "Si la conversación gira en torno a un solo tema o está repartida entre varios",
        "abrí el post para verificar",
    ],
    "dash_bloque2.py": [
        "Composición de la audiencia según el tono de sus comentarios",
        "Si la conversación está en consenso o partida en dos posturas enfrentadas",
        "Páginas oficiales que concentran la mayor interacción",
        "abrí el post para verificar",
    ],
    "dash_bloque3.py": [
        "Qué parte de la conversación es espontánea y qué parte son mensajes idénticos repetidos",
        "Qué tan urgente es responder y a qué temas responder",
        "Hacia dónde va la interacción en las próximas 24 a 48 horas",
        "Es una estimación basada en la tendencia de los últimos días",
        "Los temas que más rechazo generan, con un comentario real de ejemplo",
    ],
    "dash_bloque4.py": [
        "Un resumen estratégico que conecta lo que ocurre hoy con la memoria",
        "Léelo como un briefing",
        "PUBLICACIONES QUE SUSTENTAN EL MEMO",
        "abrí el post para verificar",
    ],
    "dash_temas.py": [
        "Temas englobantes definidos por defecto",
        "El porcentaje es sobre los comentarios que ya aprobaste",
    ],
    "dash_ui.py": [
        "abrí el post para verificar",
    ],
}


@pytest.mark.parametrize("archivo,frases", TEXTOS_ELIMINADOS.items())
def test_textos_eliminados(archivo, frases):
    contenido = _leer(archivo)
    for frase in frases:
        assert frase not in contenido, f"'{frase}' debería haberse eliminado de {archivo}"


# ── 2. Textos / helpers nuevos presentes ──

TEXTOS_NUEVOS = {
    "dash_ui.py": [
        "def card_narrativa",
        "Referencias a los post sobre",
        "verifica el post",
    ],
    "dash_bloque1.py": [
        "card_narrativa",
        "Enlaces de referencias bibliográficas",
    ],
    "dash_bloque2.py": [
        "card_narrativa",
        "Enlaces de referencias bibliográficas",
    ],
    "dash_bloque3.py": [
        "card_narrativa",
    ],
    "dash_bloque4.py": [
        "Post bibliográficos",
    ],
}


@pytest.mark.parametrize("archivo,frases", TEXTOS_NUEVOS.items())
def test_textos_nuevos(archivo, frases):
    contenido = _leer(archivo)
    for frase in frases:
        assert frase in contenido, f"'{frase}' debería estar presente en {archivo}"


# ── 3. Los módulos editados compilan ──

MODULOS = [
    "dash_ui.py",
    "dash_bloque1.py",
    "dash_bloque2.py",
    "dash_bloque3.py",
    "dash_bloque4.py",
    "dash_temas.py",
]


@pytest.mark.parametrize("archivo", MODULOS)
def test_modulos_compilan(archivo):
    ruta = os.path.join(DASH, archivo)
    py_compile.compile(ruta, doraise=True)
