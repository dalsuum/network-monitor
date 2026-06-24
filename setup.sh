#!/bin/bash

echo "================================================"
echo "  Network Monitor - Installation Script"
echo "================================================"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "âŒ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "âœ“ Python 3 found: $(python3 --version)"
echo ""

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "âŒ pip3 is not installed. Please install pip3."
    exit 1
fi

echo "âœ“ pip3 found"
echo ""

# Install requirements
echo "ðŸ“¦ Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "âœ“ Dependencies installed successfully"
else
    echo "âŒ Failed to install dependencies"
    exit 1
fi

echo ""
echo "================================================"
echo "  Installation Complete!"
echo "================================================"
echo ""
echo "To start the application, run:"
echo "  python3 app.py"
echo ""
echo "Then open your browser to:"
echo "  http://localhost:5002"
echo ""
echo "Login:"
echo "  Username: admin"
echo "  Password: set ADMIN_PASSWORD in .env"
echo ""
echo "IMPORTANT: Do not commit .env or real credentials."
echo ""
