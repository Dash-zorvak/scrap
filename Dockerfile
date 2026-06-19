# Imagen para Hugging Face Spaces (SDK: Docker).
# Arranca el dashboard Streamlit en el puerto 7860 (estandar de HF Docker Spaces).
FROM python:3.11-slim

# Dependencias de sistema utiles para compilar algunas ruedas si hiciera falta.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Usuario no-root (HF recomienda UID 1000) con HOME escribible para caches
# de huggingface_hub, transformers y streamlit.
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias primero para aprovechar el cache de capas.
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiar el resto del codigo del proyecto.
COPY --chown=user:user . .

# DATA_DIR vive en /app/data; asegurar permisos de escritura para el usuario.
RUN chown -R user:user /app
USER user

EXPOSE 7860

CMD ["streamlit", "run", "dashboard/app.py", \
     "--server.port=7860", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=false"]
