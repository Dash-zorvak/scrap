"""Resolucion de post_ids a URLs reales para evidencia de narrativas.

Este modulo traduce los post_ids/video_ids guardados durante la clasificacion
de comentarios (en _evidencia_periodo.json) a URLs reales usando las queries
de referencia existentes. Cada funcion retorna lista de URLs sin duplicados
y sin truncar (RG-5: la lista completa, no una muestra).

Uso desde el paso narrar (analytics/cli.py::cmd_narrar):
    from analytics.evidence import resolver_evidencia_tema
    urls = resolver_evidencia_tema("seguridad", evidencia["por_tema"])
"""
import logging

from analytics.queries import (
    get_fb_references_by_ids,
    get_tk_references_by_ids,
)

logger = logging.getLogger(__name__)


def _obtener_fb_references(post_ids: list[str]) -> dict[str, str]:
    """Resuelve FB post_ids a {post_id: post_url} usando get_fb_references_by_ids."""
    if not post_ids:
        return {}
    try:
        rows = get_fb_references_by_ids(post_ids)
        return {r["post_id"]: r["post_url"] for r in rows if r.get("post_url")}
    except Exception as e:
        logger.debug("FB references lookup failed: %s", e)
        return {}


def _obtener_tk_references(post_ids: list[str]) -> dict[str, str]:
    """Resuelve TikTok post_ids a {post_id: post_url} usando get_tk_references_by_ids."""
    if not post_ids:
        return {}
    try:
        rows = get_tk_references_by_ids(post_ids)
        return {r["post_id"]: r["post_url"] for r in rows if r.get("post_url")}
    except Exception as e:
        logger.debug("TK references lookup failed: %s", e)
        return {}


def _obtener_fb_recent_references(post_ids: list[str]) -> dict[str, str]:
    """Fallback: busca URLs en fb_posts recientes para IDs no encontrados."""
    if not post_ids:
        return {}
    try:
        from src.config import Config
        import sqlite3
        cfg = Config()
        conn = sqlite3.connect(cfg.FACEBOOK_DB)
        conn.row_factory = sqlite3.Row
        try:
            placeholders = ",".join("?" * len(post_ids))
            rows = conn.execute(
                f"SELECT post_id, post_url FROM fb_posts "
                f"WHERE post_id IN ({placeholders}) "
                f"AND post_url IS NOT NULL AND TRIM(post_url) != ''",
                post_ids,
            ).fetchall()
            return {r["post_id"]: r["post_url"] for r in rows}
        finally:
            conn.close()
    except Exception as e:
        logger.debug("FB recent references lookup failed: %s", e)
        return {}


def _resolver_ids_a_urls(post_ids: list[str]) -> list[str]:
    """Resuelve una lista de post_ids a URLs, intentando FB y TK.

    Primero busca en FB, luego en TK, y finalmente fallback en FB recientes
    para IDs no encontrados. Retorna URLs sin duplicados ni truncamiento.
    """
    if not post_ids:
        return []

    fb_map = _obtener_fb_references(post_ids)
    tk_map = _obtener_tk_references(post_ids)

    # Combinar resultados
    url_map = {**fb_map, **tk_map}

    # Fallback para IDs no encontrados en las tablas de referencia
    no_encontrados = [pid for pid in post_ids if pid not in url_map]
    if no_encontrados:
        fb_recent = _obtener_fb_recent_references(no_encontrados)
        url_map.update(fb_recent)

    # Mantener orden de insercion, sin duplicados
    urls = []
    seen = set()
    for pid in post_ids:
        url = url_map.get(pid, "")
        if url and url not in seen:
            urls.append(url)
            seen.add(url)
    return urls


def resolver_evidencia_tema(tema: str, evidencia_por_tema: dict) -> list[str]:
    """Resuelve post_ids de un tema a URLs reales.

    Args:
        tema: nombre del tema (ej. "seguridad").
        evidencia_por_tema: dict {tema: [post_id, ...]}.

    Returns:
        Lista de URLs sin duplicados.
    """
    post_ids = evidencia_por_tema.get(tema, [])
    return _resolver_ids_a_urls(post_ids)


def resolver_evidencia_emocion(emocion: str, evidencia_por_emocion: dict) -> list[str]:
    """Resuelve post_ids de una emocion a URLs reales."""
    post_ids = evidencia_por_emocion.get(emocion, [])
    return _resolver_ids_a_urls(post_ids)


def resolver_evidencia_friccion(tema: str, evidencia: dict) -> list[str]:
    """Resuelve post_ids de un punto de friccion a URLs reales.

    Busca en por_tema y por_emocion del dict de evidencia.
    """
    post_ids = set()
    post_ids.update(evidencia.get("por_tema", {}).get(tema, []))
    return _resolver_ids_a_urls(sorted(post_ids))


def resolver_evidencia_voz(pagina: str, evidencia: dict) -> list[str]:
    """Resuelve post_ids de una voz de influencia a URLs reales.

    Busca en todas las fuentes de evidencia disponibles.
    """
    # Las voces no tienen evidencia directa por tema/emocion en el
    # modelo actual. Retornamos URLs vacias por ahora; el campo
    # enlaces_referencia se poblara si hay datos de fb_posts por pagina.
    return []


def resolver_evidencia_alertas(alertas: list, evidencia: dict) -> list[str]:
    """Resuelve enlaces de alertas de Cambridge.

    Las alertas ya tienen enlaces_referencia pre-poblados por report.py.
    Este metodo los extrae y agrega evidencia adicional si esta disponible.
    """
    urls = []
    for alerta in alertas:
        if isinstance(alerta, dict):
            for url in alerta.get("enlaces_referencia", []):
                if url and url not in urls:
                    urls.append(url)
    return urls
