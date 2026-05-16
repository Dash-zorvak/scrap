#!/bin/bash
set -e

echo "=== Scrapeo Social - Setup ==="

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
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
