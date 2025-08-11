"""
Integration tests for dynamic context API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import json

# Import the FastAPI app
from main import app


class TestDynamicContextAPI:
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def mock_dynamic_service(self):
        """Mock the dynamic context service."""
        mock = Mock()
        mock.validate_source = AsyncMock()
        mock.process_dynamic_content = AsyncMock()
        mock.get_processing_status = Mock()
        mock.get_all_processing_tasks = Mock()
        mock.cleanup_completed_tasks = Mock()
        mock.file_upload_handler = Mock()
        mock.url_content_extractor = Mock()
        mock.github_processor = Mock()
        return mock
    
    def test_upload_files_endpoint_success(self, client, mock_dynamic_service):
        """Test successful file upload processing."""
        # Mock validation and processing
        mock_dynamic_service.validate_source.return_value = {'valid': True, 'errors': [], 'warnings': []}
        mock_dynamic_service.process_dynamic_content.return_value = 'task_123'
        
        with patch('main.dynamic_context_service', mock_dynamic_service):
            response = client.post(
                "/api/dynamic-context/upload",
                json={
                    "files": [
                        {
                            "filename": "test.txt",
                            "content_type": "text/plain",
                            "content": "VGVzdCBjb250ZW50"  # base64 encoded "Test content"
                        }
                    ]
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task_123"
        assert data["source_type"] == "upload"
        assert "Started processing 1 uploaded files" in data["message"]
    
    def test_upload_files_endpoint_validation_error(self, client, mock_dynamic_service):
        """Test file upload with validation errors."""
        # Mock validation failure
        mock_dynamic_service.validate_source.return_value = {
            'valid': False, 
            'errors': ['File type not supported'], 
            'warnings': []
        }
        
        with patch('main.dynamic_context_service', mock_dynamic_service):
            response = client.post(
                "/api/dynamic-context/upload",
                json={
                    "files": [
                        {
                            "filename": "test.exe",
                            "content_type": "application/octet-stream",
                            "content": "malicious content"
                        }
                    ]
                }
            )
        
        assert response.status_code == 400
        assert "File validation failed" in response.json()["detail"]
    
    def test_process_url_endpoint_success(self, client, mock_dynamic_service):
        """Test successful URL processing."""
        # Mock validation and processing
        mock_dynamic_service.validate_source.return_value = {'valid': True, 'errors': [], 'warnings': []}
        mock_dynamic_service.process_dynamic_content.return_value = 'task_456'
        
        with patch('main.dynamic_context_service', mock_dynamic_service):
            response = client.post(
                "/api/dynamic-context/url",
                json={"url": "https://example.com/article"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task_456"
        assert data["source_type"] == "url"
        assert "https://example.com/article" in data["message"]
    
    def test_process_url_endpoint_invalid_url(self, client):
        """Test URL processing with invalid URL."""
        response = client.post(
            "/api/dynamic-context/url",
            json={"url": "not-a-valid-url"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_process_github_endpoint_success(self, client, mock_dynamic_service):
        """Test successful GitHub repository processing."""
        # Mock validation and processing
        mock_dynamic_service.validate_source.return_value = {'valid': True, 'errors': [], 'warnings': []}
        mock_dynamic_service.process_dynamic_content.return_value = 'task_789'
        
        with patch('main.dynamic_context_service', mock_dynamic_service):
            response = client.post(
                "/api/dynamic-context/github",
                json={"repo_url": "https://github.com/user/repo"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task_789"
        assert data["source_type"] == "github"
        assert "https://github.com/user/repo" in data["message"]
    
    def test_process_github_endpoint_invalid_url(self, client):
        """Test GitHub processing with invalid repository URL."""
        response = client.post(
            "/api/dynamic-context/github",
            json={"repo_url": "https://gitlab.com/user/repo"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_processing_status_success(self, client, mock_dynamic_service):
        """Test getting processing status."""
        from services.dynamic_context_service import ProcessingStatus, ProcessingResult
        
        # Mock processing result
        mock_result = ProcessingResult(
            task_id="task_123",
            status=ProcessingStatus.COMPLETED,
            documents_processed=1,
            chunks_created=3,
            vector_embeddings=3,
            memory_items_stored=1,
            errors=[],
            processing_time=5.2,
            source_type="upload",
            source_identifier="test.txt"
        )
        
        mock_dynamic_service.get_processing_status.return_value = mock_result
        
        with patch('main.dynamic_context_service', mock_dynamic_service):
            response = client.get("/api/dynamic-context/status/task_123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task_123"
        assert data["status"] == "completed"
        assert "Processing completed successfully" in data["message"]
    
    def test_get_processing_status_not_found(self, client, mock_dynamic_service):
        """Test getting status for non-existent task."""
        mock_dynamic_service.get_processing_status.return_value = None
        
        with patch('main.dynamic_context_service', mock_dynamic_service):
            response = client.get("/api/dynamic-context/status/nonexistent")
        
        assert response.status_code == 404
        assert "Task not found" in response.json()["detail"]
    
    def test_get_supported_types_endpoint(self, client, mock_dynamic_service):
        """Test getting supported content types."""
        # Mock handlers
        mock_file_handler = Mock()
        mock_file_handler.get_supported_types.return_value = {
            'text/plain': 'Plain text files',
            'application/pdf': 'PDF documents'
        }
        
        mock_url_extractor = Mock()
        mock_url_extractor.get_supported_content_types.return_value = {
            'text/html': 'HTML pages',
            'text/plain': 'Plain text'
        }
        mock_url_extractor.__aenter__ = AsyncMock(return_value=mock_url_extractor)
        mock_url_extractor.__aexit__ = AsyncMock(return_value=None)
        
        mock_github_processor = Mock()
        mock_github_processor.get_supported_extensions.return_value = {'.md', '.py', '.txt'}
        
        mock_dynamic_service.file_upload_handler = mock_file_handler
        mock_dynamic_service.url_content_extractor = mock_url_extractor
        mock_dynamic_service.github_processor = mock_github_processor
        
        with patch('main.dynamic_context_service', mock_dynamic_service):
            response = client.get("/api/dynamic-context/supported-types")
        
        assert response.status_code == 200
        data = response.json()
        assert "file_types" in data
        assert "url_types" in data
        assert "github_extensions" in data
        assert data["file_types"]["text/plain"] == "Plain text files"
    
    def test_validate_content_source_endpoint(self, client, mock_dynamic_service):
        """Test content source validation endpoint."""
        mock_dynamic_service.validate_source.return_value = {
            'valid': True,
            'errors': [],
            'warnings': ['Minor warning']
        }
        
        with patch('main.dynamic_context_service', mock_dynamic_service):
            response = client.post(
                "/api/dynamic-context/validate",
                params={"source_type": "url"},
                json={"url": "https://example.com"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert len(data["warnings"]) == 1
    
    def test_validate_content_source_invalid_type(self, client):
        """Test validation with invalid source type."""
        response = client.post(
            "/api/dynamic-context/validate",
            params={"source_type": "invalid"},
            json={"data": "test"}
        )
        
        assert response.status_code == 400
        assert "Invalid source type" in response.json()["detail"]
    
    def test_batch_processing_endpoint(self, client, mock_dynamic_service):
        """Test batch processing endpoint."""
        mock_dynamic_service.validate_source.return_value = {'valid': True, 'errors': [], 'warnings': []}
        mock_dynamic_service.process_dynamic_content.side_effect = ['task_1', 'task_2']
        
        with patch('main.dynamic_context_service', mock_dynamic_service):
            response = client.post(
                "/api/dynamic-context/batch",
                json={
                    "sources": [
                        {"type": "url", "url": "https://example1.com"},
                        {"type": "url", "url": "https://example2.com"}
                    ]
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["task_ids"]) == 2
        assert "batch_" in data["batch_id"]
        assert "Started batch processing of 2 sources" in data["message"]
    
    def test_get_system_stats_endpoint(self, client, mock_dynamic_service):
        """Test system statistics endpoint."""
        from services.dynamic_context_service import ProcessingStatus, ProcessingResult
        
        # Mock task data
        mock_tasks = {
            'task_1': ProcessingResult(
                task_id="task_1", status=ProcessingStatus.COMPLETED,
                documents_processed=1, chunks_created=2, vector_embeddings=2,
                memory_items_stored=1, errors=[], processing_time=3.5,
                source_type="upload", source_identifier="test1.txt"
            ),
            'task_2': ProcessingResult(
                task_id="task_2", status=ProcessingStatus.FAILED,
                documents_processed=0, chunks_created=0, vector_embeddings=0,
                memory_items_stored=0, errors=[], processing_time=1.0,
                source_type="url", source_identifier="https://example.com"
            ),
            'task_3': ProcessingResult(
                task_id="task_3", status=ProcessingStatus.EXTRACTING,
                documents_processed=0, chunks_created=0, vector_embeddings=0,
                memory_items_stored=0, errors=[], processing_time=0.0,
                source_type="github", source_identifier="https://github.com/user/repo"
            )
        }
        
        mock_dynamic_service.get_all_processing_tasks.return_value = mock_tasks
        
        with patch('main.dynamic_context_service', mock_dynamic_service):
            response = client.get("/api/dynamic-context/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_tasks"] == 3
        assert data["active_tasks"] == 1  # Only extracting task
        assert data["completed_tasks"] == 1
        assert data["failed_tasks"] == 1
        assert data["average_processing_time"] == 3.5  # Only completed task
        assert data["system_health"] == "healthy"
    
    def test_cleanup_old_tasks_endpoint(self, client, mock_dynamic_service):
        """Test cleanup endpoint."""
        with patch('main.dynamic_context_service', mock_dynamic_service):
            response = client.delete("/api/dynamic-context/cleanup")
        
        assert response.status_code == 200
        data = response.json()
        assert "Old tasks cleaned up successfully" in data["message"]
        assert "timestamp" in data
        
        # Verify cleanup was called
        mock_dynamic_service.cleanup_completed_tasks.assert_called_once_with(max_age_hours=24)
    
    def test_request_validation_errors(self, client):
        """Test various request validation errors."""
        # Test empty files list
        response = client.post(
            "/api/dynamic-context/upload",
            json={"files": []}
        )
        assert response.status_code == 422
        
        # Test missing required fields
        response = client.post(
            "/api/dynamic-context/upload",
            json={
                "files": [
                    {"filename": "test.txt"}  # Missing content_type and content
                ]
            }
        )
        assert response.status_code == 422
        
        # Test too many files
        response = client.post(
            "/api/dynamic-context/upload",
            json={
                "files": [
                    {
                        "filename": f"test{i}.txt",
                        "content_type": "text/plain",
                        "content": "content"
                    }
                    for i in range(15)  # More than allowed
                ]
            }
        )
        assert response.status_code == 422
    
    def test_error_handling(self, client, mock_dynamic_service):
        """Test error handling in endpoints."""
        # Mock service error
        mock_dynamic_service.validate_source.side_effect = Exception("Service error")
        
        with patch('main.dynamic_context_service', mock_dynamic_service):
            response = client.post(
                "/api/dynamic-context/upload",
                json={
                    "files": [
                        {
                            "filename": "test.txt",
                            "content_type": "text/plain",
                            "content": "content"
                        }
                    ]
                }
            )
        
        assert response.status_code == 500
        assert "Service error" in response.json()["detail"]


if __name__ == '__main__':
    pytest.main([__file__])