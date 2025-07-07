#!/bin/bash
# Setup script for PlantUML pre-rendering support

echo "Setting up PlantUML for Foam SSG..."

# Check if Java is installed
if ! command -v java &> /dev/null; then
    echo "Error: Java is required for PlantUML. Please install Java first."
    echo "  Ubuntu/Debian: sudo apt install default-jre"
    echo "  macOS: brew install openjdk"
    echo "  Windows: Download from https://www.java.com"
    exit 1
fi

# Check if Graphviz (dot) is installed
if ! command -v dot &> /dev/null; then
    echo "Installing Graphviz (required for PlantUML diagrams)..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install graphviz
        else
            echo "Error: Homebrew not found. Please install Graphviz manually:"
            echo "  brew install graphviz"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt &> /dev/null; then
            sudo apt update && sudo apt install -y graphviz
        elif command -v yum &> /dev/null; then
            sudo yum install -y graphviz
        elif command -v pacman &> /dev/null; then
            sudo pacman -S graphviz
        else
            echo "Error: Package manager not found. Please install Graphviz manually:"
            echo "  Ubuntu/Debian: sudo apt install graphviz"
            echo "  RHEL/CentOS: sudo yum install graphviz"
            echo "  Arch: sudo pacman -S graphviz"
            exit 1
        fi
    else
        echo "Error: Unsupported OS. Please install Graphviz manually."
        exit 1
    fi
else
    echo "Graphviz already installed ✓"
fi

# Create tools directory
mkdir -p ~/foam-ssg-tools
cd ~/foam-ssg-tools

# Download PlantUML
echo "Downloading PlantUML..."
wget -O plantuml.jar "https://github.com/plantuml/plantuml/releases/download/v1.2024.0/plantuml-1.2024.0.jar"

# Create plantuml wrapper script
cat > plantuml << 'EOF'
#!/bin/bash
java -jar ~/foam-ssg-tools/plantuml.jar "$@"
EOF

chmod +x plantuml

# Add to PATH
echo "Adding PlantUML to PATH..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo 'export PATH="$HOME/foam-ssg-tools:$PATH"' >> ~/.zshrc
    echo "Please run: source ~/.zshrc"
else
    # Linux
    echo 'export PATH="$HOME/foam-ssg-tools:$PATH"' >> ~/.bashrc
    echo "Please run: source ~/.bashrc"
fi

echo "PlantUML setup complete!"
echo ""
echo "Test with: plantuml -version"
echo ""
echo "PlantUML diagrams will now be pre-rendered when building your site."