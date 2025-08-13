# mem0 Memory Layer for Integrated Lending Chatbot

This directory contains the mem0 semantic memory layer that sits on top of the existing vector and graph layers, providing enhanced context retrieval and conversation memory.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    mem0 Memory Layer                        │
├─────────────────────────────────────────────────────────────┤
│  • Semantic Memory (mem0)                                  │
│  • Context Extraction                                      │
│  • Enhanced Integration                                     │
│  • Claude Chatbot with Memory                              │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                 Existing Layers                            │
├─────────────────────────────────────────────────────────────┤
│  • Vector Store (ChromaDB)                                 │
│  • Graph Database (Neo4j)                                  │
│  • Integration Service                                      │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Mem0 Manager (`mem0_manager.py`)
- **Purpose**: Manages semantic memory using mem0
- **Features**:
  - Stores lending context with metadata
  - Semantic search across stored memories
  - Conversation history tracking
  - Fallback to in-memory storage when mem0 unavailable
  - Memory export/import functionality

### 2. Mem0 Context Extractor (`mem0_context_extractor.py`)
- **Purpose**: Extracts structured context from Lending directory
- **Features**:
  - Reads capabilities, prompts, and OpenAPI specs
  - Validates directory structure
  - Provides context summaries
  - Compatible with existing lending folder format

### 3. Mem0 Integration Service (`mem0_integration_service.py`)
- **Purpose**: Combines mem0 with existing vector and graph layers
- **Features**:
  - Multi-source context retrieval
  - Enhanced fusion scoring
  - Concept extraction and storage
  - Performance analytics

### 4. Mem0 Configuration (`mem0_config.py`)
- **Purpose**: Centralized configuration management
- **Features**:
  - Environment-specific settings
  - Validation and defaults
  - Performance tuning parameters

## Installation

1. **Install mem0 and dependencies**:
```bash
pip install mem0ai qdrant-client
```

2. **Set up Qdrant (for mem0 vector store)**:
```bash
# Using Docker
docker run -p 6333:6333 qdrant/qdrant

# Or install locally
# Follow instructions at https://qdrant.tech/documentation/quick-start/
```

3. **Configure environment variables**:
```bash
# Required
export ANTHROPIC_API_KEY="your-claude-api-key"

# Optional (with defaults)
export QDRANT_HOST="localhost"
export QDRANT_PORT="6333"
export MEMORY_EMBEDDING_MODEL="all-MiniLM-L6-v2"
export LENDING_CONTEXT_PATH="./Lending"
export MAX_CONTEXT_ITEMS="8"
```

## Usage

### Integration with Main Application

The mem0 layer is integrated into the main FastAPI application in `main.py`.

### Integration with Main Application

The mem0 layer is automatically integrated into the main FastAPI application in `main.py`.

### API Endpoints

#### Memory Management
- `GET /api/memory/stats` - Get memory statistics
- `POST /api/memory/search` - Search memory content
- `POST /api/memory/clear` - Clear memory items
- `POST /api/memory/export` - Export memory data

#### Context Operations
- `GET /api/context/summary` - Get context overview
- `GET /api/context/validate` - Validate Lending directory
- `GET /api/capability/{name}` - Get capability details

#### Enhanced Chat
- `POST /api/chat` - Chat with enhanced context
- `POST /api/initialize-context` - Initialize all layers
- `POST /api/test/enhanced-search` - Test enhanced search

## Configuration

### mem0 Configuration

```python
{
    "embedder": {
        "provider": "huggingface",
        "config": {
            "model": "all-MiniLM-L6-v2"
        }
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "host": "localhost",
            "port": 6333
        }
    }
}
```

### Fusion Scoring Weights

The enhanced integration service uses weighted scoring:

- Memory Score: 25%
- Vector Score: 20%
- Graph Score: 20%
- Conversation Score: 10%
- Fusion Score: 15%
- Content Relevance: 30%
- Metadata Relevance: 15%
- Source Reliability: 10%
- Recency Factor: 5%

## Lending Directory Structure

The context extractor expects this structure:

```
Lending/
├── Capabilities/
│   ├── ekyc/
│   │   ├── original-prompt/
│   │   │   └── *.txt
│   │   ├── mock-prompt/
│   │   │   └── *.txt
│   │   ├── original-code/
│   │   │   └── swagger/
│   │   │       └── *.yaml
│   │   └── mock-code/
│   │       └── swagger/
│   │           └── *.yaml
│   └── pan/
│       └── ... (same structure)
├── CommonPrompts/
│   └── *.txt
└── *.yaml (OpenAPI specs)
```

## Data Flow

1. **Initialization**:
   - Extract context from Lending directory
   - Store in mem0 semantic memory
   - Initialize vector and graph stores

2. **Chat Request**:
   - Get context from mem0 memory
   - Get context from vector/graph layers
   - Apply enhanced fusion scoring
   - Generate response with Claude
   - Store conversation in memory

3. **Context Retrieval**:
   - Semantic search in mem0
   - Vector similarity search
   - Graph relationship traversal
   - Intelligent fusion and ranking

## Monitoring and Analytics

### Memory Statistics
- Total memories stored
- Breakdown by type (prompts, specs, conversations)
- Memory system status (mem0 vs fallback)

### Context Analytics
- Source distribution (memory, vector, graph)
- Fusion score effectiveness
- Query pattern analysis

### Performance Metrics
- Response times by layer
- Context retrieval accuracy
- Memory usage and growth

## Troubleshooting

### Common Issues

1. **mem0 not available**:
   - Install: `pip install mem0ai`
   - Check Qdrant connection
   - Falls back to in-memory storage

2. **Qdrant connection failed**:
   - Verify Qdrant is running on port 6333
   - Check firewall settings
   - Use Docker: `docker run -p 6333:6333 qdrant/qdrant`

3. **Context extraction failed**:
   - Verify Lending directory path
   - Check file permissions
   - Validate directory structure

4. **Claude API errors**:
   - Verify ANTHROPIC_API_KEY
   - Check API rate limits
   - Falls back to mock responses

### Debug Mode

Enable debug logging:

```bash
export FLASK_DEBUG=true
export LOG_LEVEL=DEBUG
```

### Testing

Test the memory system:

```bash
curl -X POST http://localhost:8000/api/test/memory-system \
  -H "Content-Type: application/json" \
  -d '{"query": "eKYC verification process"}'
```

## Future Enhancements

1. **Advanced Memory Features**:
   - Memory consolidation and summarization
   - Automatic memory cleanup
   - Memory versioning and rollback

2. **Enhanced Context Understanding**:
   - Multi-modal context (images, documents)
   - Temporal context awareness
   - User-specific memory profiles

3. **Performance Optimizations**:
   - Context caching strategies
   - Parallel context retrieval
   - Smart prefetching

4. **Integration Improvements**:
   - Real-time memory updates
   - Cross-session memory sharing
   - Memory-based recommendations