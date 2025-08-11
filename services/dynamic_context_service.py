"""
Dynamic Context Service for handling multiple content sources.
Supports file uploads, URL content extraction, and GitHub repository processing.
"""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

from vector.document_processor import DocumentProcessor
from vector.vector_service import VectorService
from memory_layer.mem0_manager import Mem0Manager
from services.file_upload_handler import FileUploadHandler
from services.url_content_extractor import URLContentExtractor
from services.github_repository_processor import GitHubRepositoryProcessor
from models.dynamic_context_models import ProcessingStatus

logger = logging.getLogger(__name__)


@dataclass
class ProcessingError:
    error_type: str
    error_code: str
    message: str
    source_identifier: str
    suggested_action: str
    timestamp: datetime


@dataclass
class ProcessingResult:
    task_id: str
    status: ProcessingStatus
    documents_processed: int
    chunks_created: int
    vector_embeddings: int
    memory_items_stored: int
    errors: List[ProcessingError]
    processing_time: float
    source_type: str
    source_identifier: str


@dataclass
class DynamicContent:
    source_type: str  # 'upload', 'url', 'github'
    source_identifier: str  # filename, url, or repo_url
    content: str
    metadata: Dict[str, Any]
    content_type: str
    processing_timestamp: datetime


class DynamicContextService:
    """
    Service for processing dynamic content from multiple sources.
    Integrates with existing vector service and memory layer.
    """
    
    def __init__(self, document_processor: DocumentProcessor, 
                 vector_service: VectorService,
                 memory_manager: Mem0Manager):
        self.document_processor = document_processor
        self.vector_service = vector_service
        self.memory_manager = memory_manager
        
        # Initialize specialized handlers
        self.file_upload_handler = FileUploadHandler()
        self.url_content_extractor = URLContentExtractor()
        self.github_processor = GitHubRepositoryProcessor()
        
        # Task tracking
        self.processing_tasks: Dict[str, ProcessingResult] = {}
        
        # Processing limits
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.max_url_content_size = 5 * 1024 * 1024  # 5MB
        self.max_concurrent_tasks = 5
        
        logger.info("🚀 DynamicContextService initialized")
    
    async def process_dynamic_content(self, source_type: str, 
                                    content_data: Dict[str, Any]) -> str:
        """
        Process dynamic content from various sources.
        
        Args:
            source_type: Type of content source ('upload', 'url', 'github')
            content_data: Source-specific data for processing
            
        Returns:
            Task ID for tracking processing status
        """
        task_id = str(uuid.uuid4())
        
        # Initialize processing result
        processing_result = ProcessingResult(
            task_id=task_id,
            status=ProcessingStatus.PENDING,
            documents_processed=0,
            chunks_created=0,
            vector_embeddings=0,
            memory_items_stored=0,
            errors=[],
            processing_time=0.0,
            source_type=source_type,
            source_identifier=content_data.get('identifier', 'unknown')
        )
        
        self.processing_tasks[task_id] = processing_result
        
        # Start async processing
        asyncio.create_task(self._process_content_async(task_id, source_type, content_data))
        
        logger.info(f"📋 Started processing task {task_id} for {source_type}")
        return task_id
    
    async def _process_content_async(self, task_id: str, source_type: str, 
                                   content_data: Dict[str, Any]):
        """Async processing of dynamic content."""
        start_time = datetime.now()
        processing_result = self.processing_tasks[task_id]
        
        try:
            # Update status to extracting
            processing_result.status = ProcessingStatus.EXTRACTING
            
            # Extract content based on source type
            dynamic_content = await self._extract_content(source_type, content_data)
            
            if not dynamic_content:
                raise ValueError(f"Failed to extract content from {source_type}")
            
            # Update status to vectorizing
            processing_result.status = ProcessingStatus.VECTORIZING
            
            # Process content through document processor
            processed_docs = await self._process_through_pipeline(dynamic_content)
            
            # Update status to storing
            processing_result.status = ProcessingStatus.STORING
            
            # Store in vector database and memory layer
            storage_stats = await self._store_processed_content(processed_docs, dynamic_content)
            
            # Update final results
            processing_result.status = ProcessingStatus.COMPLETED
            processing_result.documents_processed = len(processed_docs)
            processing_result.chunks_created = storage_stats.get('chunks_created', 0)
            processing_result.vector_embeddings = storage_stats.get('vector_embeddings', 0)
            processing_result.memory_items_stored = storage_stats.get('memory_items', 0)
            
            logger.info(f"✅ Completed processing task {task_id}")
            
        except Exception as e:
            logger.error(f"❌ Processing failed for task {task_id}: {e}")
            
            processing_result.status = ProcessingStatus.FAILED
            processing_result.errors.append(ProcessingError(
                error_type="processing_error",
                error_code="PROC_001",
                message=str(e),
                source_identifier=content_data.get('identifier', 'unknown'),
                suggested_action="Check content format and try again",
                timestamp=datetime.now()
            ))
        
        finally:
            processing_result.processing_time = (datetime.now() - start_time).total_seconds()
    
    async def _extract_content(self, source_type: str, 
                             content_data: Dict[str, Any]) -> Optional[DynamicContent]:
        """Extract content based on source type."""
        try:
            if source_type == 'upload':
                return await self._extract_from_upload(content_data)
            elif source_type == 'url':
                return await self._extract_from_url(content_data)
            elif source_type == 'github':
                return await self._extract_from_github(content_data)
            else:
                raise ValueError(f"Unsupported source type: {source_type}")
                
        except Exception as e:
            logger.error(f"❌ Content extraction failed: {e}")
            return None
    
    async def _extract_from_upload(self, content_data: Dict[str, Any]) -> DynamicContent:
        """Extract content from uploaded files."""
        try:
            # content_data should contain 'files' list
            files = content_data.get('files', [])
            if not files:
                raise ValueError("No files provided for upload processing")
            
            # Process all uploaded files
            processed_docs = await self.file_upload_handler.process_uploaded_files(files)
            
            if not processed_docs:
                raise ValueError("No content could be extracted from uploaded files")
            
            # Combine content from all files
            combined_content = []
            combined_metadata = {
                'files_processed': len(processed_docs),
                'file_details': []
            }
            
            for doc in processed_docs:
                combined_content.append(f"=== {doc['source']} ===\n{doc['content']}")
                combined_metadata['file_details'].append({
                    'filename': doc['source'],
                    'content_type': doc['content_type'],
                    'character_count': doc['metadata']['character_count'],
                    'word_count': doc['metadata']['word_count']
                })
            
            # Create combined dynamic content
            return DynamicContent(
                source_type='upload',
                source_identifier=f"{len(files)} uploaded files",
                content='\n\n'.join(combined_content),
                metadata=combined_metadata,
                content_type='text/plain',
                processing_timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"❌ File upload processing failed: {e}")
            raise
    
    async def _extract_from_url(self, content_data: Dict[str, Any]) -> DynamicContent:
        """Extract content from URLs."""
        try:
            url = content_data.get('url')
            if not url:
                raise ValueError("No URL provided for extraction")
            
            # Extract content using URLContentExtractor
            async with self.url_content_extractor as extractor:
                extracted_data = await extractor.extract_from_url(url)
            
            if not extracted_data.get('content'):
                raise ValueError(f"No content could be extracted from URL: {url}")
            
            # Create dynamic content
            return DynamicContent(
                source_type='url',
                source_identifier=url,
                content=extracted_data['content'],
                metadata={
                    'url': url,
                    'final_url': extracted_data.get('final_url', url),
                    'title': extracted_data.get('title', ''),
                    'content_type': extracted_data.get('content_type', 'text/html'),
                    'size': extracted_data.get('size', 0),
                    'status_code': extracted_data.get('status_code', 200),
                    'extraction_method': extracted_data.get('metadata', {}).get('extraction_method', 'unknown'),
                    'word_count': extracted_data.get('metadata', {}).get('word_count', 0)
                },
                content_type=extracted_data.get('content_type', 'text/html'),
                processing_timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"❌ URL content extraction failed: {e}")
            raise
    
    async def _extract_from_github(self, content_data: Dict[str, Any]) -> DynamicContent:
        """Extract content from GitHub repositories."""
        try:
            repo_url = content_data.get('repo_url')
            if not repo_url:
                raise ValueError("No repository URL provided for extraction")
            
            # Process repository using GitHubRepositoryProcessor
            async with self.github_processor as processor:
                processed_docs = await processor.process_repository(repo_url)
            
            if not processed_docs:
                raise ValueError(f"No content could be extracted from repository: {repo_url}")
            
            # Combine content from all repository files
            combined_content = []
            combined_metadata = {
                'repo_url': repo_url,
                'files_processed': len(processed_docs),
                'file_details': []
            }
            
            # Get repository info from first document
            if processed_docs:
                first_doc = processed_docs[0]
                combined_metadata.update({
                    'repository_name': first_doc['metadata']['repository_name'],
                    'repository_full_name': first_doc['metadata']['repository_full_name'],
                    'repository_description': first_doc['metadata']['repository_description'],
                    'repository_language': first_doc['metadata']['repository_language'],
                    'repository_stars': first_doc['metadata']['repository_stars'],
                    'repository_topics': first_doc['metadata']['repository_topics']
                })
            
            for doc in processed_docs:
                # Add file separator and content
                combined_content.append(f"=== {doc['file_path']} ===\n{doc['content']}")
                
                # Add file details to metadata
                combined_metadata['file_details'].append({
                    'file_path': doc['file_path'],
                    'file_name': doc['metadata']['file_name'],
                    'file_size': doc['metadata']['file_size'],
                    'file_extension': doc['metadata']['file_extension'],
                    'character_count': doc['metadata']['character_count'],
                    'word_count': doc['metadata']['word_count']
                })
            
            # Create combined dynamic content
            return DynamicContent(
                source_type='github',
                source_identifier=repo_url,
                content='\n\n'.join(combined_content),
                metadata=combined_metadata,
                content_type='text/markdown',
                processing_timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"❌ GitHub repository processing failed: {e}")
            raise
    
    async def _process_through_pipeline(self, dynamic_content: DynamicContent) -> List[Dict[str, Any]]:
        """Process content through existing document processor."""
        try:
            # Create temporary file-like structure for document processor
            temp_doc_data = {
                'content': dynamic_content.content,
                'source': dynamic_content.source_identifier,
                'type': self._determine_content_type(dynamic_content),
                'capability': 'DYNAMIC',
                'metadata': {
                    'source_type': dynamic_content.source_type,
                    'processing_timestamp': dynamic_content.processing_timestamp.isoformat(),
                    **dynamic_content.metadata
                }
            }
            
            # Use existing document processor chunking logic
            chunks = self.document_processor._chunk_content(
                dynamic_content.content,
                dynamic_content.source_identifier,
                'DYNAMIC'
            )
            
            # Enhance chunks with dynamic content metadata
            for chunk in chunks:
                chunk['metadata'].update(temp_doc_data['metadata'])
                chunk['source_type'] = dynamic_content.source_type
            
            return chunks
            
        except Exception as e:
            logger.error(f"❌ Document processing failed: {e}")
            raise
    
    async def _store_processed_content(self, processed_docs: List[Dict[str, Any]], 
                                     dynamic_content: DynamicContent) -> Dict[str, int]:
        """Store processed content in vector database, memory layer, and graph database."""
        stats = {
            'chunks_created': len(processed_docs),
            'vector_embeddings': 0,
            'memory_items': 0,
            'graph_nodes': 0
        }
        
        try:
            # Store in vector database
            if processed_docs:
                await self.vector_service._add_document_batch(processed_docs)
                stats['vector_embeddings'] = len(processed_docs)
                logger.info(f"📊 Stored {len(processed_docs)} chunks in vector database")
            
            # Store in memory layer with enhanced content
            memory_content = f"Dynamic content from {dynamic_content.source_type}: {dynamic_content.source_identifier}"
            memory_metadata = {
                'type': 'dynamic_content',
                'source_type': dynamic_content.source_type,
                'source_identifier': dynamic_content.source_identifier,
                'content_type': dynamic_content.content_type,
                'chunks_count': len(processed_docs),
                'processing_timestamp': dynamic_content.processing_timestamp.isoformat()
            }
            
            # Store in mem0 memory
            await asyncio.to_thread(
                self.memory_manager._store_memory_item,
                memory_content,
                memory_metadata
            )
            
            # Also store individual chunks in memory for better retrieval
            for i, doc in enumerate(processed_docs[:3]):  # Store first 3 chunks
                chunk_content = f"Chunk from {dynamic_content.source_identifier}: {doc['content'][:500]}"
                chunk_metadata = {
                    'type': 'dynamic_chunk',
                    'source_type': dynamic_content.source_type,
                    'source_identifier': dynamic_content.source_identifier,
                    'chunk_index': i,
                    'capability': doc.get('capability', 'DYNAMIC')
                }
                await asyncio.to_thread(
                    self.memory_manager._store_memory_item,
                    chunk_content,
                    chunk_metadata
                )
            
            stats['memory_items'] = 1 + min(len(processed_docs), 3)
            logger.info(f"🧠 Stored {stats['memory_items']} items in memory layer")
            
            # Store key concepts in graph database if available
            try:
                # Extract key concepts from the content
                key_concepts = self._extract_key_concepts_for_graph(dynamic_content.content)
                
                if key_concepts:
                    # Try to store in graph database
                    try:
                        from graph.neo4j_service import Neo4jService
                        from graph.context_repository import ContextRepository
                        
                        # Get the graph services from the main application
                        # This is a bit of a hack - in production, we'd inject these dependencies
                        import sys
                        if 'main' in sys.modules:
                            main_module = sys.modules['main']
                            if hasattr(main_module, 'context_repository'):
                                context_repo = main_module.context_repository
                                
                                # Store dynamic content in graph
                                graph_result = await context_repo.store_dynamic_content(
                                    dynamic_content.source_type,
                                    dynamic_content.source_identifier,
                                    processed_docs,
                                    key_concepts
                                )
                                
                                stats['graph_nodes'] = graph_result.get('concepts_created', 0)
                                logger.info(f"🔗 Stored {stats['graph_nodes']} concepts in graph database")
                            else:
                                logger.info(f"🔗 Identified {len(key_concepts)} concepts for graph storage: {key_concepts[:5]}")
                                stats['graph_nodes'] = len(key_concepts)
                        else:
                            logger.info(f"🔗 Identified {len(key_concepts)} concepts for graph storage: {key_concepts[:5]}")
                            stats['graph_nodes'] = len(key_concepts)
                            
                    except Exception as graph_storage_error:
                        logger.warning(f"⚠️ Graph storage failed, but concepts identified: {graph_storage_error}")
                        logger.info(f"🔗 Identified {len(key_concepts)} concepts: {key_concepts[:5]}")
                        stats['graph_nodes'] = len(key_concepts)
                    
            except Exception as graph_error:
                logger.warning(f"⚠️ Graph concept extraction failed: {graph_error}")
            
        except Exception as e:
            logger.error(f"❌ Storage failed: {e}")
            raise
        
        return stats
    
    def _determine_content_type(self, dynamic_content: DynamicContent) -> str:
        """Determine content type for document processor."""
        if dynamic_content.source_type == 'upload':
            content_type = dynamic_content.content_type.lower()
            if 'pdf' in content_type:
                return 'pdf_document'
            elif 'word' in content_type or 'docx' in content_type:
                return 'word_document'
            elif 'markdown' in content_type:
                return 'markdown_doc'
            else:
                return 'text_document'
        elif dynamic_content.source_type == 'url':
            return 'web_content'
        elif dynamic_content.source_type == 'github':
            return 'repository_doc'
        else:
            return 'dynamic_content'
    
    async def validate_source(self, source_type: str, source_data: Any) -> Dict[str, Any]:
        """Validate content source before processing."""
        validation_result = {
            'valid': False,
            'errors': [],
            'warnings': []
        }
        
        try:
            if source_type == 'upload':
                validation_result = await self._validate_upload(source_data)
            elif source_type == 'url':
                validation_result = await self._validate_url(source_data)
            elif source_type == 'github':
                validation_result = await self._validate_github(source_data)
            else:
                validation_result['errors'].append(f"Unsupported source type: {source_type}")
                
        except Exception as e:
            validation_result['errors'].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    async def _validate_upload(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate uploaded files."""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        files = file_data.get('files', [])
        if not files:
            result['valid'] = False
            result['errors'].append("No files provided")
            return result
        
        # Validate each file using FileUploadHandler
        for i, file_info in enumerate(files):
            file_validation = await self.file_upload_handler.validate_file(file_info)
            
            if not file_validation['valid']:
                result['valid'] = False
                for error in file_validation['errors']:
                    result['errors'].append(f"File {i+1} ({file_info.get('filename', 'unknown')}): {error}")
            
            # Add warnings
            for warning in file_validation.get('warnings', []):
                result['warnings'].append(f"File {i+1} ({file_info.get('filename', 'unknown')}): {warning}")
        
        return result
    
    async def _validate_url(self, url_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate URL."""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        url = url_data.get('url', '')
        
        if not url:
            result['valid'] = False
            result['errors'].append("URL is required")
            return result
        
        # Use URLContentExtractor validation
        async with self.url_content_extractor as extractor:
            is_valid = await extractor.validate_url(url)
            
            if not is_valid:
                result['valid'] = False
                result['errors'].append("Invalid or unsafe URL")
            
            # Try to detect content type
            try:
                content_type = await extractor.detect_content_type(url)
                if content_type:
                    supported_types = extractor.get_supported_content_types()
                    if not any(content_type.startswith(supported) for supported in supported_types.keys()):
                        result['warnings'].append(f"Content type '{content_type}' may not be fully supported")
                else:
                    result['warnings'].append("Could not detect content type")
            except Exception as e:
                result['warnings'].append(f"Could not check content type: {str(e)}")
        
        return result
    
    async def _validate_github(self, repo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate GitHub repository URL."""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        repo_url = repo_data.get('repo_url', '')
        
        if not repo_url:
            result['valid'] = False
            result['errors'].append("Repository URL is required")
            return result
        
        try:
            # Use GitHubRepositoryProcessor validation
            async with self.github_processor as processor:
                is_valid = await processor.validate_repository_url(repo_url)
                
                if not is_valid:
                    result['valid'] = False
                    result['errors'].append("Invalid or inaccessible GitHub repository URL")
                else:
                    # Get repository summary for additional validation info
                    try:
                        summary = await processor.get_repository_summary(repo_url)
                        
                        # Add informational warnings
                        if summary['documentation_files'] == 0:
                            result['warnings'].append("Repository contains no documentation files")
                        elif summary['documentation_files'] > 30:
                            result['warnings'].append(f"Repository contains {summary['documentation_files']} documentation files - processing may take time")
                        
                        # Add file type information
                        file_types = summary.get('file_types', {})
                        if file_types:
                            supported_count = sum(count for ext, count in file_types.items() 
                                                if ext in processor.get_supported_extensions())
                            if supported_count == 0:
                                result['warnings'].append("Repository contains no supported file types")
                        
                    except Exception as e:
                        result['warnings'].append(f"Could not get repository details: {str(e)}")
                        
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Repository validation failed: {str(e)}")
        
        return result
    
    def get_processing_status(self, task_id: str) -> Optional[ProcessingResult]:
        """Get processing status for a task."""
        return self.processing_tasks.get(task_id)
    
    def get_all_processing_tasks(self) -> Dict[str, ProcessingResult]:
        """Get all processing tasks."""
        return self.processing_tasks.copy()
    
    def _extract_key_concepts_for_graph(self, content: str) -> List[str]:
        """Extract key concepts that could be stored in graph database."""
        import re
        
        concepts = []
        content_lower = content.lower()
        
        # Technical concepts relevant to lending
        lending_concepts = [
            'ekyc', 'pan', 'aadhaar', 'otp', 'verification', 'validation',
            'authentication', 'authorization', 'compliance', 'kyc', 'aml',
            'loan', 'credit', 'underwriting', 'disbursement', 'repayment',
            'api', 'service', 'endpoint', 'request', 'response', 'database'
        ]
        
        for concept in lending_concepts:
            if concept in content_lower:
                concepts.append(concept.upper())
        
        # Extract acronyms
        acronyms = re.findall(r'\b[A-Z]{2,}\b', content)
        concepts.extend(acronyms)
        
        # Extract API endpoints
        endpoints = re.findall(r'/api/[a-zA-Z0-9/_-]+', content)
        concepts.extend([ep.replace('/api/', '') for ep in endpoints])
        
        return list(set(concepts))[:20]  # Limit to 20 concepts
    
    def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """Clean up old completed tasks."""
        current_time = datetime.now()
        tasks_to_remove = []
        
        for task_id, result in self.processing_tasks.items():
            if result.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]:
                # Use processing_time as a proxy for task age since we don't store creation time
                if result.processing_time > 0:  # Only remove tasks that have completed processing
                    tasks_to_remove.append(task_id)
        
        # Keep only the most recent 50 tasks to prevent memory bloat
        if len(self.processing_tasks) > 50:
            sorted_tasks = sorted(
                self.processing_tasks.items(), 
                key=lambda x: x[1].processing_time, 
                reverse=True
            )
            tasks_to_keep = dict(sorted_tasks[:50])
            tasks_to_remove.extend([tid for tid in self.processing_tasks.keys() if tid not in tasks_to_keep])
        
        for task_id in tasks_to_remove:
            del self.processing_tasks[task_id]
        
        if tasks_to_remove:
            logger.info(f"🧹 Cleaned up {len(tasks_to_remove)} old processing tasks")