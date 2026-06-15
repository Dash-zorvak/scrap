import logging
import sqlite3

from src.storage.db import LocalStorage
from dashboard import config as _cfg
from dashboard._generar_id import generar_id_post, generar_id_comentario, _base_para_hash
from dashboard.escritura_tiktok import insertar_video, insertar_comentario_tiktok, obtener_ids_videos

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


def guardar_lote(lote: list, modo_prueba: bool = False) -> dict:
    ruta_fb = _cfg.FACEBOOK_TEST_DB if modo_prueba else _cfg.FACEBOOK_DB
    ruta_tk = _cfg.TIKTOK_TEST_DB if modo_prueba else _cfg.TIKTOK_DB

    resumen = {"fb_posts": 0, "fb_comments": 0, "tk_videos": 0, "tk_comments": 0, "errores": []}

    revisados = [item for item in lote if item.get("estado") == "revisado"]
    if not revisados:
        return resumen

    store = LocalStorage(db_path=ruta_fb)
    fb_ids_existentes = store.get_all_ids("fb_posts", "post_id")

    conn_tk = sqlite3.connect(ruta_tk)
    try:
        tk_ids_existentes = obtener_ids_videos(conn_tk)
    except Exception:
        tk_ids_existentes = set()

    for item in revisados:
        datos = item.get("datos_revisados", {})
        plataforma = datos.get("plataforma")

        try:
            if plataforma == "facebook":
                base = _base_para_hash(datos)
                post_id = generar_id_post(base, fb_ids_existentes)
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

            else:
                raise ValueError(f"Plataforma no soportada: {plataforma}")

        except Exception as e:
            resumen["errores"].append(f"Error procesando item {item.get('id_temporal','?')}: {e}")
            logger.exception(f"Error en guardar_lote para item {item.get('id_temporal')}")

    conn_tk.close()
    return resumen
