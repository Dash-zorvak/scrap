"""Configuración de logging centralizada.

Todos los módulos del proyecto usan esta función para configurar su logger
raíz con el mismo formato y nivel. Se llama una sola vez al inicio de
app.py y panel_carga.py.

Uso:
    from config.logging_config import configurar_logging
    configurar_logging()  # nivel INFO por defecto
"""
import logging
import logging.handlers
import os


def configurar_logging(nivel: str = "INFO", log_a_archivo: bool = False,
                       max_bytes: int = 5 * 1024 * 1024,
                       backup_count: int = 3) -> None:
    """Configura el logger raíz con formato consistente.

    Args:
        nivel: nivel de log (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_a_archivo: si True, también escribe a data/logs/app.log.
        max_bytes: tamaño máximo del archivo de log antes de rotar.
        backup_count: número de archivos de log rotativos a conservar.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, nivel.upper(), logging.INFO))

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler stdout (capturado por Streamlit/systemd/Cloudflare)
    if not root.handlers:
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        root.addHandler(stream)

    # Handler archivo rotativo (opcional)
    if log_a_archivo:
        try:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            log_dir = os.path.join(base, "data", "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, "app.log")

            file_handler = logging.handlers.RotatingFileHandler(
                log_path, maxBytes=max_bytes, backupCount=backup_count,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except OSError:
            root.warning("No se pudo crear archivo de log en data/logs/app.log")
