"""Punto unico de saneamiento de contenido de terceros antes de inyectarlo
en bloques st.markdown(..., unsafe_allow_html=True).

Todo texto que provenga de comentarios, citas, publicaciones o cualquier
campo de analysis.json que contenga texto libre DEBE pasar por safe_text()
antes de interpolarse en HTML. Los campos de este propio codigo (labels,
clases CSS, valores numericos ya validados) no requieren saneamiento.
"""
from markupsafe import escape


def safe_text(value) -> str:
    """Escapa HTML. None -> cadena vacia. Cualquier tipo no-str se castea a str."""
    if value is None:
        return ""
    return str(escape(str(value)))


def safe_list(values) -> list:
    return [safe_text(v) for v in (values or [])]
