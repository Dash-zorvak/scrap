#!/usr/bin/env bash
# Levanta el PANEL DE CARGA del analista. SOLO LOCAL: no se enruta por el tunel
# de Cloudflare, asi que el alcalde nunca lo ve. Operas sobre la misma DB local.
#
# Uso:
#   ./run_panel.sh
#   Luego abre http://localhost:8502 en tu navegador.

set -e
cd "$(dirname "$0")"

PANEL_PORT="${PANEL_PORT:-8502}"

echo "▶ Panel de carga (solo local) en http://localhost:${PANEL_PORT}"
streamlit run dashboard/panel_carga.py \
    --server.port "${PANEL_PORT}" \
    --server.address 127.0.0.1
