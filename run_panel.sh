#!/usr/bin/env bash
# Levanta el PANEL DE CARGA del analista en el puerto 8502.
#
#   - LOCAL: abre http://localhost:8502 en tu Mac.
#   - REMOTO (opcional, desde el celular): además necesitas el túnel corriendo
#     (lo levanta run_dashboard.sh) y haber configurado el subdominio del panel
#     en ~/.cloudflared/config.yml + una app de Cloudflare Access que permita
#     SOLO tu correo. Ver la sección 7 de DESPLIEGUE.md.
#
# El panel ESCRIBE en la DB LOCAL (config.py). Mantén su acceso restringido a ti.

set -e
cd "$(dirname "$0")"

PANEL_PORT="${PANEL_PORT:-8502}"

echo "▶ Panel de carga en http://localhost:${PANEL_PORT}"
echo "  Para subir desde el celular: ten el túnel arriba (run_dashboard.sh) y"
echo "  entra a tu subdominio del panel protegido con Cloudflare Access (DESPLIEGUE.md §7)."
streamlit run dashboard/panel_carga.py \
    --server.port "${PANEL_PORT}" \
    --server.address 127.0.0.1
