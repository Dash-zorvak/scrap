"""Unico punto de escritura para data/analysis.json.

Toda escritura a analysis.json pasa por aqui.  Garantiza:
1. Validacion antes de escribir (V01-V08).
2. Backup automatico del archivo previo.
3. Escritura atomica (temp + rename).
4. Rollback automatico si la validacion falla.

Uso:
    from analytics.publish import publicar_analysis
    resultado = publicar_analysis(nuevos_datos)
    if not resultado.es_publicable:
        print(resultado.errores)
"""
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone

from analytics.schema_validator import validar, ValidationError, ValidationResult

_ANALYSIS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "analysis.json"
)


def publicar_analysis(data: dict, path: str | None = None,
                      max_backups: int = 5,
                      render_narrativas: bool = True) -> ValidationResult:
    """Valida y escribe analysis.json de forma atomica.

    Args:
        data: dict con la estructura de analysis.json.
        path: ruta al archivo (default: data/analysis.json).
        max_backups: cuantos backups antiguos conservar.
        render_narrativas: si True, renderiza placeholders en narrativas.

    Returns:
        ValidationResult con errores si la validacion falla.
        Si es publicable, escribe el archivo y retorna resultado sin errores.
    """
    path = path or _ANALYSIS_PATH

    # Renderizar narrativas antes de validar (placeholders -> valores reales)
    if render_narrativas:
        from analytics.narrative_renderer import renderizar_analysis
        data = renderizar_analysis(data)

    resultado = validar(data)
    if not resultado.es_publicable:
        return resultado

    dir_destino = os.path.dirname(path)
    os.makedirs(dir_destino, exist_ok=True)

    # Backup del archivo actual
    if os.path.exists(path):
        _crear_backup(path, max_backups)

    # Escritura atomica: temp file -> rename
    fd, tmp_path = tempfile.mkstemp(
        suffix=".json", prefix=".analysis_", dir=dir_destino
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        shutil.move(tmp_path, path)
    except Exception:
        # Cleanup temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return resultado


def _crear_backup(path: str, max_backups: int):
    """Crea un backup numerado del archivo y elimina los mas antiguos."""
    backup_dir = os.path.join(os.path.dirname(path), "_analysis_backups")
    os.makedirs(backup_dir, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    nombre = os.path.basename(path)
    backup_path = os.path.join(backup_dir, f"{nombre}.{ts}.bak")
    shutil.copy2(path, backup_path)

    # Limpiar backups antiguos
    backups = sorted(
        [f for f in os.listdir(backup_dir) if f.startswith(nombre)],
    )
    while len(backups) > max_backups:
        os.unlink(os.path.join(backup_dir, backups.pop(0)))
