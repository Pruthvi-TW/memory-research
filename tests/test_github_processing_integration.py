"""
Integration tests for GitHub repository processing to vector storage workflow.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from services.dynamic_context_service import DynamicContextService
from services.github_repository_processor import GitHubRepositoryProcessor
from vector.document_processor import DocumentProcessor
from vector.vector_service import VectorService
from memory_layer.mem0_manager import Mem0Manager


class TestGitHubProcessingIntegration:
    
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
                'content': 'GitHub repository chunk 1',
                'source': 'testuser/test-repo',
                'chunk_id': 0,
                'type': 'repository_doc',
                'capability': 'DYNAMIC',
                'metadata': {'chunk_count': 2}
            },
            {
                'content': 'GitHub repository chunk 2',
                'source': 'testuser/test-repo',
                'chunk_id': 1,
                'type': 'repository_doc',
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
    def mock_github_docs(self):
        """Mock processed GitHub repository documents."""
        return [
            {
                'content': '# Test Repository\n\nThis is a test repository for demonstration purposes.',
                'source': 'testuser/test-repo/README.md',
                'source_type': 'github',
                'file_path': 'README.md',
                'repository': 'testuser/test-repo',
                'metadata': {
                    'repository_name': 'test-repo',
                    'repository_full_name': 'testuser/test-repo',
                    'repository_description': 'A test repository',
                    'repository_language': 'Python',
                    'repository_stars': 100,
                    'file_path': 'README.md',
                    'file_name': 'README.md',
                    'file_size': 500,
                    'file_extension': '.md',
                    'character_count': 75,
                    'word_count': 12,
                    'repository_topics': ['python', 'testing']
                }
            },
            {
                'content': '# API Documentation\n\nThis document describes the API endpoints.',
                'source': 'testuser/test-repo/docs/api.md',
                'source_type': 'github',
                'file_path': 'docs/api.md',
                'repository': 'testuser/test-repo',
                'metadata': {
                    'repository_name': 'test-repo',
                    'repository_full_name': 'testuser/test-repo',
                    'repository_description': 'A test repository',
                    'repository_language': 'Python',
                    'repository_stars': 100,
                    'file_path': 'docs/api.md',
                    'file_name': 'api.md',
                    'file_size': 300,
                    'file_extension': '.md',
                    'character_count': 60,
                    'word_count': 10,
                    'repository_topics': ['python', 'testing']
                }
            }
        ]
    
    @pytest.fixture
    def mock_repo_summary(self):
        """Mock repository summary."""
        return {
            'repository': {
                'name': 'test-repo',
                'full_name': 'testuser/test-repo',
                'description': 'A test repository',
                'language': 'Python',
                'stars': 100
            },
            'total_files': 10,
            'documentation_files': 5,
            'file_types': {'.md': 3, '.py': 2},
            'estimated_processing_time': 10
        }
    
    @pytest.mark.asyncio
    async def test_complete_github_processing_workflow(self, dynamic_service, mock_github_docs,
                                                     mock_vector_service, mock_memory_manager):
        """Test complete workflow from GitHub repository to vector storage."""
        
        # Mock the GitHub processor
        with patch.object(dynamic_service.github_processor, '__aenter__') as mock_context:
            mock_processor = Mock()
            mock_processor.process_repository = AsyncMock(return_value=mock_github_docs)
            mock_context.return_value = mock_processor
            
            # Prepare content data
            content_data = {
                'identifier': 'test_github_repo',
                'repo_url': 'https://github.com/testuser/test-repo'
            }
            
            # Start processing
            task_id = await dynamic_service.process_dynamic_content('github', content_data)
            
            # Wait for processing to complete
            await asyncio.sleep(0.1)
            
            # Check processing result
            result = dynamic_service.get_processing_status(task_id)
            assert result is not None
            assert result.source_type == 'github'
            
            # Verify vector service was called
            mock_vector_service._add_document_batch.assert_called_once()
            
            # Verify memory manager was called
            mock_memory_manager._store_memory_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_github_validation_integration(self, dynamic_service, mock_repo_summary):
        """Test GitHub repository validation integration."""
        
        # Mock GitHub processor validation
        with patch.object(dynamic_service.github_processor, '__aenter__') as mock_context:
            mock_processor = Mock()
            mock_processor.validate_repository_url = AsyncMock(return_value=True)
            mock_processor.get_repository_summary = AsyncMock(return_value=mock_repo_summary)
            mock_processor.get_supported_extensions = Mock(return_value={'.md', '.py', '.txt'})
            mock_context.return_value = mock_processor
            
            # Test valid repository
            validation_result = await dynamic_service.validate_source('github', {
                'repo_url': 'https://github.com/testuser/test-repo'
            })
            assert validation_result['valid'] is True
        
        # Test invalid repository
        with patch.object(dynamic_service.github_processor, '__aenter__') as mock_context:
            mock_processor = Mock()
            mock_processor.validate_repository_url = AsyncMock(return_value=False)
            mock_context.return_value = mock_processor
            
            validation_result = await dynamic_service.validate_source('github', {
                'repo_url': 'https://github.com/testuser/nonexistent'
            })
            assert validation_result['valid'] is False
            assert len(validation_result['errors']) > 0
    
    @pytest.mark.asyncio
    async def test_github_processing_error_handling(self, dynamic_service):
        """Test error handling during GitHub repository processing."""
        
        # Mock processing failure
        with patch.object(dynamic_service.github_processor, '__aenter__') as mock_context:
            mock_processor = Mock()
            mock_processor.process_repository = AsyncMock(side_effect=ValueError("Repository not accessible"))
            mock_context.return_value = mock_processor
            
            content_data = {
                'identifier': 'failing_github_repo',
                'repo_url': 'https://github.com/testuser/private-repo'
            }
            
            task_id = await dynamic_service.process_dynamic_content('github', content_data)
            await asyncio.sleep(0.1)
            
            result = dynamic_service.get_processing_status(task_id)
            assert result.status.value == 'failed'
            assert len(result.errors) > 0
            assert 'Repository not accessible' in str(result.errors[0].message)
    
    @pytest.mark.asyncio
    async def test_github_multiple_files_processing(self, dynamic_service, mock_vector_service, mock_github_docs):
        """Test processing multiple files from GitHub repository."""
        
        with patch.object(dynamic_service.github_processor, '__aenter__') as mock_context:
            mock_processor = Mock()
            mock_processor.process_repository = AsyncMock(return_value=mock_github_docs)
            mock_context.return_value = mock_processor
            
            content_data = {
                'identifier': 'multi_file_repo',
                'repo_url': 'https://github.com/testuser/test-repo'
            }
            
            task_id = await dynamic_service.process_dynamic_content('github', content_data)
            await asyncio.sleep(0.1)
            
            result = dynamic_service.get_processing_status(task_id)
            assert result is not None
            
            # Should have processed multiple files
            mock_vector_service._add_document_batch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_github_chunking_integration(self, dynamic_service, mock_document_processor):
        """Test integration with document processor chunking for GitHub content."""
        
        # Mock large repository content
        large_github_docs = [
            {
                'content': 'This is a very large documentation file that should be chunked. ' * 200,
                'source': 'testuser/test-repo/LARGE_README.md',
                'source_type': 'github',
                'file_path': 'LARGE_README.md',
                'repository': 'testuser/test-repo',
                'metadata': {
                    'repository_name': 'test-repo',
                    'repository_full_name': 'testuser/test-repo',
                    'repository_description': 'A test repository',
                    'repository_language': 'Python',
                    'repository_stars': 100,
                    'file_path': 'LARGE_README.md',
                    'file_name': 'LARGE_README.md',
                    'file_size': 10000,
                    'file_extension': '.md',
                    'character_count': 10000,
                    'word_count': 2000,
                    'repository_topics': ['python']
                }
            }
        ]
        
        with patch.object(dynamic_service.github_processor, '__aenter__') as mock_context:
            mock_processor = Mock()
            mock_processor.process_repository = AsyncMock(return_value=large_github_docs)
            mock_context.return_value = mock_processor
            
            content_data = {
                'identifier': 'large_repo',
                'repo_url': 'https://github.com/testuser/large-repo'
            }
            
            task_id = await dynamic_service.process_dynamic_content('github', content_data)
            await asyncio.sleep(0.1)
            
            # Verify chunking was called
            mock_document_processor._chunk_content.assert_called_once()
            
            # Check that chunks were processed
            result = dynamic_service.get_processing_status(task_id)
            assert result.chunks_created > 0
    
    @pytest.mark.asyncio
    async def test_github_metadata_preservation(self, dynamic_service, mock_vector_service, mock_github_docs):
        """Test that GitHub repository metadata is preserved through processing."""
        
        with patch.object(dynamic_service.github_processor, '__aenter__') as mock_context:
            mock_processor = Mock()
            mock_processor.process_repository = AsyncMock(return_value=mock_github_docs)
            mock_context.return_value = mock_processor
            
            content_data = {
                'identifier': 'metadata_test',
                'repo_url': 'https://github.com/testuser/test-repo'
            }
            
            task_id = await dynamic_service.process_dynamic_content('github', content_data)
            await asyncio.sleep(0.1)
            
            # Check that vector service was called with proper metadata
            mock_vector_service._add_document_batch.assert_called_once()
            call_args = mock_vector_service._add_document_batch.call_args[0][0]
            
            # Verify metadata is present
            assert len(call_args) > 0
            chunk = call_args[0]
            assert 'metadata' in chunk
            assert chunk['metadata']['source_type'] == 'github'
            assert chunk['metadata']['repo_url'] == 'https://github.com/testuser/test-repo'
            assert chunk['metadata']['repository_name'] == 'test-repo'
            assert chunk['metadata']['repository_language'] == 'Python'
    
    @pytest.mark.asyncio
    async def test_github_validation_warnings(self, dynamic_service):
        """Test GitHub validation warnings for different repository conditions."""
        
        # Test repository with no documentation files
        empty_summary = {
            'repository': {'name': 'empty-repo'},
            'total_files': 5,
            'documentation_files': 0,
            'file_types': {'.py': 5},
            'estimated_processing_time': 0
        }
        
        with patch.object(dynamic_service.github_processor, '__aenter__') as mock_context:
            mock_processor = Mock()
            mock_processor.validate_repository_url = AsyncMock(return_value=True)
            mock_processor.get_repository_summary = AsyncMock(return_value=empty_summary)
            mock_processor.get_supported_extensions = Mock(return_value={'.md', '.py', '.txt'})
            mock_context.return_value = mock_processor
            
            validation_result = await dynamic_service.validate_source('github', {
                'repo_url': 'https://github.com/testuser/empty-repo'
            })
            
            assert validation_result['valid'] is True
            assert any('no documentation files' in warning for warning in validation_result['warnings'])
        
        # Test repository with many documentation files
        large_summary = {
            'repository': {'name': 'large-repo'},
            'total_files': 100,
            'documentation_files': 50,
            'file_types': {'.md': 50},
            'estimated_processing_time': 100
        }
        
        with patch.object(dynamic_service.github_processor, '__aenter__') as mock_context:
            mock_processor = Mock()
            mock_processor.validate_repository_url = AsyncMock(return_value=True)
            mock_processor.get_repository_summary = AsyncMock(return_value=large_summary)
            mock_processor.get_supported_extensions = Mock(return_value={'.md', '.py', '.txt'})
            mock_context.return_value = mock_processor
            
            validation_result = await dynamic_service.validate_source('github', {
                'repo_url': 'https://github.com/testuser/large-repo'
            })
            
            assert validation_result['valid'] is True
            assert any('processing may take time' in warning for warning in validation_result['warnings'])
    
    @pytest.mark.asyncio
    async def test_github_empty_repository_handling(self, dynamic_service):
        """Test handling of repositories with no processable content."""
        
        with patch.object(dynamic_service.github_processor, '__aenter__') as mock_context:
            mock_processor = Mock()
            mock_processor.process_repository = AsyncMock(return_value=[])  # Empty repository
            mock_context.return_value = mock_processor
            
            content_data = {
                'identifier': 'empty_repo',
                'repo_url': 'https://github.com/testuser/empty-repo'
            }
            
            task_id = await dynamic_service.process_dynamic_content('github', content_data)
            await asyncio.sleep(0.1)
            
            result = dynamic_service.get_processing_status(task_id)
            assert result.status.value == 'failed'
            assert any('No content could be extracted' in error.message for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_github_rate_limit_handling(self, dynamic_service):
        """Test handling of GitHub API rate limits."""
        
        with patch.object(dynamic_service.github_processor, '__aenter__') as mock_context:
            mock_processor = Mock()
            mock_processor.process_repository = AsyncMock(side_effect=ValueError("API rate limit exceeded"))
            mock_context.return_value = mock_processor
            
            content_data = {
                'identifier': 'rate_limited_repo',
                'repo_url': 'https://github.com/testuser/popular-repo'
            }
            
            task_id = await dynamic_service.process_dynamic_content('github', content_data)
            await asyncio.sleep(0.1)
            
            result = dynamic_service.get_processing_status(task_id)
            assert result.status.value == 'failed'
            assert any('rate limit' in error.message.lower() for error in result.errors)


if __name__ == '__main__':
    pytest.main([__file__])