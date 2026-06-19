import hashlib


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
    return f"{datos.get('account_id','')}|{datos.get('created_at','')}|{(datos.get('description','') or '')[:200]}"
