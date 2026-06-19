"""
Sincronización opcional de las bases SQLite con un Dataset privado de Hugging Face.

Pensado para Hugging Face Spaces, cuyo disco es EFÍMERO (se pierde al reiniciar o
reconstruir el Space). Este módulo descarga las bases al arrancar y las vuelve a
subir tras cada escritura, usando un Dataset privado como almacén persistente.

OPCIONAL y NO INVASIVO: si no se definen las variables de entorno HF_DATASET_REPO
y HF_TOKEN, todas las funciones son no-ops y el proyecto se comporta igual que hoy
(local o Railway con volumen). Nunca lanza excepciones hacia la app.
"""

import logging
import os
import shutil

logger = logging.getLogger(__name__)

HF_DATASET_REPO = os.environ.get("HF_DATASET_REPO", "").strip()
HF_TOKEN = os.environ.get("HF_TOKEN", "").strip()

_SYNC_ACTIVO = bool(HF_DATASET_REPO and HF_TOKEN)
_ya_descargado = False


def sync_habilitado() -> bool:
    """True solo si se configuraron HF_DATASET_REPO y HF_TOKEN."""
    return _SYNC_ACTIVO


def _rutas_db():
    """Rutas absolutas de las tres bases (importa config de forma diferida)."""
    from dashboard import config as _cfg
    return [_cfg.FACEBOOK_DB, _cfg.TIKTOK_DB, _cfg.EXTERNOS_DB]


def pull_dbs() -> None:
    """Descarga las bases desde el Dataset al arrancar (una sola vez por proceso).

    No-op si la sincronización no está configurada. Nunca lanza excepción: si algo
    falla, se registra y se continúa con las bases locales.
    """
    global _ya_descargado
    if not _SYNC_ACTIVO or _ya_descargado:
        return
    _ya_descargado = True
    try:
        from huggingface_hub import hf_hub_download

        for ruta in _rutas_db():
            nombre = os.path.basename(ruta)
            try:
                cache_path = hf_hub_download(
                    repo_id=HF_DATASET_REPO,
                    filename=nombre,
                    repo_type="dataset",
                    token=HF_TOKEN,
                )
                os.makedirs(os.path.dirname(ruta), exist_ok=True)
                shutil.copyfile(cache_path, ruta)
                logger.info("hf_sync: base descargada -> %s", nombre)
            except Exception as e:
                # Normal en el primer arranque: el archivo aún no existe en el Dataset.
                logger.info("hf_sync: no se descargó %s (%s)", nombre, e)
    except Exception:
        logger.exception("hf_sync: fallo al descargar; se usan bases locales")


def push_dbs() -> None:
    """Sube las bases locales al Dataset tras una escritura.

    No-op si la sincronización no está configurada. Nunca lanza excepción.
    Crea el Dataset (privado) si aún no existe.
    """
    if not _SYNC_ACTIVO:
        return
    try:
        from huggingface_hub import HfApi

        api = HfApi(token=HF_TOKEN)
        try:
            api.create_repo(
                repo_id=HF_DATASET_REPO,
                repo_type="dataset",
                private=True,
                exist_ok=True,
            )
        except Exception:
            logger.exception("hf_sync: no se pudo asegurar el Dataset")

        for ruta in _rutas_db():
            if not os.path.exists(ruta):
                continue
            nombre = os.path.basename(ruta)
            try:
                api.upload_file(
                    path_or_fileobj=ruta,
                    path_in_repo=nombre,
                    repo_id=HF_DATASET_REPO,
                    repo_type="dataset",
                )
                logger.info("hf_sync: base subida -> %s", nombre)
            except Exception:
                logger.exception("hf_sync: fallo al subir %s", nombre)
    except Exception:
        logger.exception("hf_sync: fallo general al subir bases")
