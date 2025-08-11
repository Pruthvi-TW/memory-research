# Deployment Guide - Dynamic Context Ingestion System

## Quick Start

### 1. Prerequisites

- **Python 3.8+** with pip
- **Node.js 16+** with npm
- **Neo4j Database** (optional, for graph features)
- **Anthropic API Key** (required)

### 2. Installation

```bash
# Clone and navigate to the project
cd integrated-lending-chatbot

# Install Python dependencies
pip install -r requirements.txt

# Install and build frontend
cd frontend
npm install
npm run build
cd ..

# Make startup script executable
chmod +x run_system.sh
```

### 3. Configuration

Create a `.env` file in the project root:

```bash
# Required: Anthropic API Key
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Neo4j Configuration (for graph features)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# Optional: Mem0 Configuration (for enhanced memory)
MEM0_API_KEY=your_mem0_api_key_here

# Optional: Application Configuration
LENDING_CONTEXT_PATH=./Lending
MAX_CONTEXT_ITEMS=8
MAX_FILE_SIZE=10485760
MAX_CONCURRENT_TASKS=5
```

### 4. Start the System

```bash
# Using the startup script (recommended)
./run_system.sh

# Or directly with Python
python main.py
```

### 5. Access the Application

- **Frontend**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

## Detailed Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | ✅ | - | Anthropic Claude API key |
| `NEO4J_URI` | ❌ | `bolt://localhost:7687` | Neo4j database URI |
| `NEO4J_USER` | ❌ | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | ❌ | `password` | Neo4j password |
| `MEM0_API_KEY` | ❌ | - | Mem0 API key for enhanced memory |
| `LENDING_CONTEXT_PATH` | ❌ | `./Lending` | Path to base lending documentation |
| `MAX_CONTEXT_ITEMS` | ❌ | `8` | Maximum context items per query |
| `MAX_FILE_SIZE` | ❌ | `10485760` | Max file size in bytes (10MB) |
| `MAX_FILES_PER_UPLOAD` | ❌ | `10` | Maximum files per upload |
| `MAX_CONCURRENT_TASKS` | ❌ | `5` | Maximum concurrent processing tasks |
| `CHUNK_SIZE` | ❌ | `1000` | Text chunk size for processing |
| `VECTOR_WEIGHT` | ❌ | `0.6` | Weight for vector similarity in fusion |
| `GRAPH_WEIGHT` | ❌ | `0.4` | Weight for graph relevance in fusion |
| `HOST` | ❌ | `0.0.0.0` | Server host |
| `PORT` | ❌ | `8000` | Server port |
| `DEBUG` | ❌ | `false` | Enable debug mode |
| `LOG_LEVEL` | ❌ | `INFO` | Logging level |

### Feature Configuration

The system automatically enables/disables features based on available configuration:

- **Neo4j Graph Database**: Enabled if `NEO4J_PASSWORD` is set and not default
- **Mem0 Enhanced Memory**: Enabled if `MEM0_API_KEY` is provided
- **File Upload**: Always enabled
- **URL Processing**: Always enabled
- **GitHub Processing**: Always enabled

## Production Deployment

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy and build frontend
COPY frontend/ ./frontend/
RUN cd frontend && npm install && npm run build

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Start the application
CMD ["python", "main.py"]
```

Build and run:

```bash
docker build -t lending-chatbot .
docker run -p 8000:8000 --env-file .env lending-chatbot
```

### Docker Compose with Neo4j

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.14
    environment:
      NEO4J_AUTH: neo4j/your_password_here
      NEO4J_PLUGINS: '["apoc"]'
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data

  chatbot:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=your_anthropic_api_key_here
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=your_password_here
    depends_on:
      - neo4j
    volumes:
      - ./Lending:/app/Lending
      - chroma_data:/app/vector/chroma_db

volumes:
  neo4j_data:
  chroma_data:
```

Start with:

```bash
docker-compose up -d
```

### Kubernetes Deployment

Create `k8s-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lending-chatbot
spec:
  replicas: 2
  selector:
    matchLabels:
      app: lending-chatbot
  template:
    metadata:
      labels:
        app: lending-chatbot
    spec:
      containers:
      - name: chatbot
        image: lending-chatbot:latest
        ports:
        - containerPort: 8000
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: chatbot-secrets
              key: anthropic-api-key
        - name: NEO4J_URI
          value: "bolt://neo4j-service:7687"
        volumeMounts:
        - name: chroma-storage
          mountPath: /app/vector/chroma_db
      volumes:
      - name: chroma-storage
        persistentVolumeClaim:
          claimName: chroma-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: lending-chatbot-service
spec:
  selector:
    app: lending-chatbot
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Performance Optimization

### System Resources

**Minimum Requirements:**
- CPU: 2 cores
- RAM: 4GB
- Storage: 10GB

**Recommended for Production:**
- CPU: 4+ cores
- RAM: 8GB+
- Storage: 50GB+ SSD

### Database Optimization

**Neo4j:**
```bash
# In neo4j.conf
dbms.memory.heap.initial_size=2G
dbms.memory.heap.max_size=4G
dbms.memory.pagecache.size=2G
```

**Chroma:**
- Use SSD storage for vector database
- Consider distributed deployment for large datasets

### Application Tuning

```bash
# Increase processing limits for high-volume usage
MAX_CONCURRENT_TASKS=10
MAX_FILE_SIZE=52428800  # 50MB
CHUNK_SIZE=1500
```

## Monitoring and Logging

### Health Monitoring

Set up monitoring for these endpoints:
- `GET /api/health` - Overall system health
- `GET /api/stats` - System statistics
- `GET /api/dynamic-context/stats` - Processing statistics

### Logging Configuration

```bash
# Enhanced logging
LOG_LEVEL=DEBUG
LOG_FILE=/var/log/lending-chatbot.log
```

### Metrics Collection

The system exposes metrics through:
- Processing task statistics
- Context retrieval performance
- Database connection status
- Memory usage patterns

## Security Considerations

### API Security

1. **API Key Management**: Store API keys securely using environment variables or secret management systems
2. **CORS Configuration**: Restrict CORS origins in production
3. **Rate Limiting**: Implement rate limiting for API endpoints
4. **Input Validation**: All inputs are validated before processing

### File Upload Security

1. **File Type Validation**: Only allowed file types are processed
2. **Size Limits**: Configurable file size limits prevent abuse
3. **Content Scanning**: Files are scanned for malicious content
4. **Sandboxed Processing**: File processing runs in isolated environments

### Database Security

1. **Neo4j**: Use authentication and encrypted connections
2. **Chroma**: Secure file system permissions for vector storage
3. **Mem0**: API key-based authentication

## Troubleshooting

### Common Issues

**1. Configuration Errors**
```bash
# Check configuration
python config.py

# Validate environment
python -c "from config import validate_environment; print(validate_environment())"
```

**2. Database Connection Issues**
```bash
# Test Neo4j connection
python -c "from graph.neo4j_service import Neo4jService; import asyncio; asyncio.run(Neo4jService().test_connection())"

# Check Chroma database
python -c "from vector.vector_service import VectorService; print(VectorService().get_collection_info())"
```

**3. Processing Failures**
```bash
# Check processing status
curl http://localhost:8000/api/dynamic-context/stats

# View system insights
curl http://localhost:8000/api/dynamic-context/insights
```

**4. Memory Issues**
```bash
# Clean up old tasks
curl -X DELETE http://localhost:8000/api/dynamic-context/cleanup

# Monitor system resources
curl http://localhost:8000/api/stats
```

### Debug Mode

Enable debug mode for detailed logging:

```bash
DEBUG=true
LOG_LEVEL=DEBUG
python main.py
```

### Testing

Run the comprehensive test suite:

```bash
# Test all functionality
python test_dynamic_context.py

# Run specific tests
python -m pytest tests/ -v
```

## Backup and Recovery

### Data Backup

**Neo4j Database:**
```bash
neo4j-admin dump --database=neo4j --to=/backup/neo4j-backup.dump
```

**Chroma Vector Store:**
```bash
tar -czf chroma-backup.tar.gz vector/chroma_db/
```

**Configuration:**
```bash
cp .env .env.backup
```

### Recovery

**Restore Neo4j:**
```bash
neo4j-admin load --from=/backup/neo4j-backup.dump --database=neo4j --force
```

**Restore Chroma:**
```bash
tar -xzf chroma-backup.tar.gz
```

## Scaling

### Horizontal Scaling

1. **Load Balancer**: Use nginx or cloud load balancer
2. **Multiple Instances**: Run multiple application instances
3. **Shared Storage**: Use shared storage for Chroma database
4. **Database Clustering**: Use Neo4j clustering for high availability

### Vertical Scaling

1. **Increase Resources**: Add more CPU and RAM
2. **Optimize Configuration**: Tune processing limits
3. **Database Tuning**: Optimize database configurations

## Support

For issues and questions:

1. Check the logs for error messages
2. Review the configuration with `python config.py`
3. Run the test suite with `python test_dynamic_context.py`
4. Check system health at `/api/health`
5. Review system insights at `/api/dynamic-context/insights`

## Version History

- **v2.1.0**: Dynamic context ingestion system with enhanced configuration
- **v2.0.0**: Multi-layer integration with Mem0, Neo4j, and Chroma
- **v1.0.0**: Basic lending chatbot with static context