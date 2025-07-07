#!/bin/bash

# Foam SSG Environment Setup Script using uv
# This script sets up a Python environment and installs dependencies using uv

set -e  # Exit on any error

echo "🚀 Setting up Foam SSG environment with uv..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install uv first:"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "or visit: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

echo "✅ uv found: $(uv --version)"

# Initialize uv project if not already done
if [ ! -f "uv.lock" ]; then
    echo "📦 Initializing uv project..."
    uv sync
else
    echo "✅ uv project already initialized"
    echo "📥 Syncing dependencies..."
    uv sync
fi

# Make setup script executable
chmod +x setup.sh

# Make PlantUML setup script executable if it exists
if [ -f "plantuml-setup.sh" ]; then
    chmod +x plantuml-setup.sh
    echo "✅ Made plantuml-setup.sh executable"
fi

# Show instructions
echo ""
echo "🎉 Setup complete!"
echo ""
echo "To run Foam SSG:"
echo "  uv run python foam-ssg.py /path/to/notes -o /path/to/output"
echo "  uv run python foam-ssg.py /path/to/notes --serve"
echo ""
echo "Or activate the virtual environment:"
echo "  source .venv/bin/activate"
echo "  python foam-ssg.py /path/to/notes -o /path/to/output"
echo ""
echo "Optional: Set up PlantUML for diagram support:"
echo "  ./plantuml-setup.sh"
echo ""
echo "To add development dependencies:"
echo "  uv add --dev pytest black flake8 mypy"
echo ""
echo "Dependencies installed:"
uv pip list