"""
Integration tests for URL processing to vector storage workflow.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from services.dynamic_context_service import DynamicContextService
from services.url_content_extractor import URLContentExtractor
from vector.document_processor import DocumentProcessor
from vector.vector_service import VectorService
from memory_layer.mem0_manager import Mem0Manager


class TestURLProcessingIntegration:
    
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
                'content': 'URL content chunk 1',
                'source': 'https://example.com',
                'chunk_id': 0,
                'type': 'web_content',
                'capability': 'DYNAMIC',
                'metadata': {'chunk_count': 2}
            },
            {
                'content': 'URL content chunk 2',
                'source': 'https://example.com',
                'chunk_id': 1,
                'type': 'web_content',
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
    def mock_url_extraction(self):
        """Mock successful URL content extraction."""
        return {
            'url': 'https://example.com',
            'content': 'This is extracted web content from the URL. It contains useful information about the topic.',
            'title': 'Example Page Title',
            'content_type': 'text/html',
            'size': 150,
            'status_code': 200,
            'final_url': 'https://example.com',
            'metadata': {
                'extraction_method': 'html_parser',
                'word_count': 15,
                'text_length': 150
            }
        }
    
    @pytest.mark.asyncio
    async def test_complete_url_processing_workflow(self, dynamic_service, mock_url_extraction,
                                                  mock_vector_service, mock_memory_manager):
        """Test complete workflow from URL to vector storage."""
        
        # Mock the URL content extractor
        with patch.object(dynamic_service.url_content_extractor, '__aenter__') as mock_context:
            mock_extractor = Mock()
            mock_extractor.extract_from_url = AsyncMock(return_value=mock_url_extraction)
            mock_context.return_value = mock_extractor
            
            # Prepare content data
            content_data = {
                'identifier': 'test_url',
                'url': 'https://example.com'
            }
            
            # Start processing
            task_id = await dynamic_service.process_dynamic_content('url', content_data)
            
            # Wait for processing to complete
            await asyncio.sleep(0.1)
            
            # Check processing result
            result = dynamic_service.get_processing_status(task_id)
            assert result is not None
            assert result.source_type == 'url'
            
            # Verify vector service was called
            mock_vector_service._add_document_batch.assert_called_once()
            
            # Verify memory manager was called
            mock_memory_manager._store_memory_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_url_validation_integration(self, dynamic_service):
        """Test URL validation integration."""
        
        # Mock URL content extractor validation
        with patch.object(dynamic_service.url_content_extractor, '__aenter__') as mock_context:
            mock_extractor = Mock()
            mock_extractor.validate_url = AsyncMock(return_value=True)
            mock_extractor.detect_content_type = AsyncMock(return_value='text/html')
            mock_extractor.get_supported_content_types = Mock(return_value={'text/html': 'HTML pages'})
            mock_context.return_value = mock_extractor
            
            # Test valid URL
            validation_result = await dynamic_service.validate_source('url', {'url': 'https://example.com'})
            assert validation_result['valid'] is True
        
        # Test invalid URL
        with patch.object(dynamic_service.url_content_extractor, '__aenter__') as mock_context:
            mock_extractor = Mock()
            mock_extractor.validate_url = AsyncMock(return_value=False)
            mock_context.return_value = mock_extractor
            
            validation_result = await dynamic_service.validate_source('url', {'url': 'invalid-url'})
            assert validation_result['valid'] is False
            assert len(validation_result['errors']) > 0
    
    @pytest.mark.asyncio
    async def test_url_content_extraction_error_handling(self, dynamic_service):
        """Test error handling during URL content extraction."""
        
        # Mock extraction failure
        with patch.object(dynamic_service.url_content_extractor, '__aenter__') as mock_context:
            mock_extractor = Mock()
            mock_extractor.extract_from_url = AsyncMock(side_effect=ValueError("Network error"))
            mock_context.return_value = mock_extractor
            
            content_data = {
                'identifier': 'failing_url',
                'url': 'https://failing-example.com'
            }
            
            task_id = await dynamic_service.process_dynamic_content('url', content_data)
            await asyncio.sleep(0.1)
            
            result = dynamic_service.get_processing_status(task_id)
            assert result.status.value == 'failed'
            assert len(result.errors) > 0
            assert 'Network error' in str(result.errors[0].message)
    
    @pytest.mark.asyncio
    async def test_url_content_chunking_integration(self, dynamic_service, mock_document_processor):
        """Test integration with document processor chunking for URL content."""
        
        # Mock long URL content
        long_content = {
            'url': 'https://example.com/long-article',
            'content': 'This is a very long article content that should be chunked into multiple pieces. ' * 100,
            'title': 'Long Article',
            'content_type': 'text/html',
            'size': 5000,
            'status_code': 200,
            'final_url': 'https://example.com/long-article',
            'metadata': {
                'extraction_method': 'html_parser',
                'word_count': 1500,
                'text_length': 5000
            }
        }
        
        with patch.object(dynamic_service.url_content_extractor, '__aenter__') as mock_context:
            mock_extractor = Mock()
            mock_extractor.extract_from_url = AsyncMock(return_value=long_content)
            mock_context.return_value = mock_extractor
            
            content_data = {
                'identifier': 'long_url',
                'url': 'https://example.com/long-article'
            }
            
            task_id = await dynamic_service.process_dynamic_content('url', content_data)
            await asyncio.sleep(0.1)
            
            # Verify chunking was called
            mock_document_processor._chunk_content.assert_called_once()
            
            # Check that chunks were processed
            result = dynamic_service.get_processing_status(task_id)
            assert result.chunks_created > 0
    
    @pytest.mark.asyncio
    async def test_url_metadata_preservation(self, dynamic_service, mock_vector_service, mock_url_extraction):
        """Test that URL metadata is preserved through processing."""
        
        with patch.object(dynamic_service.url_content_extractor, '__aenter__') as mock_context:
            mock_extractor = Mock()
            mock_extractor.extract_from_url = AsyncMock(return_value=mock_url_extraction)
            mock_context.return_value = mock_extractor
            
            content_data = {
                'identifier': 'metadata_test',
                'url': 'https://example.com'
            }
            
            task_id = await dynamic_service.process_dynamic_content('url', content_data)
            await asyncio.sleep(0.1)
            
            # Check that vector service was called with proper metadata
            mock_vector_service._add_document_batch.assert_called_once()
            call_args = mock_vector_service._add_document_batch.call_args[0][0]
            
            # Verify metadata is present
            assert len(call_args) > 0
            chunk = call_args[0]
            assert 'metadata' in chunk
            assert chunk['metadata']['source_type'] == 'url'
            assert chunk['metadata']['url'] == 'https://example.com'
            assert chunk['metadata']['title'] == 'Example Page Title'
    
    @pytest.mark.asyncio
    async def test_different_content_types(self, dynamic_service, mock_vector_service):
        """Test processing different content types from URLs."""
        
        test_cases = [
            {
                'content_type': 'text/html',
                'content': '<html><body>HTML content</body></html>',
                'expected_type': 'web_content'
            },
            {
                'content_type': 'text/plain',
                'content': 'Plain text content',
                'expected_type': 'web_content'
            },
            {
                'content_type': 'application/pdf',
                'content': 'PDF content extracted as text',
                'expected_type': 'web_content'
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            mock_extraction = {
                'url': f'https://example{i}.com',
                'content': test_case['content'],
                'title': f'Test Page {i}',
                'content_type': test_case['content_type'],
                'size': len(test_case['content']),
                'status_code': 200,
                'final_url': f'https://example{i}.com',
                'metadata': {
                    'extraction_method': 'test_parser',
                    'word_count': len(test_case['content'].split())
                }
            }
            
            with patch.object(dynamic_service.url_content_extractor, '__aenter__') as mock_context:
                mock_extractor = Mock()
                mock_extractor.extract_from_url = AsyncMock(return_value=mock_extraction)
                mock_context.return_value = mock_extractor
                
                content_data = {
                    'identifier': f'content_type_test_{i}',
                    'url': f'https://example{i}.com'
                }
                
                task_id = await dynamic_service.process_dynamic_content('url', content_data)
                await asyncio.sleep(0.1)
                
                result = dynamic_service.get_processing_status(task_id)
                assert result.status.value == 'completed'
    
    @pytest.mark.asyncio
    async def test_url_network_timeout_handling(self, dynamic_service):
        """Test handling of network timeouts during URL processing."""
        
        with patch.object(dynamic_service.url_content_extractor, '__aenter__') as mock_context:
            mock_extractor = Mock()
            mock_extractor.extract_from_url = AsyncMock(side_effect=asyncio.TimeoutError("Request timeout"))
            mock_context.return_value = mock_extractor
            
            content_data = {
                'identifier': 'timeout_test',
                'url': 'https://slow-example.com'
            }
            
            task_id = await dynamic_service.process_dynamic_content('url', content_data)
            await asyncio.sleep(0.1)
            
            result = dynamic_service.get_processing_status(task_id)
            assert result.status.value == 'failed'
            assert any('timeout' in error.message.lower() for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_url_content_size_validation(self, dynamic_service):
        """Test validation of URL content size limits."""
        
        # Test with content that's too large
        large_content = {
            'url': 'https://example.com/large',
            'content': 'x' * (dynamic_service.max_url_content_size + 1000),
            'title': 'Large Content',
            'content_type': 'text/html',
            'size': dynamic_service.max_url_content_size + 1000,
            'status_code': 200,
            'final_url': 'https://example.com/large',
            'metadata': {'extraction_method': 'html_parser'}
        }
        
        with patch.object(dynamic_service.url_content_extractor, '__aenter__') as mock_context:
            mock_extractor = Mock()
            mock_extractor.extract_from_url = AsyncMock(return_value=large_content)
            mock_context.return_value = mock_extractor
            
            content_data = {
                'identifier': 'large_content_test',
                'url': 'https://example.com/large'
            }
            
            task_id = await dynamic_service.process_dynamic_content('url', content_data)
            await asyncio.sleep(0.1)
            
            # Should still process but might have warnings
            result = dynamic_service.get_processing_status(task_id)
            # The service should handle large content gracefully
            assert result is not None


if __name__ == '__main__':
    pytest.main([__file__])