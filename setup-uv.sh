#!/bin/bash

# Foam SSG Environment Setup Script using uv
# This script offers options to migrate from requirements.txt or use pyproject.toml

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

# Check if requirements-txt.txt exists
if [ -f "requirements-txt.txt" ]; then
    echo "📄 Found requirements-txt.txt file"
    echo "Choose setup method:"
    echo "1) Use requirements-txt.txt (recommended for existing setup)"
    echo "2) Use pyproject.toml (modern Python project)"
    read -p "Enter choice (1 or 2): " choice
    
    case $choice in
        1)
            echo "📦 Setting up with requirements-txt.txt..."
            
            # Create virtual environment
            if [ ! -d ".venv" ]; then
                echo "📦 Creating virtual environment..."
                uv venv
            fi
            
            # Install from requirements file
            echo "📥 Installing dependencies from requirements-txt.txt..."
            uv pip install -r requirements-txt.txt
            
            echo "✅ Setup complete using requirements-txt.txt!"
            ;;
        2)
            echo "📦 Setting up with pyproject.toml..."
            
            # Use uv sync for pyproject.toml
            if [ ! -f "uv.lock" ]; then
                echo "📦 Initializing uv project..."
                uv sync
            else
                echo "✅ uv project already initialized"
                echo "📥 Syncing dependencies..."
                uv sync
            fi
            
            echo "✅ Setup complete using pyproject.toml!"
            ;;
        *)
            echo "❌ Invalid choice. Please run the script again."
            exit 1
            ;;
    esac
else
    echo "📦 No requirements-txt.txt found, using pyproject.toml..."
    
    # Use uv sync for pyproject.toml
    if [ ! -f "uv.lock" ]; then
        echo "📦 Initializing uv project..."
        uv sync
    else
        echo "✅ uv project already initialized"
        echo "📥 Syncing dependencies..."
        uv sync
    fi
    
    echo "✅ Setup complete using pyproject.toml!"
fi

# Make setup scripts executable
chmod +x setup-uv.sh
if [ -f "setup.sh" ]; then
    chmod +x setup.sh
fi

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
if [ -f "uv.lock" ]; then
    echo "  uv run python foam-ssg.py /path/to/notes -o /path/to/output"
    echo "  uv run python foam-ssg.py /path/to/notes --serve"
else
    echo "  source .venv/bin/activate"
    echo "  python foam-ssg.py /path/to/notes -o /path/to/output"
    echo "  python foam-ssg.py /path/to/notes --serve"
fi
echo ""
echo "Optional: Set up PlantUML for diagram support:"
echo "  ./plantuml-setup.sh"
echo ""
echo "Dependencies installed:"
if [ -f "uv.lock" ]; then
    uv pip list
else
    source .venv/bin/activate && pip list
fi