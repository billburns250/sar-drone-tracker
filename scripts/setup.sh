#!/bin/bash

# SAR Drone Tracker - Initial Setup Script
# Run this after cloning the repository

set -e  # Exit on any error

echo "🚁 SAR Drone Tracker - Initial Setup"
echo "====================================="

# Check if we're in the right directory
if [ ! -f "README.md" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    echo "Please install Python 3.8 or newer"
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r config/requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp config/.env.template .env
    echo "✅ .env file created - PLEASE EDIT IT WITH YOUR API CREDENTIALS"
else
    echo "✅ .env file already exists"
fi

# Make scripts executable
echo "🔐 Making scripts executable..."
chmod +x scripts/*.sh

# Create logs directory
echo "📁 Creating logs directory..."
mkdir -p logs

# Run basic tests
echo "🧪 Running basic tests..."
if python -c "import src.caltopo_client; print('✅ CalTopo client imports successfully')"; then
    echo "✅ Basic module tests passed"
else
    echo "❌ Basic module tests failed"
    exit 1
fi

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit the .env file with your API credentials:"
echo "   nano .env"
echo ""
echo "2. Test your CalTopo integration:"
echo "   python test_caltopo_integration.py"
echo ""
echo "3. Once working, commit your initial setup:"
echo "   git add ."
echo "   git commit -m 'Initial project setup'"
echo "   git push origin main"
echo ""
echo "For help setting up API credentials, see:"
echo "   docs/api-setup.md"
echo ""
echo "📚 Documentation available at:"
echo "   https://github.com/[your-org]/sar-drone-tracker/tree/main/docs"
