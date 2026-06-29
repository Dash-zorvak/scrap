import logging
import sqlite3

from src.storage.db import LocalStorage
from dashboard import config as _cfg
from dashboard._generar_id import (
    generar_id_post,
    generar_id_comentario,
    _base_para_hash,
    firma_contenido,
    resolver_id_post,
)
from dashboard.escritura_tiktok import insertar_video, insertar_comentario_tiktok, obtener_ids_videos
from dashboard.externos_store import (
    asegurar_tablas_externas,
    obtener_ids_posts_externos,
    insertar_post_externo,
    insertar_comentario_externo,
    agregar_pagina_externa,
)

logger = logging.getLogger(__name__)


def _fb_post_insert_dict(datos: dict, post_id: str) -> dict:
    comentarios = datos.get("comentarios") or []
    return {
        "post_id": post_id,
        "page_name": datos.get("page_name", ""),
        "message": datos.get("message", ""),
        "created_time": datos.get("created_time"),
        "likes_count": datos.get("likes_count", 0) or 0,
        "loves_count": datos.get("loves_count", 0) or 0,
        "cares_count": datos.get("cares_count", 0) or 0,
        "hahas_count": datos.get("hahas_count", 0) or 0,
        "sads_count": datos.get("sads_count", 0) or 0,
        "wows_count": datos.get("wows_count", 0) or 0,
        "angrys_count": datos.get("angrys_count", 0) or 0,
        "comments_count": datos.get("comments_count", 0) or len(comentarios),
        "shares_count": datos.get("shares_count", 0) or 0,
        "views_count": datos.get("views_count", 0) or 0,
        "post_url": datos.get("post_url", ""),
        "source": "manual",
    }


def _fb_comment_insert_dict(comentario: dict, comment_id: str, post_id: str) -> dict:
    return {
        "comment_id": comment_id,
        "post_id": post_id,
        "message": comentario.get("texto", ""),
        "author_name": comentario.get("autor") or "",
    }


def _cargar_firmas_fb(ruta_fb: str) -> dict:
    """Precarga {firma_contenido -> post_id} de los posts FB ya guardados.

    Permite que `resolver_id_post` reutilice un post existente cuando el mismo
    contenido se vuelve a subir con otra URL (permalink vs enlace de compartir),
    evitando duplicar el post y sus comentarios entre sesiones distintas.
    """
    firmas: dict = {}
    try:
        conn = sqlite3.connect(ruta_fb)
        try:
            filas = conn.execute(
                "SELECT post_id, page_name, created_time, message FROM fb_posts"
            ).fetchall()
        finally:
            conn.close()
        for post_id, page_name, created_time, message in filas:
            firma = firma_contenido({
                "plataforma": "facebook",
                "page_name": page_name,
                "created_time": created_time,
                "message": message,
            })
            if firma:
                firmas.setdefault(firma, post_id)
    except Exception:
        # Tabla aun inexistente (base nueva) u otro problema de lectura: sin
        # firmas previas la ingesta sigue funcionando, solo sin dedup por contenido.
        return {}
    return firmas


def guardar_lote(lote: list, progreso_cb=None) -> dict:
    """Guarda un lote de items revisados en sus bases de datos.

    progreso_cb (opcional): callable(i, total, etiqueta) que se invoca una vez
    por cada item revisado procesado (haya tenido exito o error), para que la UI
    pueda mostrar un contador real i/total en vez de quedarse en 0/total hasta
    el final. Cualquier excepcion del callback se ignora.
    """
    ruta_fb = _cfg.FACEBOOK_DB
    ruta_tk = _cfg.TIKTOK_DB
    ruta_ext = _cfg.EXTERNOS_DB

    resumen = {
        "fb_posts": 0, "fb_comments": 0,
        "tk_videos": 0, "tk_comments": 0,
        "ext_posts": 0, "ext_comments": 0,
        "errores": [],
    }

    revisados = [item for item in lote if item.get("estado") == "revisado"]
    if not revisados:
        return resumen

    total = len(revisados)

    store = LocalStorage(db_path=ruta_fb)
    fb_ids_existentes = store.get_all_ids("fb_posts", "post_id")
    fb_firmas = _cargar_firmas_fb(ruta_fb)

    conn_tk = sqlite3.connect(ruta_tk)
    try:
        tk_ids_existentes = obtener_ids_videos(conn_tk)
    except Exception:
        tk_ids_existentes = set()

    asegurar_tablas_externas(ruta_ext)
    conn_ext = sqlite3.connect(ruta_ext)
    try:
        ext_ids_existentes = obtener_ids_posts_externos(conn_ext)
    except Exception:
        ext_ids_existentes = set()

    for _idx, item in enumerate(revisados, start=1):
        datos = item.get("datos_revisados", {})
        plataforma = datos.get("plataforma")

        try:
            if plataforma == "facebook":
                post_id = resolver_id_post(datos, fb_ids_existentes, fb_firmas)
                fb_ids_existentes.add(post_id)
                post_dict = _fb_post_insert_dict(datos, post_id)
                ok = store.insert_fb_post(post_dict)
                if not ok:
                    resumen["errores"].append(f"Error insertando post FB: {post_id}")
                    continue
                resumen["fb_posts"] += 1

                comentarios = datos.get("comentarios") or []
                for idx, c in enumerate(comentarios):
                    texto = c.get("texto", "")
                    if not texto:
                        continue
                    cid = generar_id_comentario(post_id, texto, idx)
                    cdict = _fb_comment_insert_dict(c, cid, post_id)
                    ok = store.insert_fb_comment(cdict)
                    if ok:
                        resumen["fb_comments"] += 1
                    else:
                        resumen["errores"].append(f"Error insertando comentario FB: {cid}")

                # Persistir las capturas subidas para poder incrustar la
                # publicacion en el informe PDF de la medalla mas adelante.
                try:
                    from dashboard.capturas_store import guardar_capturas
                    guardar_capturas(post_id, item.get("imagenes"))
                except Exception:
                    pass

                item["post_id"] = post_id
                item["estado"] = "guardado"

            elif plataforma == "tiktok":
                base = _base_para_hash(datos)
                video_id = generar_id_post(base, tk_ids_existentes)
                tk_ids_existentes.add(video_id)
                ok = insertar_video(conn_tk, datos, video_id)
                if not ok:
                    resumen["errores"].append(f"Error insertando video TK: {video_id}")
                    continue
                resumen["tk_videos"] += 1

                comentarios = datos.get("comentarios") or []
                for idx, c in enumerate(comentarios):
                    texto = c.get("texto", "")
                    if not texto:
                        continue
                    cid = generar_id_comentario(video_id, texto, idx)
                    ok = insertar_comentario_tiktok(conn_tk, cid, video_id, texto)
                    if ok:
                        resumen["tk_comments"] += 1
                    else:
                        resumen["errores"].append(f"Error insertando comentario TK: {cid}")

                item["video_id"] = video_id
                item["estado"] = "guardado"

            elif plataforma == "externos":
                base = _base_para_hash(datos)
                post_id = generar_id_post(base, ext_ids_existentes)
                ext_ids_existentes.add(post_id)
                ok = insertar_post_externo(conn_ext, datos, post_id)
                if not ok:
                    resumen["errores"].append(f"Error insertando post externo: {post_id}")
                    continue
                resumen["ext_posts"] += 1

                comentarios = datos.get("comentarios") or []
                for idx, c in enumerate(comentarios):
                    texto = c.get("texto", "")
                    if not texto:
                        continue
                    cid = generar_id_comentario(post_id, texto, idx)
                    try:
                        insertar_comentario_externo(conn_ext, cid, post_id, texto, c.get("autor"))
                        resumen["ext_comments"] += 1
                    except Exception:
                        resumen["errores"].append(f"Error insertando comentario externo: {cid}")

                conn_ext.commit()
                try:
                    agregar_pagina_externa(datos.get("page_name", ""), ruta_ext)
                except Exception:
                    pass

                item["post_id"] = post_id
                item["estado"] = "guardado"

            else:
                raise ValueError(f"Plataforma no soportada: {plataforma}")

        except Exception as e:
            resumen["errores"].append(f"Error procesando item {item.get('id_temporal','?')}: {e}")
            logger.exception(f"Error en guardar_lote para item {item.get('id_temporal')}")

        if progreso_cb is not None:
            etiqueta = (
                datos.get("page_name")
                or datos.get("account_id")
                or item.get("id_temporal", "")
            )
            try:
                progreso_cb(_idx, total, etiqueta)
            except Exception:
                pass

    conn_tk.close()
    conn_ext.close()

    # Persistir en HF Dataset si la sincronizacion esta activa (no-op en local/Railway).
    try:
        from dashboard.hf_sync import push_dbs as _hf_push_dbs
        _hf_push_dbs()
    except Exception:
        pass

    return resumen
