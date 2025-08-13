# FStratum Chatbot

An AI-powered financial assistant with dynamic context ingestion capabilities. The system combines vector search, graph database relationships, and memory layers to provide intelligent responses based on financial domain knowledge.

## 🏗️ Architecture

```
fstratum-chatbot/
├── core/                          # Core system components
│   ├── ai/                        # AI and memory services
│   │   ├── chat_service.py        # Anthropic Claude integration
│   │   ├── mem0_manager.py        # Memory layer management
│   │   └── mem0_integration_service.py
│   ├── database/                  # Data storage services
│   │   ├── vector_service.py      # ChromaDB vector operations
│   │   ├── neo4j_service.py       # Graph database operations
│   │   └── context_repository.py  # Context management
│   └── processing/                # Content processing
│       ├── file_upload_handler.py # File processing
│       ├── url_content_extractor.py # URL content extraction
│       └── github_repository_processor.py # GitHub integration
├── services/                      # Business logic services
├── models/                        # Data models and schemas
├── frontend/                      # React frontend application
├── tests/                         # Unit and integration tests
└── main.py                        # FastAPI application entry point
```

### Processing Flow
```
[User] → [Frontend] → [Dynamic Context] → [AI Memory] → [Vector DB] → [Graph DB] → [Claude API] → [Response]
                           ↓
                    [Files/URLs/GitHub]
```

### Core Components

1. **AI Layer**: Chat service with Anthropic Claude and memory management
2. **Database Layer**: Vector search (ChromaDB) and graph relationships (Neo4j)
3. **Processing Layer**: Dynamic content ingestion from multiple sources
4. **Frontend**: React-based chat interface with file upload capabilities

### Enhanced Context Retrieval Strategy with mem0

1. **mem0 Semantic Memory**: Retrieve relevant context from persistent semantic memory
2. **Vector Search**: Use Chroma DB to find semantically similar documents
3. **Graph Enhancement**: Enrich results using Neo4j relationship traversal
4. **Conversation Context**: Include relevant conversation history from mem0
5. **Enhanced Fusion**: Advanced scoring combining all context sources
6. **LLM Generation**: Generate responses using the multi-layered enriched context

## 📁 Project Structure

```
integrated-lending-chatbot/
├── frontend/                   # React frontend application
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── services/          # API services
│   │   └── App.tsx           # Main application
│   └── package.json
├── mem0/                      # mem0 semantic memory layer
│   ├── mem0_manager.py       # mem0 memory operations
│   ├── mem0_context_extractor.py # Lending context extraction
│   ├── mem0_integration_service.py # Multi-layer integration
│   ├── mem0_config.py        # Configuration management
│   └── README.md             # mem0 layer documentation
├── vector/                    # Vector store implementation
│   ├── vector_service.py     # Chroma DB operations
│   ├── document_processor.py # Document processing
│   └── embeddings.py        # Embedding utilities
├── graph/                    # Graph database implementation
│   ├── neo4j_service.py     # Neo4j operations
│   ├── context_repository.py # Graph data access
│   └── schema.py            # Graph schema
├── services/                 # Business logic layer
│   ├── integration_service.py # Vector + Graph integration
│   ├── chat_service.py       # LLM integration
│   └── context_service.py    # Context orchestration
├── models/                   # Data models
│   └── chat_models.py       # Pydantic models
├── Lending/                  # Lending context directory
│   ├── Capabilities/         # Capability-specific content
│   └── CommonPrompts/        # Shared guidelines
├── main.py                   # FastAPI application
├── requirements.txt          # Python dependencies
└── .env.example             # Environment variables template
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 18+ and npm
- Neo4j Database (Community Edition or Desktop)
- Qdrant Vector Database (for mem0)
- Anthropic API Key

### Installation

1. **Setup environment**:
   ```bash
   cd integrated-lending-chatbot
   cp .env.example .env
   # Edit .env with your credentials:
   # - NEO4J_PASSWORD=your_neo4j_password
   # - ANTHROPIC_API_KEY=your_anthropic_key
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install and build frontend**:
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

4. **Start databases**:
   ```bash
   # Start Neo4j database
   # If using Neo4j Desktop, start your database
   # If using Community Edition:
   neo4j start
   
   # Start Qdrant for mem0 (using Docker)
   docker run -p 6333:6333 qdrant/qdrant
   ```

5. **Start the application**:
   ```bash
   python main.py
   # Application will be available at http://localhost:8000
   ```

6. **Initialize context** (via web interface or API):
   - **Web Interface**: Click "Initialize Context" button in the chat interface
   - **API**: 
     ```bash
     curl -X POST "http://localhost:8000/api/initialize-context" \
          -H "Content-Type: application/json" \
          -d '{"lending_path": "../Lending"}'
     ```

### Development Mode

For development with hot reload:

```bash
# Terminal 1: Start backend with reload
uvicorn main:app --reload --port 8000

# Terminal 2: Start React dev server
cd frontend
npm run dev
# Frontend will be available at http://localhost:3000
```

## 🔄 Integration Benefits

### Vector + Graph Synergy

1. **Semantic Discovery**: Vector search finds conceptually similar content
2. **Relationship Enhancement**: Graph traversal discovers related concepts and flows
3. **Context Ranking**: Combined scoring provides better relevance ranking
4. **Comprehensive Coverage**: Ensures both semantic and structural relationships are captured

### Enhanced Query Processing

- **Multi-modal Search**: Combines text similarity with relationship strength
- **Context Expansion**: Graph relationships expand the context beyond direct matches
- **Relevance Scoring**: Weighted combination of vector similarity and graph centrality
- **Dynamic Context**: Adapts context based on conversation history stored in graph

## 📊 Performance Optimizations

- **Hybrid Indexing**: Vector embeddings + Neo4j indexes
- **Caching Strategy**: Redis for frequently accessed contexts
- **Batch Processing**: Efficient document processing and embedding generation
- **Connection Pooling**: Optimized database connections

## 🔧 API Endpoints

### Chat Endpoint
```bash
POST /api/chat
{
  "message": "How does eKYC verification work?",
  "session_id": "optional-session-id"
}
```

### Initialize Context
```bash
POST /api/initialize-context
{
  "lending_path": "../Lending"
}
```

### Health Check
```bash
GET /api/health
```

## 🛠️ Development

### Running in Development Mode

```bash
# Terminal 1: Start backend with hot reload
uvicorn main:app --reload --port 8000

# Terminal 2: Start React dev server
cd frontend
npm run dev
```

### Testing the Integration

```bash
# Test vector search
curl -X POST "http://localhost:8000/api/test/vector-search" \
     -H "Content-Type: application/json" \
     -d '{"query": "eKYC verification process"}'

# Test graph search
curl -X POST "http://localhost:8000/api/test/graph-search" \
     -H "Content-Type: application/json" \
     -d '{"query": "PAN validation"}'

# Test integrated search
curl -X POST "http://localhost:8000/api/test/integrated-search" \
     -H "Content-Type: application/json" \
     -d '{"query": "document verification workflow"}'
```

## 📈 Monitoring & Analytics

- **Query Performance**: Track vector search and graph query times
- **Context Quality**: Monitor relevance scores and user feedback
- **System Health**: Database connections, embedding model status
- **Usage Patterns**: Popular queries and context utilization

## 🔒 Security & Compliance

- **Data Privacy**: PII masking in logs and responses
- **API Security**: Rate limiting and authentication
- **Database Security**: Encrypted connections and access controls
- **Audit Trail**: Complete conversation and context usage logging