#!/bin/bash

echo "================================"
echo "Installing Telegram AI Bot"
echo "================================"
echo ""

echo "[1/3] Installing Python packages..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error installing packages!"
    exit 1
fi

echo ""
echo "[2/3] Installing Playwright browsers..."
playwright install chromium
if [ $? -ne 0 ]; then
    echo "Error installing Playwright!"
    exit 1
fi

echo ""
echo "[3/3] Setting up configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo ".env file created! Please edit it with your credentials."
else
    echo ".env file already exists."
fi

echo ""
echo "================================"
echo "Installation complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your credentials"
echo "2. Run: python setup.py (to verify setup)"
echo "3. Run: python main.py (to start the bot)"
echo ""

