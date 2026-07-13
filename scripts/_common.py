"""Funciones compartidas para scripts de mantenimiento.

Centraliza validación de identificadores SQL y whitelist de tablas conocidas
para evitar duplicación entre purge_out_of_range.py, verify_db.py, etc.
"""
import re

_IDENT_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

# Whitelist de tablas conocidas del proyecto.
# Solo estas tablas pueden interpolarse en SQL de scripts.
TABLE_WHITELIST = frozenset({
    # Facebook
    "fb_posts", "fb_comments", "fb_engagement",
    # TikTok
    "videos", "comments",
    # Externos
    "external_posts", "external_comments", "external_sentimiento", "external_pages",
    # Auditoría
    "audit_log",
    # Temas
    "tema_aprobaciones",
})


def validar_identificador(nombre: str) -> str:
    """Valida que un identificador SQL sea seguro (alfanumérico + _).

    Raises:
        ValueError: si el identificador contiene caracteres no seguros.
    """
    if not _IDENT_RE.match(nombre):
        raise ValueError(f"Identificador SQL invalido/no permitido: {nombre!r}")
    return nombre


def validar_tabla(nombre: str) -> str:
    """Valida que un nombre de tabla esté en la whitelist conocida.

    Primero valida que sea un identificador seguro, luego verifica
    que esté en la whitelist de tablas del proyecto.

    Raises:
        ValueError: si el nombre no es seguro o no está en la whitelist.
    """
    validar_identificador(nombre)
    if nombre not in TABLE_WHITELIST:
        raise ValueError(
            f"Tabla '{nombre}' no está en la whitelist de tablas conocidas. "
            f"Tablas permitidas: {sorted(TABLE_WHITELIST)}"
        )
    return nombre
