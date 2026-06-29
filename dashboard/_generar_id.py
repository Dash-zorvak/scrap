import hashlib
import uuid


def generar_id_post(base: str, ids_existentes: set) -> str:
    h = hashlib.sha1(base.encode("utf-8")).hexdigest()[:10]
    for eid in ids_existentes:
        if eid.endswith(f"_{h}"):
            return eid
    max_corr = 0
    for eid in ids_existentes:
        if eid.startswith("MAN_"):
            parts = eid.split("_")
            if len(parts) >= 3:
                try:
                    corr = int(parts[1])
                    if corr > max_corr:
                        max_corr = corr
                except ValueError:
                    pass
    corr = max_corr + 1
    return f"MAN_{corr:04d}_{h}"


def generar_id_comentario(id_padre: str, texto: str, indice: int) -> str:
    h = hashlib.sha1(texto.encode("utf-8")).hexdigest()[:8]
    return f"{id_padre}_c{indice:03d}_{h}"


def _base_para_hash(datos: dict) -> str:
    post_url = datos.get("post_url") or ""
    if post_url:
        return post_url
    if datos.get("plataforma") in ("facebook", "externos"):
        return f"{datos.get('page_name','')}|{datos.get('created_time','')}|{(datos.get('message','') or '')[:200]}"
    # TikTok: misma estrategia que Facebook -> identidad por CONTENIDO, nunca por
    # metricas. La descripcion cumple el papel del 'message' de FB. Cuando hay
    # descripcion la base es determinista, de modo que re-subir el MISMO video
    # reutiliza su id (upsert) igual que en FB. Cuando NO hay descripcion (ni
    # URL) no existe identidad fiable: dos videos DISTINTOS de la misma cuenta y
    # fecha producian la MISMA base -> el mismo id -> insertar_video
    # (INSERT OR REPLACE) pisaba una fila con otra (el bug reportado: de varios
    # subidos solo quedaba el ultimo). Para esos casos generamos una base UNICA
    # por video (uuid4) y asi cada video es SIEMPRE una fila propia y nunca puede
    # sobrescribir a otro que no le corresponde. Las metricas NO entran en la
    # firma: son volatiles (cambian con el tiempo / lectura del modelo) y por eso
    # el intento anterior de diferenciar por metricas no era fiable.
    desc = (datos.get("description", "") or "").strip()
    if desc:
        return "|".join(str(x) for x in [
            datos.get("account_id", "") or "",
            _norm_fecha(datos.get("created_at")),
            desc[:200],
        ])
    return f"tiktok-sin-identidad-{uuid.uuid4().hex}"


def _norm_fecha(val) -> str:
    """Normaliza una fecha a 'YYYY-MM-DD'.

    Acepta str ('2026-06-22 00:00:00.000000', '2026-06-22T00:00:00'), datetime
    (su str() empieza por la fecha ISO) o None. Permite comparar la fecha de un
    post entre lo recien subido (str del formulario) y lo ya guardado en la base
    (DateTime de SQLAlchemy), que pueden diferir en separador o microsegundos.
    """
    if not val:
        return ""
    return str(val)[:10]


def firma_contenido(datos: dict) -> str:
    """Firma de contenido de un post, INDEPENDIENTE de la URL.

    El mismo post de Facebook puede subirse con dos enlaces distintos: el
    permalink ('.../posts/123') y el enlace de compartir ('.../share/p/XXXX').
    Como `_base_para_hash` usa la URL literal, esos dos enlaces producen dos
    post_id distintos -> el post y TODOS sus comentarios se guardan dos veces.
    Esta firma (plataforma + pagina + fecha + inicio del texto) identifica que es
    el mismo post aunque cambie la URL.

    Devuelve '' cuando no hay texto suficiente para una firma fiable; en ese caso
    NO se deduplica por contenido (solo por URL), para no fusionar por error dos
    posts distintos que carecen de texto.
    """
    plat = datos.get("plataforma")
    if plat in ("facebook", "externos"):
        page = (datos.get("page_name", "") or "").strip()
        msg = (datos.get("message", "") or "").strip()
        if not msg:
            return ""
        return f"{plat}|{page}|{_norm_fecha(datos.get('created_time'))}|{msg[:200]}"
    if plat == "tiktok":
        desc = (datos.get("description", "") or "").strip()
        if not desc:
            return ""
        return f"tiktok|{datos.get('account_id','') or ''}|{_norm_fecha(datos.get('created_at'))}|{desc[:200]}"
    return ""


def resolver_id_post(datos: dict, ids_existentes: set, firmas_existentes: dict) -> str:
    """Resuelve el post_id a usar, reutilizando un post ya existente cuando:
      1) coincide la firma de contenido (mismo post subido con enlace distinto), o
      2) coincide el hash de la URL (comportamiento clasico de generar_id_post).

    `firmas_existentes` es un dict {firma_contenido -> post_id} que se MUTA para
    registrar el id resultante, de modo que tambien deduplica dentro del mismo
    lote (dos items con el mismo contenido y distinta URL -> un solo post_id).
    """
    firma = firma_contenido(datos)
    if firma and firma in firmas_existentes:
        return firmas_existentes[firma]
    base = _base_para_hash(datos)
    pid = generar_id_post(base, ids_existentes)
    if firma:
        firmas_existentes.setdefault(firma, pid)
    return pid
