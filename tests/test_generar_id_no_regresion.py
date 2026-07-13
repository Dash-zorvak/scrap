"""Tests de regresion para el bug historico de generacion de IDs (H-ARQ4).

Previenen que dup_counter genere sufijos artificiales _1/_2 para posts con
la misma URL subidos en momentos distintos. Verifica que resolver_id_post
reutiliza el mismo post_id (comportamiento upsert) en vez de duplicar.
"""
import re

from dashboard._generar_id import (
    generar_id_post,
    resolver_id_post,
    firma_contenido,
    _base_para_hash,
)
from scripts.dedupe_existing import has_artificial_suffix


def test_mismo_post_url_reutiliza_id():
    """Mismo post_url -> mismo post_id (upsert, no duplicado)."""
    datos = {
        "plataforma": "facebook",
        "page_name": "Alcaldia de Santa Ana",
        "created_time": "2026-07-01",
        "message": "Mensaje de prueba para dedup",
        "post_url": "https://fb.com/posts/12345",
    }
    ids_existentes = set()
    firmas = {}

    pid1 = resolver_id_post(datos, ids_existentes, firmas)
    ids_existentes.add(pid1)

    pid2 = resolver_id_post(datos, ids_existentes, firmas)
    assert pid1 == pid2, "El mismo post subido dos veces debe producir el mismo post_id"


def test_mismo_contenido_distinta_url_reutiliza_id():
    """Misma firma de contenido pero distinta URL -> mismo post_id."""
    datos1 = {
        "plataforma": "facebook",
        "page_name": "Alcaldia de Santa Ana",
        "created_time": "2026-07-01",
        "message": "Mensaje duplicado con URL distinta",
        "post_url": "https://fb.com/posts/11111",
    }
    datos2 = {
        "plataforma": "facebook",
        "page_name": "Alcaldia de Santa Ana",
        "created_time": "2026-07-01",
        "message": "Mensaje duplicado con URL distinta",
        "post_url": "https://fb.com/share/p/XXXXX",
    }
    ids_existentes = set()
    firmas = {}

    pid1 = resolver_id_post(datos1, ids_existentes, firmas)
    ids_existentes.add(pid1)

    pid2 = resolver_id_post(datos2, ids_existentes, firmas)
    assert pid1 == pid2, "Mismo contenido con URL distinta debe reutilizar post_id"


def test_posts_distintos_sin_url_generan_ids_distintos():
    """Dos posts distintos sin post_url -> cada uno recibe un post_id distinto."""
    datos1 = {
        "plataforma": "facebook",
        "page_name": "Alcaldia",
        "created_time": "2026-07-01",
        "message": "Primer post distinto",
    }
    datos2 = {
        "plataforma": "facebook",
        "page_name": "Alcaldia",
        "created_time": "2026-07-01",
        "message": "Segundo post distinto",
    }
    ids_existentes = set()
    firmas = {}

    pid1 = resolver_id_post(datos1, ids_existentes, firmas)
    ids_existentes.add(pid1)
    pid2 = resolver_id_post(datos2, ids_existentes, firmas)
    assert pid1 != pid2, "Posts distintos deben tener IDs distintos"


def test_no_sufijos_artificiales():
    """regresion del bug: ningun post_id termina en _N (sufijo de corr)."""
    datos = {
        "plataforma": "facebook",
        "page_name": "Alcaldia",
        "created_time": "2026-07-01",
        "message": "Test sin sufijos",
        "post_url": "https://fb.com/posts/99999",
    }
    ids_existentes = set()
    firmas = {}
    for _ in range(5):
        pid = resolver_id_post(datos, ids_existentes, firmas)
        ids_existentes.add(pid)

    assert not has_artificial_suffix(pid), f"post_id no debe tener sufijo artificial: {pid}"


def test_tiktok_sin_descripcion_uuid_unico():
    """Videos TikTok sin descripcion ni URL generan id unico (uuid4)."""
    datos = {
        "plataforma": "tiktok",
        "account_id": 1,
        "created_at": "2026-07-01",
        "description": "",
    }
    ids_existentes = set()
    firmas = {}

    pid1 = resolver_id_post(datos, ids_existentes, firmas)
    ids_existentes.add(pid1)
    pid2 = resolver_id_post(datos, ids_existentes, firmas)
    assert pid1 != pid2, "TikTok sin descripcion: cada video debe tener id unico"
