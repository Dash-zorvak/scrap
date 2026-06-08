#!/bin/bash
set -e

echo "=== Scrapeo Social - Setup ==="

# Elegir intérprete soportado (3.11 preferido; 3.14 aún no tiene wheels para numpy/pandas/lxml)
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "ERROR: '$PYTHON_BIN' no encontrado."
    echo "Instalá Python 3.11 (pyenv install 3.11 / brew install python@3.11 / apt install python3.11-venv)"
    echo "o exportá la ruta: PYTHON_BIN=/ruta/a/python3.11 ./setup.sh"
    exit 1
fi

TARGET_VER="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

# Recrear el venv si no existe o si quedó con otra versión de Python
if [ -d "venv" ]; then
    CURRENT_VER="$(venv/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "")"
    if [ "$CURRENT_VER" != "$TARGET_VER" ]; then
        echo "venv existente usa Python '$CURRENT_VER', se requiere '$TARGET_VER'. Recreando..."
        rm -rf venv
    fi
fi

if [ ! -d "venv" ]; then
    echo "Creating virtual environment with $PYTHON_BIN (Python $TARGET_VER)..."
    "$PYTHON_BIN" -m venv venv
fi

source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium

# Copy env file
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env from .env.example - please configure it!"
fi

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env with your configuration"
echo "  2. Activate environment: source venv/bin/activate"
echo "  3. Run: python -m src.main scrape"
echo "  4. Analyze: python -m src.main analyze"
