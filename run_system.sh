#!/bin/bash

# Dynamic Context Ingestion System Startup Script

echo "🚀 Starting Integrated Lending Chatbot with Dynamic Context"
echo "=========================================================="

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: Please run this script from the integrated-lending-chatbot directory"
    exit 1
fi

# Check Python dependencies
echo "📦 Checking Python dependencies..."
if ! python -c "import fastapi, anthropic, chromadb, neo4j, mem0" 2>/dev/null; then
    echo "⚠️  Installing Python dependencies..."
    pip install -r requirements.txt
fi

# Check if frontend is built
if [ ! -d "frontend/dist" ]; then
    echo "🔨 Building frontend..."
    cd frontend
    if [ ! -d "node_modules" ]; then
        echo "📦 Installing Node.js dependencies..."
        npm install
    fi
    npm run build
    cd ..
fi

# Check environment variables
echo "🔧 Checking environment configuration..."
if [ ! -f ".env" ]; then
    echo "⚠️  Creating .env file template..."
    cat > .env << EOF
# Anthropic API Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# Mem0 Configuration
MEM0_API_KEY=your_mem0_api_key_here

# Application Configuration
LENDING_CONTEXT_PATH=./Lending
MAX_CONTEXT_ITEMS=8
EOF
    echo "📝 Please edit .env file with your API keys and configuration"
    echo "   Required: ANTHROPIC_API_KEY"
    echo "   Optional: NEO4J_* (for graph features), MEM0_API_KEY (for enhanced memory)"
fi

# Check for required API keys
source .env
if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "your_anthropic_api_key_here" ]; then
    echo "❌ Error: ANTHROPIC_API_KEY is required in .env file"
    echo "   Get your API key from: https://console.anthropic.com/"
    exit 1
fi

# Start the system
echo "🎯 Starting backend server..."
echo "   API will be available at: http://localhost:8000"
echo "   Frontend will be available at: http://localhost:8000"
echo ""
echo "📋 Available endpoints:"
echo "   • Chat: POST /api/chat"
echo "   • Upload Files: POST /api/dynamic-context/upload"
echo "   • Process URL: POST /api/dynamic-context/url"
echo "   • Process GitHub: POST /api/dynamic-context/github"
echo "   • System Health: GET /api/health"
echo "   • System Stats: GET /api/stats"
echo ""
echo "🔍 To test the system, run: python test_dynamic_context.py"
echo "📖 For detailed documentation, see: DYNAMIC_CONTEXT_README.md"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================================="

# Start the FastAPI server
python main.py