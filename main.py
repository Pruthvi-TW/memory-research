from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import logging
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv

# Import configuration
from config import config, validate_environment

# Set up logging
logging.basicConfig(
    level=getattr(logging, config.logging.log_level),
    format=config.logging.log_format,
    filename=config.logging.log_file
)
logger = logging.getLogger(__name__)

from vector.vector_service import VectorService
from graph.neo4j_service import Neo4jService
from graph.context_repository import ContextRepository
from services.integration_service import IntegrationService
from services.chat_service import ChatService
from services.context_service import ContextService
from models.chat_models import ChatRequest, ChatResponse, InitializeRequest
from models.dynamic_context_models import (
    FileUploadRequest, URLProcessingRequest, GitHubProcessingRequest,
    DynamicContextResponse, ProcessingStatusResponse, ValidationResult,
    SupportedTypesResponse, BatchProcessingRequest, BatchProcessingResponse,
    SystemStatsResponse
)

# Import memory layer
from memory_layer.mem0_manager import Mem0Manager
from memory_layer.mem0_context_extractor import Mem0ContextExtractor
from memory_layer.mem0_integration_service import Mem0IntegrationService

# Import dynamic context services
from services.dynamic_context_service import DynamicContextService

load_dotenv()

# Validate configuration on startup
validation_result = validate_environment()
if not validation_result["valid"]:
    logger.error("❌ Configuration validation failed:")
    for error in validation_result["errors"]:
        logger.error(f"   - {error}")
    raise SystemExit("Configuration errors detected. Please check your .env file.")

app = FastAPI(
    title="Integrated Lending Context Chatbot with Dynamic Context", 
    version="2.1.0",
    description="AI-powered lending assistant with dynamic context ingestion capabilities"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.server.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services with dependency injection
vector_service = VectorService()
neo4j_service = Neo4jService()
context_repository = ContextRepository(neo4j_service)
integration_service = IntegrationService(vector_service, context_repository)

# Initialize mem0 layer
memory_manager = Mem0Manager()
context_extractor = Mem0ContextExtractor(
    lending_dir=os.getenv("LENDING_CONTEXT_PATH", "./Lending")
)
enhanced_integration_service = Mem0IntegrationService(
    memory_manager=memory_manager,
    vector_service=vector_service,
    context_repository=context_repository,
    existing_integration_service=integration_service
)

chat_service = ChatService()
context_service = ContextService(integration_service)

# Initialize dynamic context service
from vector.document_processor import DocumentProcessor
document_processor = DocumentProcessor()

dynamic_context_service = DynamicContextService(
    document_processor=document_processor,
    vector_service=vector_service,
    memory_manager=memory_manager
)

# Mount frontend static files
if os.path.exists(config.server.frontend_dist_path):
    app.mount("/assets", StaticFiles(directory=f"{config.server.frontend_dist_path}/assets"), name="assets")
    logger.info(f"📁 Frontend assets mounted from {config.server.frontend_dist_path}")

@app.on_event("startup")
async def startup_event():
    """Initialize all services"""
    print("🚀 Starting Integrated Lending Chatbot...")
    
    # Initialize Vector Store first (safer)
    try:
        await vector_service.initialize()
        print("✅ Vector store initialized")
    except Exception as e:
        print(f"⚠️ Vector store initialization failed: {e}")
        print("📝 Continuing with limited functionality...")
    
    # Initialize Neo4j (optional for basic functionality)
    try:
        await neo4j_service.initialize()
        print("✅ Neo4j connection established")
    except Exception as e:
        print(f"⚠️ Neo4j initialization failed: {e}")
        print("📝 Continuing without graph database...")
    
    print("🎉 Services ready!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services"""
    await neo4j_service.close()
    print("✅ Services closed")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the React chat interface"""
    if os.path.exists("frontend/dist/index.html"):
        with open("frontend/dist/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Integrated Lending Chatbot API</h1><p>Frontend not built. Run <code>cd frontend && npm run build</code></p>")

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Handle chat requests with enhanced mem0 + vector + graph context retrieval
    
    Processing Flow:
    1. mem0 semantic memory search
    2. Vector search for document similarity
    3. Graph enhancement for relationship context
    4. Enhanced context fusion and ranking
    5. LLM response generation with memory storage
    """
    try:
        print(f"💬 Processing chat request: {request.message[:50]}...")
        
        # Step 1: Get enhanced context (mem0 + Vector + Graph)
        context_items = await enhanced_integration_service.get_enhanced_context(
            request.message, 
            max_items=int(os.getenv("MAX_CONTEXT_ITEMS", 8))
        )
        
        print(f"📊 Retrieved {len(context_items)} enhanced context items")
        
        # Step 2: Generate response using LLM with enhanced context
        response = await chat_service.generate_response(
            message=request.message,
            context_items=context_items,
            session_id=request.session_id
        )
        
        # Step 3: Store conversation in enhanced memory system
        await enhanced_integration_service.store_enhanced_context(
            user_message=request.message,
            assistant_response=response,
            session_id=request.session_id,
            context_used=context_items
        )
        
        # Also store in existing graph system for compatibility (if available)
        try:
            await context_service.store_conversation(
                user_message=request.message,
                bot_response=response,
                session_id=request.session_id,
                context_used=context_items
            )
        except Exception as graph_error:
            logger.warning(f"⚠️ Graph storage failed (continuing without it): {graph_error}")
            # Continue without graph storage - not critical for functionality
        
        return ChatResponse(
            response=response,
            context_items=[
                f"{item.get('context_source', 'unknown')}: {item['content'][:100]}..." 
                for item in context_items[:3]
            ],
            session_id=request.session_id,
            processing_info={
                "memory_matches": len([i for i in context_items if i.get('context_source') == 'memory']),
                "vector_matches": len([i for i in context_items if i.get('vector_score', 0) > 0]),
                "graph_matches": len([i for i in context_items if i.get('graph_score', 0) > 0]),
                "conversation_matches": len([i for i in context_items if i.get('context_source') == 'conversation']),
                "total_context_items": len(context_items),
                "enhanced_fusion": True
            }
        )
        
    except Exception as e:
        print(f"❌ Chat error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/initialize-context")
async def initialize_context(request: InitializeRequest):
    """Initialize mem0 memory + vector store + graph database with lending context"""
    try:
        print("🚀 Starting enhanced context initialization with mem0...")
        
        lending_path = request.lending_path or os.getenv("LENDING_CONTEXT_PATH", "./Lending")
        print(f"📁 Using lending path: {lending_path}")
        
        # Step 1: Extract context from Lending directory
        context_data = context_extractor.extract_all_context()
        print(f"📄 Extracted context data with {len(context_data.get('capabilities', {}))} capabilities")
        
        # Step 2: Initialize mem0 memory
        memory_stats = memory_manager.store_lending_context(context_data)
        print(f"🧠 Stored {memory_stats.get('total_stored', 0)} items in mem0 memory")
        
        # Step 3: Initialize existing vector and graph contexts
        existing_result = await context_service.initialize_integrated_context(lending_path)
        
        return {
            "message": "Enhanced context initialized successfully with mem0 layer",
            "stats": {
                "memory_layer": memory_stats,
                "existing_layers": existing_result,
                "total_capabilities": len(context_data.get('capabilities', {})),
                "common_prompts": len(context_data.get('common_prompts', {})),
                "openapi_specs": len(context_data.get('openapi_specs', {}))
            }
        }
        
    except FileNotFoundError as e:
        print(f"❌ File not found error: {e}")
        raise HTTPException(status_code=404, detail=f"Lending directory not found: {str(e)}")
    except Exception as e:
        print(f"❌ Enhanced context initialization error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to initialize enhanced context: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Comprehensive health check for all services"""
    try:
        neo4j_status = await neo4j_service.test_connection()
        vector_status = vector_service.get_collection_info()
        
        return {
            "status": "healthy",
            "services": {
                "neo4j": {
                    "connected": neo4j_status,
                    "status": "healthy" if neo4j_status else "unhealthy",
                    "enabled": config.is_feature_enabled("neo4j")
                },
                "vector_store": {
                    "collection_count": vector_status.get('count', 0),
                    "status": "healthy" if vector_status.get('count', 0) > 0 else "empty",
                    "enabled": True
                },
                "anthropic": {
                    "configured": bool(config.ai.anthropic_api_key),
                    "status": "configured" if config.ai.anthropic_api_key else "not_configured",
                    "model": config.ai.anthropic_model
                },
                "mem0": {
                    "configured": bool(config.ai.mem0_api_key),
                    "status": "configured" if config.ai.mem0_api_key else "not_configured",
                    "enabled": config.is_feature_enabled("mem0")
                }
            },
            "features": {
                feature: config.is_feature_enabled(feature)
                for feature in ["neo4j", "mem0", "github", "url_processing", "file_upload"]
            },
            "configuration": {
                "max_context_items": config.context.max_context_items,
                "max_file_size_mb": config.processing.max_file_size / (1024 * 1024),
                "max_concurrent_tasks": config.processing.max_concurrent_tasks
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/api/config")
async def get_system_configuration():
    """Get system configuration information (non-sensitive)."""
    try:
        return {
            "version": "2.1.0",
            "features_enabled": {
                feature: config.is_feature_enabled(feature)
                for feature in ["neo4j", "mem0", "github", "url_processing", "file_upload"]
            },
            "processing_limits": config.get_processing_limits(),
            "supported_file_types": config.get_supported_file_types(),
            "context_settings": {
                "max_context_items": config.context.max_context_items,
                "vector_weight": config.context.vector_weight,
                "graph_weight": config.context.graph_weight,
                "memory_weight": config.context.memory_weight
            },
            "ai_settings": {
                "model": config.ai.anthropic_model,
                "max_tokens": config.ai.anthropic_max_tokens,
                "temperature": config.ai.anthropic_temperature,
                "embedding_model": config.ai.embedding_model
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_system_stats():
    """Get comprehensive system statistics including mem0 layer and dynamic content"""
    try:
        # Get enhanced analytics from all layers
        enhanced_analytics = await enhanced_integration_service.get_context_analytics()
        
        # Get traditional statistics for compatibility
        graph_stats = await context_repository.get_graph_statistics()
        vector_stats = vector_service.get_collection_info()
        
        # Get dynamic content statistics
        dynamic_stats = await integration_service.get_dynamic_content_overview()
        
        return {
            "enhanced_analytics": enhanced_analytics,
            "graph_database": graph_stats,
            "vector_store": vector_stats,
            "dynamic_content": dynamic_stats,
            "integration": {
                "total_documents": graph_stats.get("documents", 0),
                "vector_embeddings": vector_stats.get("count", 0),
                "memory_items": enhanced_analytics.get("memory_layer", {}).get("total_memories", 0),
                "capabilities": graph_stats.get("capabilities", 0),
                "concepts": graph_stats.get("concepts", 0),
                "context_sources": enhanced_analytics.get("total_context_sources", 0),
                "dynamic_chunks": dynamic_stats.get("integration_summary", {}).get("total_dynamic_chunks", 0),
                "dynamic_documents": dynamic_stats.get("integration_summary", {}).get("total_dynamic_documents", 0)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Test endpoints for development
@app.post("/api/test/vector-search")
async def test_vector_search(request: dict):
    """Test vector search functionality"""
    try:
        results = await vector_service.search(request["query"], n_results=5)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/test/graph-search")
async def test_graph_search(request: dict):
    """Test graph search functionality"""
    try:
        query_words = request["query"].upper().split()
        results = await context_repository.find_matching_concepts(query_words)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/test/integrated-search")
async def test_integrated_search(request: dict):
    """Test integrated search functionality"""
    try:
        results = await integration_service.get_integrated_context(request["query"], max_items=10)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# mem0 Memory Management Endpoints
@app.get("/api/memory/stats")
async def get_memory_stats():
    """Get detailed mem0 memory statistics"""
    try:
        stats = memory_manager.get_memory_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/search")
async def search_memory(request: dict):
    """Search mem0 memory for specific content"""
    try:
        query = request.get("query", "")
        limit = request.get("limit", 5)
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
            
        results = memory_manager.get_relevant_context(query, limit=limit)
        
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/clear")
async def clear_memory(request: dict = None):
    """Clear mem0 memory items, optionally by type"""
    try:
        request = request or {}
        memory_type = request.get("type")
        
        success = memory_manager.clear_memory(memory_type)
        
        if success:
            return {
                "message": f"Successfully cleared {memory_type or 'all'} memories",
                "cleared_type": memory_type
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to clear memory")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/context/summary")
async def get_context_summary():
    """Get a readable overview of available context from Lending directory"""
    try:
        summary = context_extractor.get_context_summary()
        memory_stats = memory_manager.get_memory_stats()
        
        return {
            "summary": summary,
            "memory_stats": memory_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/context/validate")
async def validate_context():
    """Validate the Lending directory structure"""
    try:
        validation_result = context_extractor.validate_lending_structure()
        return validation_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/capability/{capability_name}")
async def get_capability_details(capability_name: str):
    """Get detailed information about a specific capability"""
    try:
        details = context_extractor.get_capability_details(capability_name)
        return details
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/export")
async def export_memory(request: dict):
    """Export mem0 memory data for backup/analysis"""
    try:
        output_path = request.get("output_path", "memory_export.json")
        
        success = memory_manager.export_memory(output_path)
        
        if success:
            return {
                "message": f"Memory exported successfully to {output_path}",
                "output_path": output_path
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to export memory")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced Testing Endpoints
@app.post("/api/test/enhanced-search")
async def test_enhanced_search(request: dict):
    """Test enhanced search functionality with mem0 integration"""
    try:
        query = request.get("query", "eKYC verification process")
        max_items = request.get("max_items", 5)
        
        results = await enhanced_integration_service.get_enhanced_context(query, max_items)
        
        return {
            "query": query,
            "results": results,
            "count": len(results),
            "sources": list(set(r.get("context_source", "unknown") for r in results))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/test/dynamic-search")
async def test_dynamic_search(request: dict):
    """Test dynamic content search functionality"""
    try:
        query = request.get("query", "dynamic content processing")
        source_types = request.get("source_types", None)  # ['upload', 'url', 'github']
        max_items = request.get("max_items", 5)
        
        results = await integration_service.search_dynamic_content_only(query, source_types, max_items)
        
        return {
            "query": query,
            "source_types_filter": source_types,
            "results": results,
            "count": len(results),
            "source_types_found": list(set(r.get("source_type", "unknown") for r in results))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/test/memory-system")
async def test_memory_system(request: dict = None):
    """Test the mem0 memory system functionality"""
    try:
        request = request or {}
        test_query = request.get("query", "eKYC verification process")
        
        # Test memory search
        memory_results = memory_manager.get_relevant_context(test_query, limit=3)
        
        # Test conversation storage
        test_session = "test_session"
        memory_manager.add_conversation(
            user_message=test_query,
            assistant_response="Test response for mem0 memory system",
            session_id=test_session
        )
        
        # Get conversation history
        history = memory_manager.get_conversation_history(test_session, limit=1)
        
        return {
            "test_query": test_query,
            "memory_results": len(memory_results),
            "conversation_stored": len(history) > 0,
            "memory_stats": memory_manager.get_memory_stats(),
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Dynamic Context Ingestion Endpoints

@app.post("/api/dynamic-context/upload", response_model=DynamicContextResponse)
async def upload_files_for_processing(request: FileUploadRequest):
    """
    Process uploaded files and integrate with context system.
    
    Accepts multiple files and processes them through the dynamic context pipeline.
    """
    try:
        # Validate files
        validation_result = await dynamic_context_service.validate_source('upload', {'files': request.files})
        
        if not validation_result['valid']:
            raise HTTPException(
                status_code=400, 
                detail=f"File validation failed: {', '.join(validation_result['errors'])}"
            )
        
        # Start processing
        task_id = await dynamic_context_service.process_dynamic_content('upload', {
            'identifier': f"{len(request.files)} uploaded files",
            'files': request.files
        })
        
        return DynamicContextResponse(
            task_id=task_id,
            message=f"Started processing {len(request.files)} uploaded files",
            source_type="upload",
            estimated_processing_time=len(request.files) * 5
        )
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"❌ File upload processing error: {e}")
        logger.error(f"❌ Full traceback: {error_details}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dynamic-context/url", response_model=DynamicContextResponse)
async def process_url_content(request: URLProcessingRequest):
    """
    Process content from a URL and integrate with context system.
    
    Fetches content from the provided URL and processes it through the pipeline.
    """
    try:
        # Validate URL
        validation_result = await dynamic_context_service.validate_source('url', {'url': request.url})
        
        if not validation_result['valid']:
            raise HTTPException(
                status_code=400,
                detail=f"URL validation failed: {', '.join(validation_result['errors'])}"
            )
        
        # Start processing
        task_id = await dynamic_context_service.process_dynamic_content('url', {
            'identifier': request.url,
            'url': request.url
        })
        
        return DynamicContextResponse(
            task_id=task_id,
            message=f"Started processing content from URL: {request.url}",
            source_type="url",
            estimated_processing_time=10
        )
        
    except Exception as e:
        logger.error(f"❌ URL processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dynamic-context/github", response_model=DynamicContextResponse)
async def process_github_repository(request: GitHubProcessingRequest):
    """
    Process GitHub repository content and integrate with context system.
    
    Fetches documentation and code files from the repository and processes them.
    """
    try:
        # Validate repository
        validation_result = await dynamic_context_service.validate_source('github', {'repo_url': request.repo_url})
        
        if not validation_result['valid']:
            raise HTTPException(
                status_code=400,
                detail=f"Repository validation failed: {', '.join(validation_result['errors'])}"
            )
        
        # Start processing
        task_id = await dynamic_context_service.process_dynamic_content('github', {
            'identifier': request.repo_url,
            'repo_url': request.repo_url
        })
        
        return DynamicContextResponse(
            task_id=task_id,
            message=f"Started processing GitHub repository: {request.repo_url}",
            source_type="github",
            estimated_processing_time=30
        )
        
    except Exception as e:
        logger.error(f"❌ GitHub repository processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dynamic-context/status/{task_id}", response_model=ProcessingStatusResponse)
async def get_processing_status(task_id: str):
    """
    Get the processing status of a dynamic content task.
    
    Returns current status, progress information, and results if completed.
    """
    try:
        result = dynamic_context_service.get_processing_status(task_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Create progress information
        progress = {
            "documents_processed": result.documents_processed,
            "chunks_created": result.chunks_created,
            "vector_embeddings": result.vector_embeddings,
            "memory_items_stored": result.memory_items_stored,
            "processing_time": result.processing_time
        }
        
        # Create status message
        if result.status.value == 'completed':
            message = f"Processing completed successfully. Processed {result.documents_processed} documents into {result.chunks_created} chunks."
        elif result.status.value == 'failed':
            message = f"Processing failed: {result.errors[0].message if result.errors else 'Unknown error'}"
        elif result.status.value == 'pending':
            message = "Processing is queued and will start shortly."
        else:
            message = f"Processing is {result.status.value}..."
        
        # Convert ProcessingResult dataclass to dict for Pydantic model
        result_dict = None
        if result.status.value in ['completed', 'failed']:
            result_dict = {
                "task_id": result.task_id,
                "status": result.status,
                "documents_processed": result.documents_processed,
                "chunks_created": result.chunks_created,
                "vector_embeddings": result.vector_embeddings,
                "memory_items_stored": result.memory_items_stored,
                "errors": [
                    {
                        "error_type": error.error_type,
                        "error_code": error.error_code,
                        "message": error.message,
                        "source_identifier": error.source_identifier,
                        "suggested_action": error.suggested_action,
                        "timestamp": error.timestamp.isoformat() if hasattr(error.timestamp, 'isoformat') else str(error.timestamp)
                    } for error in result.errors
                ],
                "processing_time": result.processing_time,
                "source_type": result.source_type,
                "source_identifier": result.source_identifier
            }

        return ProcessingStatusResponse(
            task_id=task_id,
            status=result.status,
            progress=progress,
            result=result_dict,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Status check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dynamic-context/supported-types", response_model=SupportedTypesResponse)
async def get_supported_types():
    """
    Get information about supported content types and formats.
    
    Returns details about supported file types, URL content types, and GitHub file extensions.
    """
    try:
        # Get supported types from handlers
        file_types = dynamic_context_service.file_upload_handler.get_supported_types()
        
        # Get URL content types
        async with dynamic_context_service.url_content_extractor as extractor:
            url_types = extractor.get_supported_content_types()
        
        # Get GitHub supported extensions
        github_extensions = list(dynamic_context_service.github_processor.get_supported_extensions())
        
        return SupportedTypesResponse(
            file_types=file_types,
            url_types=url_types,
            github_extensions=github_extensions
        )
        
    except Exception as e:
        logger.error(f"❌ Supported types error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dynamic-context/validate")
async def validate_content_source(source_type: str, source_data: dict):
    """
    Validate a content source before processing.
    
    Checks if the provided source is valid and accessible.
    """
    try:
        if source_type not in ['upload', 'url', 'github']:
            raise HTTPException(status_code=400, detail="Invalid source type")
        
        validation_result = await dynamic_context_service.validate_source(source_type, source_data)
        
        return ValidationResult(
            valid=validation_result['valid'],
            errors=validation_result['errors'],
            warnings=validation_result['warnings']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Validation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dynamic-context/batch", response_model=BatchProcessingResponse)
async def process_batch_sources(request: BatchProcessingRequest):
    """
    Process multiple content sources in a batch.
    
    Accepts multiple sources of different types and processes them concurrently.
    """
    try:
        task_ids = []
        batch_id = f"batch_{len(request.sources)}_{int(datetime.now().timestamp())}"
        
        for i, source in enumerate(request.sources):
            source_type = source['type']
            source_data = {k: v for k, v in source.items() if k != 'type'}
            source_data['identifier'] = f"{batch_id}_source_{i}"
            
            # Validate source
            validation_result = await dynamic_context_service.validate_source(source_type, source_data)
            if not validation_result['valid']:
                raise HTTPException(
                    status_code=400,
                    detail=f"Source {i+1} validation failed: {', '.join(validation_result['errors'])}"
                )
            
            # Start processing
            task_id = await dynamic_context_service.process_dynamic_content(source_type, source_data)
            task_ids.append(task_id)
        
        return BatchProcessingResponse(
            batch_id=batch_id,
            task_ids=task_ids,
            message=f"Started batch processing of {len(request.sources)} sources",
            estimated_total_time=len(request.sources) * 15
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Batch processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dynamic-context/stats", response_model=SystemStatsResponse)
async def get_dynamic_context_stats():
    """
    Get system statistics for dynamic context processing.
    
    Returns information about processing tasks, queue status, and system health.
    """
    try:
        all_tasks = dynamic_context_service.get_all_processing_tasks()
        
        # Calculate statistics
        total_tasks = len(all_tasks)
        active_tasks = len([t for t in all_tasks.values() if t.status.value in ['pending', 'extracting', 'vectorizing', 'storing']])
        completed_tasks = len([t for t in all_tasks.values() if t.status.value == 'completed'])
        failed_tasks = len([t for t in all_tasks.values() if t.status.value == 'failed'])
        
        # Calculate average processing time
        completed_task_times = [t.processing_time for t in all_tasks.values() if t.status.value == 'completed' and t.processing_time > 0]
        avg_processing_time = sum(completed_task_times) / len(completed_task_times) if completed_task_times else 0.0
        
        # Determine system health
        if failed_tasks > total_tasks * 0.5:
            health = "unhealthy"
        elif active_tasks > 10:
            health = "busy"
        else:
            health = "healthy"
        
        return SystemStatsResponse(
            total_tasks=total_tasks,
            active_tasks=active_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            processing_queue_size=active_tasks,
            average_processing_time=avg_processing_time,
            supported_sources=["upload", "url", "github"],
            system_health=health
        )
        
    except Exception as e:
        logger.error(f"❌ Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/dynamic-context/cleanup")
async def cleanup_old_tasks():
    """
    Clean up old completed and failed tasks.
    
    Removes tasks older than 24 hours to free up memory.
    """
    try:
        dynamic_context_service.cleanup_completed_tasks(max_age_hours=24)
        
        return {
            "message": "Old tasks cleaned up successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Cleanup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dynamic-context/insights")
async def get_dynamic_context_insights():
    """
    Get insights about dynamically added content and its impact on the system.
    
    Returns analytics about content sources, processing patterns, and system performance.
    """
    try:
        # Get all processing tasks
        all_tasks = dynamic_context_service.get_all_processing_tasks()
        
        # Analyze content sources
        source_analysis = {
            'upload': {'count': 0, 'success_rate': 0, 'avg_chunks': 0},
            'url': {'count': 0, 'success_rate': 0, 'avg_chunks': 0},
            'github': {'count': 0, 'success_rate': 0, 'avg_chunks': 0}
        }
        
        total_chunks_added = 0
        total_memory_items = 0
        total_vector_embeddings = 0
        
        for task in all_tasks.values():
            source_type = task.source_type
            if source_type in source_analysis:
                source_analysis[source_type]['count'] += 1
                
                if task.status.value == 'completed':
                    source_analysis[source_type]['success_rate'] += 1
                    source_analysis[source_type]['avg_chunks'] += task.chunks_created
                    total_chunks_added += task.chunks_created
                    total_memory_items += task.memory_items_stored
                    total_vector_embeddings += task.vector_embeddings
        
        # Calculate success rates and averages
        for source_type, data in source_analysis.items():
            if data['count'] > 0:
                data['success_rate'] = (data['success_rate'] / data['count']) * 100
                if data['success_rate'] > 0:
                    successful_tasks = sum(1 for task in all_tasks.values() 
                                         if task.source_type == source_type and task.status.value == 'completed')
                    if successful_tasks > 0:
                        data['avg_chunks'] = data['avg_chunks'] / successful_tasks
        
        # Get memory and vector store stats
        memory_stats = memory_manager.get_memory_stats()
        vector_stats = vector_service.get_collection_info()
        
        # Calculate system impact
        dynamic_content_ratio = 0
        if vector_stats.get('count', 0) > 0:
            dynamic_content_ratio = (total_vector_embeddings / vector_stats['count']) * 100
        
        return {
            "processing_summary": {
                "total_tasks": len(all_tasks),
                "completed_tasks": len([t for t in all_tasks.values() if t.status.value == 'completed']),
                "failed_tasks": len([t for t in all_tasks.values() if t.status.value == 'failed']),
                "active_tasks": len([t for t in all_tasks.values() if t.status.value in ['pending', 'extracting', 'vectorizing', 'storing']])
            },
            "content_sources": source_analysis,
            "system_impact": {
                "total_chunks_added": total_chunks_added,
                "total_memory_items_added": total_memory_items,
                "total_vector_embeddings_added": total_vector_embeddings,
                "dynamic_content_ratio_percent": round(dynamic_content_ratio, 2)
            },
            "current_system_state": {
                "memory_layer": memory_stats,
                "vector_store": vector_stats,
                "dynamic_processing_active": len([t for t in all_tasks.values() if t.status.value in ['pending', 'extracting', 'vectorizing', 'storing']]) > 0
            },
            "recommendations": _generate_system_recommendations(source_analysis, total_chunks_added, len(all_tasks))
        }
        
    except Exception as e:
        logger.error(f"❌ Insights error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _generate_system_recommendations(source_analysis: Dict, total_chunks: int, total_tasks: int) -> List[str]:
    """Generate recommendations based on system usage patterns."""
    recommendations = []
    
    # Check for failed tasks
    for source_type, data in source_analysis.items():
        if data['count'] > 0 and data['success_rate'] < 80:
            recommendations.append(f"Consider reviewing {source_type} processing - success rate is {data['success_rate']:.1f}%")
    
    # Check for system load
    if total_tasks > 100:
        recommendations.append("Consider running cleanup to remove old completed tasks")
    
    # Check for content diversity
    active_sources = sum(1 for data in source_analysis.values() if data['count'] > 0)
    if active_sources == 1:
        recommendations.append("Consider using multiple content sources (files, URLs, GitHub) for richer context")
    
    # Check for processing volume
    if total_chunks > 1000:
        recommendations.append("Large amount of dynamic content added - monitor system performance")
    elif total_chunks < 10:
        recommendations.append("Add more dynamic content to improve context richness")
    
    if not recommendations:
        recommendations.append("System is operating optimally")
    
    return recommendations


# Catch-all route for React Router (must be last)
@app.get("/{path:path}", response_class=HTMLResponse)
async def serve_react_app(path: str):
    """Serve React app for any non-API routes"""
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    frontend_index = f"{config.server.frontend_dist_path}/index.html"
    if os.path.exists(frontend_index):
        with open(frontend_index, "r") as f:
            return HTMLResponse(content=f.read())
    
    return HTMLResponse(content="""
    <h1>🏦 Integrated Lending Chatbot API</h1>
    <p>Frontend not built. Run the following commands:</p>
    <pre>cd frontend && npm install && npm run build</pre>
    <h2>API Endpoints:</h2>
    <ul>
        <li><a href="/api/health">Health Check</a></li>
        <li><a href="/api/config">System Configuration</a></li>
        <li><a href="/api/stats">System Statistics</a></li>
        <li><a href="/docs">API Documentation</a></li>
    </ul>
    """)

if __name__ == "__main__":
    print("🚀 Starting Integrated Lending Chatbot with Dynamic Context")
    print("=" * 60)
    
    # Print configuration summary
    validation = validate_environment()
    if validation["valid"]:
        print("✅ Configuration validated successfully")
        
        print(f"\n📊 Features enabled:")
        for feature, enabled in validation["features_enabled"].items():
            status = "✅" if enabled else "❌"
            print(f"   {status} {feature}")
        
        print(f"\n🌐 Server starting on:")
        print(f"   • Host: {config.server.host}")
        print(f"   • Port: {config.server.port}")
        print(f"   • Frontend: http://localhost:{config.server.port}")
        print(f"   • API Docs: http://localhost:{config.server.port}/docs")
        
        print(f"\n🔧 Processing limits:")
        limits = config.get_processing_limits()
        print(f"   • Max file size: {limits['max_file_size'] / (1024*1024):.1f}MB")
        print(f"   • Max files per upload: {limits['max_files_per_upload']}")
        print(f"   • Max concurrent tasks: {limits['max_concurrent_tasks']}")
        
        print("\n" + "=" * 60)
        print("🎯 Ready to accept requests!")
        print("   Use Ctrl+C to stop the server")
        print("=" * 60)
        
        # Start the server
        uvicorn.run(
            "main:app",
            host=config.server.host,
            port=config.server.port,
            reload=config.server.debug,
            log_level=config.logging.log_level.lower()
        )
    else:
        print("❌ Configuration validation failed:")
        for error in validation["errors"]:
            print(f"   - {error}")
        print("\nPlease check your .env file and try again.")
        exit(1)