"""Deduplica posts de Facebook que quedaron guardados dos veces.

CAUSA: un mismo post puede subirse con dos enlaces distintos: el permalink
('.../posts/123') y el enlace de compartir ('.../share/p/XXXX'). Como el id del
post se derivaba del texto de la URL, cada enlace generaba un post_id distinto y,
con el, una copia del post y de TODOS sus comentarios. Al aprobar un comentario,
su gemelo (con otro comment_id) seguia pendiente y \"reaparecia\" para clasificar.

QUE HACE: detecta posts con la misma FIRMA DE CONTENIDO (pagina + fecha + inicio
del texto), conserva uno (el canonico) y, de las copias, ELIMINA solo los
comentarios identicos exactos (mismo autor + mismo texto) y MUEVE al canonico los
que solo existian en la copia. No se pierde ningun comentario distinto: el
dashboard sigue basandose en el 100%% de los comentarios reales. NUNCA colapsa
comentarios de personas distintas ni textos parecidos (por ejemplo la misma
persona comentando \"Excelente\" en dos publicaciones diferentes se conserva).

Reasigna o elimina las aprobaciones de tema afectadas. El post canonico se elige
por: mas comentarios -> permalink (evita '/share/') -> post_id menor (estable).

Uso:
    python dashboard/dedupe_posts.py             # pide confirmacion
    python dashboard/dedupe_posts.py --dry-run   # solo informa, no modifica
    python dashboard/dedupe_posts.py --force     # sin confirmacion
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard._generar_id import firma_contenido


def _norm_txt(s: str) -> str:
    """Normaliza un texto de comentario para comparar COPIAS EXACTAS del mismo
    comentario (colapsa espacios e ignora may/minusculas). No hace coincidencia
    difusa: textos realmente distintos siguen siendo distintos."""
    return " ".join((s or "").split()).casefold()


def _tiene_tabla(conn, nombre: str) -> bool:
    return conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (nombre,)
    ).fetchone() is not None


def _n_comentarios(conn, post_id: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM fb_comments WHERE post_id=?", (post_id,)
    ).fetchone()[0]


def grupos_duplicados(conn) -> list:
    """Devuelve los grupos (>=2 post_id) que comparten firma de contenido."""
    filas = conn.execute(
        "SELECT post_id, page_name, created_time, message FROM fb_posts"
    ).fetchall()
    grupos: dict = {}
    for post_id, page_name, created_time, message in filas:
        firma = firma_contenido({
            "plataforma": "facebook",
            "page_name": page_name,
            "created_time": created_time,
            "message": message,
        })
        if not firma:
            continue
        grupos.setdefault(firma, []).append(post_id)
    return [pids for pids in grupos.values() if len(pids) > 1]


def elegir_canonico(conn, post_ids: list) -> str:
    """Elige el post a conservar: mas comentarios, luego permalink (no '/share/'),
    luego el post_id menor (orden estable)."""
    def clave(pid):
        url = conn.execute(
            "SELECT post_url FROM fb_posts WHERE post_id=?", (pid,)
        ).fetchone()[0] or ""
        return (-_n_comentarios(conn, pid), 1 if "/share/" in url else 0, pid)

    return sorted(post_ids, key=clave)[0]


def deduplicar(conn) -> dict:
    """Fusiona los grupos de posts duplicados in-place. Devuelve un resumen."""
    resumen = {
        "grupos": 0,
        "posts_eliminados": 0,
        "comentarios_eliminados": 0,
        "comentarios_reasignados": 0,
        "aprobaciones_remapeadas": 0,
        "aprobaciones_eliminadas": 0,
    }
    hay_aprob = _tiene_tabla(conn, "tema_aprobaciones")

    for grupo in grupos_duplicados(conn):
        resumen["grupos"] += 1
        canonico = elegir_canonico(conn, grupo)

        # (autor, texto_norm) -> comment_id ya presente en el canonico
        canon_map: dict = {}
        for cid, autor, msg in conn.execute(
            "SELECT comment_id, author_name, message FROM fb_comments WHERE post_id=?",
            (canonico,),
        ):
            canon_map.setdefault((autor or "", _norm_txt(msg)), cid)

        for dup in grupo:
            if dup == canonico:
                continue
            dup_coms = conn.execute(
                "SELECT comment_id, author_name, message FROM fb_comments WHERE post_id=?",
                (dup,),
            ).fetchall()
            for cid, autor, msg in dup_coms:
                clave = (autor or "", _norm_txt(msg))
                if clave in canon_map:
                    # el canonico ya tiene este comentario exacto -> borrar la copia
                    destino = canon_map[clave]
                    conn.execute("DELETE FROM fb_comments WHERE comment_id=?", (cid,))
                    resumen["comentarios_eliminados"] += 1
                    if hay_aprob:
                        ya = conn.execute(
                            "SELECT 1 FROM tema_aprobaciones WHERE comment_id=?",
                            (destino,),
                        ).fetchone()
                        if ya:
                            d = conn.execute(
                                "DELETE FROM tema_aprobaciones WHERE comment_id=?",
                                (cid,),
                            ).rowcount
                            resumen["aprobaciones_eliminadas"] += d
                        else:
                            n = conn.execute(
                                "UPDATE tema_aprobaciones SET comment_id=? WHERE comment_id=?",
                                (destino, cid),
                            ).rowcount
                            resumen["aprobaciones_remapeadas"] += n
                else:
                    # comentario que el canonico no tenia -> moverlo al canonico
                    suffix = cid[len(dup):] if cid.startswith(dup) else "_" + cid
                    destino = canonico + suffix
                    while conn.execute(
                        "SELECT 1 FROM fb_comments WHERE comment_id=?", (destino,)
                    ).fetchone():
                        destino += "x"
                    conn.execute(
                        "UPDATE fb_comments SET comment_id=?, post_id=? WHERE comment_id=?",
                        (destino, canonico, cid),
                    )
                    canon_map[clave] = destino
                    resumen["comentarios_reasignados"] += 1
                    if hay_aprob:
                        conn.execute(
                            "UPDATE tema_aprobaciones SET comment_id=? WHERE comment_id=?",
                            (destino, cid),
                        )
            conn.execute("DELETE FROM fb_posts WHERE post_id=?", (dup,))
            resumen["posts_eliminados"] += 1

    conn.commit()
    return resumen


def _previsualizar(conn) -> list:
    lineas = []
    for grupo in grupos_duplicados(conn):
        canon = elegir_canonico(conn, grupo)
        otros = [p for p in grupo if p != canon]
        lineas.append(f"  - {len(grupo)} copias | conservar: {canon} | eliminar: {otros}")
    return lineas


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    dry = "--dry-run" in argv or "-n" in argv
    force = "--force" in argv or "-f" in argv

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config import FACEBOOK_DB

    if not os.path.exists(FACEBOOK_DB):
        print(f"No existe la base: {FACEBOOK_DB}")
        return

    conn = sqlite3.connect(FACEBOOK_DB)
    try:
        lineas = _previsualizar(conn)
        if not lineas:
            print("\u2705 No hay posts duplicados. Nada que hacer.")
            return
        print("Posts duplicados detectados (misma pagina + fecha + texto):")
        for l in lineas:
            print(l)
        if dry:
            print("\n(--dry-run) No se modifico nada.")
            return
        if not force:
            resp = input("\n\u00bfFusionar y eliminar los duplicados? (escribe 'si'): ")
            if resp.strip().lower() not in ("si", "s\u00ed", "s", "yes", "y"):
                print("Cancelado.")
                return
        res = deduplicar(conn)
        print("\n\u2705 Listo:")
        for k, v in res.items():
            print(f"   {k}: {v}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
