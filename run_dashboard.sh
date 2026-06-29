#!/usr/bin/env bash
# Levanta el DASHBOARD DEL ALCALDE (solo lectura) y lo expone con el tunel de
# Cloudflare. La base de datos se queda en local; el tunel solo enruta el
# puerto 8501. Apaga todo con Ctrl + C.
#
# Requisitos previos (ver DESPLIEGUE.md):
#   - brew install cloudflared
#   - cloudflared tunnel create santaana-dashboard
#   - ~/.cloudflared/config.yml con ingress a http://localhost:8501
#   - Cloudflare Access con login por correo sobre el subdominio

set -e
cd "$(dirname "$0")"

# Nombre del tunel ya creado (cambialo si usaste otro).
TUNNEL_NAME="${TUNNEL_NAME:-santaana-dashboard}"
DASH_PORT="${DASH_PORT:-8501}"

echo "▶ Iniciando dashboard del alcalde en http://localhost:${DASH_PORT} ..."
streamlit run dashboard/app.py \
    --server.port "${DASH_PORT}" \
    --server.headless true \
    --server.address 127.0.0.1 &
DASH_PID=$!

# Al salir (Ctrl + C) cerramos tambien el dashboard.
trap 'echo; echo "■ Cerrando..."; kill $DASH_PID 2>/dev/null' EXIT

# Pequena espera para que Streamlit este listo antes de abrir el tunel.
sleep 4

echo "▶ Abriendo tunel de Cloudflare (${TUNNEL_NAME}) ..."
cloudflared tunnel run "${TUNNEL_NAME}"
