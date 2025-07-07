#!/bin/bash

# Foam SSG Environment Setup Script using mamba
# This script sets up a conda environment and installs dependencies using mamba

set -e  # Exit on any error

echo "🚀 Setting up Foam SSG environment with mamba..."

# Check if mamba is installed
if ! command -v mamba &> /dev/null; then
    echo "❌ mamba is not installed. Please install mamba first:"
    echo "Visit: https://mamba.readthedocs.io/en/latest/installation.html"
    echo "Or install via conda: conda install mamba -n base -c conda-forge"
    exit 1
fi

echo "✅ mamba found: $(mamba --version)"

# Environment name
ENV_NAME="foam-ssg"

# Check if environment already exists
if mamba env list | grep -q "^${ENV_NAME}"; then
    echo "📦 Environment '${ENV_NAME}' already exists"
    read -p "Do you want to remove and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Removing existing environment..."
        mamba env remove -n ${ENV_NAME}
    else
        echo "✅ Using existing environment"
    fi
fi

# Create environment if it doesn't exist
if ! mamba env list | grep -q "^${ENV_NAME}"; then
    echo "📦 Creating conda environment '${ENV_NAME}'..."
    mamba create -n ${ENV_NAME} python=3.11 -y
fi

# Activate environment and install dependencies
echo "📥 Installing dependencies..."
mamba activate ${ENV_NAME}

# Install Python packages
mamba install -n ${ENV_NAME} -c conda-forge -y \
    markdown \
    jinja2 \
    networkx \
    beautifulsoup4 \
    pygments

# Install python-frontmatter via pip (not available in conda-forge)
mamba run -n ${ENV_NAME} pip install python-frontmatter

# Make setup scripts executable
chmod +x setup-mamba.sh

# Make PlantUML setup script executable if it exists
if [ -f "plantuml-setup.sh" ]; then
    chmod +x plantuml-setup.sh
    echo "✅ Made plantuml-setup.sh executable"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To activate the environment:"
echo "  mamba activate ${ENV_NAME}"
echo ""
echo "To run Foam SSG:"
echo "  python foam-ssg.py /path/to/notes -o /path/to/output"
echo "  python foam-ssg.py /path/to/notes --serve"
echo ""
echo "Optional: Set up PlantUML for diagram support:"
echo "  ./plantuml-setup.sh"
echo ""
echo "To deactivate the environment:"
echo "  mamba deactivate"
echo ""
echo "To remove the environment:"
echo "  mamba env remove -n ${ENV_NAME}"
echo ""
echo "Dependencies installed:"
mamba list -n ${ENV_NAME}