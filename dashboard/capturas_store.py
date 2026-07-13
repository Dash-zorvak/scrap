"""Persistencia de capturas (imágenes) subidas en la ingesta, por post.

La ingesta extrae datos de las capturas con visión y, hasta ahora, las
descartaba. Para poder incrustar la publicación en el informe PDF de la medalla,
aquí se guardan los archivos de imagen en DATA_DIR/capturas/<post_id>/ y se
pueden listar después por post_id. Solo se guardan imágenes (PNG/JPG/WEBP); los
PDF subidos se omiten para el embed (sus datos sí se extraen aparte).
"""

import os
import sys

# DEUDA TÉCNICA: path hack temporal. Migrar a pyproject.toml cuando se consolide el paquete.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config import DATA_DIR  # type: ignore
except Exception:  # respaldo defensivo
    DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.getcwd(), "data"))

_EXT_VALIDAS = (".png", ".jpg", ".jpeg", ".webp")


def _dir_capturas(post_id, base=None):
    base = base or os.getenv("CAPTURAS_DIR") or os.path.join(DATA_DIR, "capturas")
    return os.path.join(base, str(post_id))


def guardar_capturas(post_id, imagenes, base=None):
    """Guarda imágenes de un post. Acepta UploadedFile de Streamlit, objetos con
    .getvalue()/.read(), o tuplas (nombre, bytes). Devuelve las rutas guardadas.
    """
    if not post_id or not imagenes:
        return []
    destino = _dir_capturas(post_id, base)
    try:
        os.makedirs(destino, exist_ok=True)
    except Exception:
        return []
    rutas = []
    for i, img in enumerate(imagenes):
        try:
            nombre = getattr(img, "name", None)
            datos = None
            if nombre is None and isinstance(img, (tuple, list)) and len(img) == 2:
                nombre, datos = img[0], img[1]
            elif hasattr(img, "getvalue"):
                datos = img.getvalue()
            elif hasattr(img, "read"):
                datos = img.read()
            else:
                datos = img
            ext = os.path.splitext(nombre or "")[1].lower()
            if ext not in _EXT_VALIDAS:
                continue  # solo imágenes; PDF y otros se omiten para el embed
            if not isinstance(datos, (bytes, bytearray)):
                continue
            ruta = os.path.join(destino, f"{i:02d}{ext}")
            with open(ruta, "wb") as f:
                f.write(datos)
            rutas.append(ruta)
        except Exception:
            continue
    return rutas


def listar_capturas(post_id, base=None):
    """Lista las rutas de capturas guardadas para un post (orden estable)."""
    destino = _dir_capturas(post_id, base)
    if not os.path.isdir(destino):
        return []
    try:
        return sorted(
            os.path.join(destino, n)
            for n in os.listdir(destino)
            if os.path.splitext(n)[1].lower() in _EXT_VALIDAS
        )
    except Exception:
        return []


def borrar_capturas(post_id, base=None):
    """Elimina las capturas de un post (al borrar el registro)."""
    destino = _dir_capturas(post_id, base)
    if not os.path.isdir(destino):
        return
    try:
        for n in os.listdir(destino):
            try:
                os.remove(os.path.join(destino, n))
            except Exception:
                pass
        os.rmdir(destino)
    except Exception:
        pass
