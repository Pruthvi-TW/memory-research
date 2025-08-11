# Dynamic Context Ingestion System

## Overview

The Dynamic Context Ingestion System allows you to add new context to your lending chatbot in real-time without restarting the system. It supports three types of content sources:

- **📁 File Uploads**: PDF, DOCX, TXT, and Markdown files
- **🌐 URL Content**: Web pages and documentation
- **🐙 GitHub Repositories**: Documentation and code files

## Architecture

```
User Input (Files/URLs/GitHub) 
    ↓
Dynamic Context Service
    ↓
Content Extraction & Chunking
    ↓
Parallel Storage:
├── Mem0 (Semantic Memory)
├── Neo4j (Graph Relationships) 
└── Chroma (Vector Embeddings)
    ↓
Enhanced Context Retrieval
    ↓
LLM Response Generation
```

## Features

### ✨ Real-time Processing
- Content is processed asynchronously in the background
- Continue chatting while content is being ingested
- Real-time status updates and progress tracking

### 🔄 Multi-layer Integration
- **Memory Layer (Mem0)**: Stores semantic memories and conversation context
- **Vector Store (Chroma)**: Enables similarity-based content retrieval
- **Graph Database (Neo4j)**: Maintains relationships between concepts

### 🎯 Enhanced Context Fusion
- Combines results from all three storage layers
- Intelligent scoring system that weighs different context sources
- Deduplication and relevance ranking

### 📊 Content Management
- Track all uploaded content with status indicators
- View processing statistics and system insights
- Content sidebar shows upload history and status

## How to Use

### 1. Start the System

```bash
# Backend
cd integrated-lending-chatbot
python main.py

# Frontend (in another terminal)
cd frontend
npm run dev
```

### 2. Initialize Base Context

Click "Initialize Context" to load the base lending documentation.

### 3. Add Dynamic Content

Click "Add Dynamic Context" and choose your source:

#### 📁 File Upload
- Supports: PDF, DOCX, TXT, MD files
- Max file size: 10MB per file
- Max files: 10 files at once

#### 🌐 URL Processing
- Extracts content from web pages
- Supports HTML, plain text, and structured content
- Automatically handles redirects and content type detection

#### 🐙 GitHub Repository
- Processes documentation files (.md, .txt, .rst)
- Extracts README files, docs folders, and code comments
- Supports both public and accessible private repositories

### 4. Monitor Processing

- View real-time status in the content sidebar
- Processing typically takes 5-30 seconds depending on content size
- Status indicators: ⏳ Processing → ✅ Completed / ❌ Failed

### 5. Chat with Enhanced Context

Once content is processed, it's immediately available for chat responses. The system will:
- Search across all content sources
- Combine results using fusion scoring
- Provide context-aware responses

## API Endpoints

### Content Processing
- `POST /api/dynamic-context/upload` - Upload files
- `POST /api/dynamic-context/url` - Process URL
- `POST /api/dynamic-context/github` - Process GitHub repo

### Status & Management
- `GET /api/dynamic-context/status/{task_id}` - Check processing status
- `GET /api/dynamic-context/stats` - System statistics
- `GET /api/dynamic-context/insights` - Content insights and recommendations
- `GET /api/dynamic-context/supported-types` - Supported file types

### Batch Processing
- `POST /api/dynamic-context/batch` - Process multiple sources
- `DELETE /api/dynamic-context/cleanup` - Clean up old tasks

## Configuration

### File Upload Limits
```python
max_file_size = 10 * 1024 * 1024  # 10MB
max_url_content_size = 5 * 1024 * 1024  # 5MB
max_concurrent_tasks = 5
```

### Supported File Types
- **Documents**: PDF, DOCX, TXT, MD
- **Web Content**: HTML, XML, JSON
- **GitHub Files**: .md, .txt, .py, .js, .json, .yml, .rst

### Processing Pipeline
1. **Extraction**: Content is extracted based on file type
2. **Chunking**: Content is split into manageable chunks (500-1000 chars)
3. **Vectorization**: Chunks are converted to embeddings
4. **Storage**: Parallel storage in Mem0, Chroma, and Neo4j
5. **Indexing**: Content becomes searchable immediately

## Testing

Run the test suite to verify system functionality:

```bash
python test_dynamic_context.py
```

This will test:
- System health and initialization
- File upload processing
- URL content extraction
- GitHub repository processing
- Chat integration with dynamic content
- System insights and analytics

## Troubleshooting

### Common Issues

#### Processing Fails
- Check file format is supported
- Verify file size is under limits
- Ensure URL is accessible
- Check GitHub repository is public or accessible

#### Content Not Appearing in Chat
- Wait for processing to complete (check status)
- Verify content was successfully stored (check insights)
- Try asking more specific questions related to the content

#### Performance Issues
- Clean up old tasks: `DELETE /api/dynamic-context/cleanup`
- Monitor system resources
- Consider reducing concurrent processing tasks

### Debug Information

Check the backend logs for detailed processing information:
- Content extraction details
- Storage operation results
- Error messages and stack traces

### System Health

Monitor system health via:
- `GET /api/health` - Overall system status
- `GET /api/dynamic-context/stats` - Processing statistics
- `GET /api/dynamic-context/insights` - Content analysis

## Best Practices

### Content Selection
- Upload relevant, high-quality documentation
- Use descriptive filenames
- Organize content by topic or capability

### Processing Optimization
- Process content in batches when possible
- Monitor system resources during large uploads
- Clean up completed tasks regularly

### Chat Optimization
- Ask specific questions about uploaded content
- Reference document names or topics explicitly
- Use technical terms that appear in your content

## Advanced Features

### Batch Processing
Process multiple sources simultaneously:

```json
{
  "sources": [
    {"type": "upload", "files": [...]},
    {"type": "url", "url": "https://example.com"},
    {"type": "github", "repo_url": "https://github.com/user/repo"}
  ]
}
```

### Content Validation
Validate sources before processing:

```json
POST /api/dynamic-context/validate
{
  "source_type": "url",
  "source_data": {"url": "https://example.com"}
}
```

### System Analytics
Get detailed insights about content usage:

```json
GET /api/dynamic-context/insights
```

Returns processing statistics, content analysis, and optimization recommendations.

## Integration with Existing System

The dynamic context system seamlessly integrates with:
- **Existing Vector Store**: New content is added to the same Chroma collection
- **Memory Layer**: Mem0 manages both static and dynamic memories
- **Graph Database**: Neo4j relationships include dynamic content
- **Chat Service**: Enhanced context retrieval uses all content sources

## Security Considerations

- File uploads are validated for type and size
- URLs are checked for safety and accessibility
- GitHub repositories must be publicly accessible
- Content is processed in isolated environments
- No sensitive data is logged or stored permanently

## Performance Metrics

Typical processing times:
- **Small files** (< 1MB): 5-10 seconds
- **Medium files** (1-5MB): 10-20 seconds
- **Large files** (5-10MB): 20-30 seconds
- **URLs**: 5-15 seconds
- **GitHub repos**: 15-60 seconds (depending on size)

## Future Enhancements

Planned improvements:
- Support for more file types (Excel, PowerPoint)
- Integration with cloud storage (Google Drive, Dropbox)
- Automatic content updates for URLs and repositories
- Advanced content preprocessing and filtering
- Multi-language content support