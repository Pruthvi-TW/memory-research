"""
Integration tests for file upload to vector storage workflow.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from services.dynamic_context_service import DynamicContextService
from services.file_upload_handler import FileUploadHandler
from vector.document_processor import DocumentProcessor
from vector.vector_service import VectorService
from memory_layer.mem0_manager import Mem0Manager


class TestFileUploadIntegration:
    
    @pytest.fixture
    def mock_vector_service(self):
        mock = Mock(spec=VectorService)
        mock._add_document_batch = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_memory_manager(self):
        mock = Mock(spec=Mem0Manager)
        mock._store_memory_item = Mock()
        return mock
    
    @pytest.fixture
    def mock_document_processor(self):
        mock = Mock(spec=DocumentProcessor)
        mock._chunk_content = Mock(return_value=[
            {
                'content': 'Test chunk 1',
                'source': 'test.txt',
                'chunk_id': 0,
                'type': 'text_document',
                'capability': 'DYNAMIC',
                'metadata': {'chunk_count': 2}
            },
            {
                'content': 'Test chunk 2',
                'source': 'test.txt',
                'chunk_id': 1,
                'type': 'text_document',
                'capability': 'DYNAMIC',
                'metadata': {'chunk_count': 2}
            }
        ])
        return mock
    
    @pytest.fixture
    def dynamic_service(self, mock_document_processor, mock_vector_service, mock_memory_manager):
        return DynamicContextService(
            document_processor=mock_document_processor,
            vector_service=mock_vector_service,
            memory_manager=mock_memory_manager
        )
    
    @pytest.fixture
    def sample_files(self):
        return [
            {
                'filename': 'test1.txt',
                'content_type': 'text/plain',
                'content': b'This is the first test document with some content.'
            },
            {
                'filename': 'test2.md',
                'content_type': 'text/markdown',
                'content': b'# Test Document\n\nThis is a **markdown** document.'
            }
        ]
    
    @pytest.mark.asyncio
    async def test_complete_file_upload_workflow(self, dynamic_service, sample_files, 
                                               mock_vector_service, mock_memory_manager):
        """Test complete workflow from file upload to vector storage."""
        
        # Prepare content data
        content_data = {
            'identifier': 'test_upload',
            'files': sample_files
        }
        
        # Start processing
        task_id = await dynamic_service.process_dynamic_content('upload', content_data)
        
        # Wait for processing to complete
        await asyncio.sleep(0.1)  # Allow async processing to complete
        
        # Check processing result
        result = dynamic_service.get_processing_status(task_id)
        assert result is not None
        assert result.source_type == 'upload'
        
        # Verify vector service was called
        mock_vector_service._add_document_batch.assert_called_once()
        
        # Verify memory manager was called
        mock_memory_manager._store_memory_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_file_validation_integration(self, dynamic_service):
        """Test file validation integration."""
        
        # Test valid files
        valid_files = [
            {
                'filename': 'valid.txt',
                'content_type': 'text/plain',
                'content': b'Valid content'
            }
        ]
        
        validation_result = await dynamic_service.validate_source('upload', {'files': valid_files})
        assert validation_result['valid'] is True
        
        # Test invalid files
        invalid_files = [
            {
                'filename': 'invalid.exe',
                'content_type': 'application/octet-stream',
                'content': b'Invalid content'
            }
        ]
        
        validation_result = await dynamic_service.validate_source('upload', {'files': invalid_files})
        assert validation_result['valid'] is False
        assert len(validation_result['errors']) > 0
    
    @pytest.mark.asyncio
    async def test_multiple_file_processing(self, dynamic_service, mock_vector_service):
        """Test processing multiple files in a single upload."""
        
        files = [
            {
                'filename': f'test{i}.txt',
                'content_type': 'text/plain',
                'content': f'Content for file {i}'.encode()
            }
            for i in range(3)
        ]
        
        content_data = {
            'identifier': 'multi_upload',
            'files': files
        }
        
        task_id = await dynamic_service.process_dynamic_content('upload', content_data)
        await asyncio.sleep(0.1)
        
        result = dynamic_service.get_processing_status(task_id)
        assert result is not None
        
        # Should have processed all files
        mock_vector_service._add_document_batch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_file_processing_error_handling(self, dynamic_service):
        """Test error handling during file processing."""
        
        # Test with empty files list
        content_data = {
            'identifier': 'empty_upload',
            'files': []
        }
        
        task_id = await dynamic_service.process_dynamic_content('upload', content_data)
        await asyncio.sleep(0.1)
        
        result = dynamic_service.get_processing_status(task_id)
        assert result.status.value == 'failed'
        assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_chunking_integration(self, dynamic_service, mock_document_processor):
        """Test integration with document processor chunking."""
        
        files = [
            {
                'filename': 'long_document.txt',
                'content_type': 'text/plain',
                'content': b'This is a very long document that should be chunked into multiple pieces for better processing and retrieval.' * 50
            }
        ]
        
        content_data = {
            'identifier': 'chunking_test',
            'files': files
        }
        
        task_id = await dynamic_service.process_dynamic_content('upload', content_data)
        await asyncio.sleep(0.1)
        
        # Verify chunking was called
        mock_document_processor._chunk_content.assert_called_once()
        
        # Check that chunks were processed
        result = dynamic_service.get_processing_status(task_id)
        assert result.chunks_created > 0
    
    @pytest.mark.asyncio
    async def test_metadata_preservation(self, dynamic_service, mock_vector_service):
        """Test that file metadata is preserved through processing."""
        
        files = [
            {
                'filename': 'metadata_test.txt',
                'content_type': 'text/plain',
                'content': b'Test content for metadata preservation'
            }
        ]
        
        content_data = {
            'identifier': 'metadata_test',
            'files': files
        }
        
        task_id = await dynamic_service.process_dynamic_content('upload', content_data)
        await asyncio.sleep(0.1)
        
        # Check that vector service was called with proper metadata
        mock_vector_service._add_document_batch.assert_called_once()
        call_args = mock_vector_service._add_document_batch.call_args[0][0]
        
        # Verify metadata is present
        assert len(call_args) > 0
        chunk = call_args[0]
        assert 'metadata' in chunk
        assert chunk['metadata']['source_type'] == 'upload'
        assert 'processing_timestamp' in chunk['metadata']
    
    @pytest.mark.asyncio
    async def test_concurrent_file_processing(self, dynamic_service):
        """Test processing multiple file uploads concurrently."""
        
        # Create multiple upload tasks
        tasks = []
        for i in range(3):
            files = [
                {
                    'filename': f'concurrent_{i}.txt',
                    'content_type': 'text/plain',
                    'content': f'Concurrent content {i}'.encode()
                }
            ]
            
            content_data = {
                'identifier': f'concurrent_test_{i}',
                'files': files
            }
            
            task_id = await dynamic_service.process_dynamic_content('upload', content_data)
            tasks.append(task_id)
        
        # Wait for all to complete
        await asyncio.sleep(0.2)
        
        # Check all tasks completed
        for task_id in tasks:
            result = dynamic_service.get_processing_status(task_id)
            assert result is not None
            # Should either be completed or failed, not pending
            assert result.status.value in ['completed', 'failed']


if __name__ == '__main__':
    pytest.main([__file__])