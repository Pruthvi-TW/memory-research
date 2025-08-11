"""
Unit tests for FileUploadHandler service.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from services.file_upload_handler import FileUploadHandler


class TestFileUploadHandler:
    
    @pytest.fixture
    def handler(self):
        return FileUploadHandler()
    
    @pytest.fixture
    def sample_text_file(self):
        return {
            'filename': 'test.txt',
            'content_type': 'text/plain',
            'content': b'This is a test document with some content for processing.'
        }
    
    @pytest.fixture
    def sample_markdown_file(self):
        return {
            'filename': 'test.md',
            'content_type': 'text/markdown',
            'content': b'# Test Document\n\nThis is a **markdown** document with [links](http://example.com).\n\n```python\nprint("code")\n```'
        }
    
    @pytest.mark.asyncio
    async def test_validate_file_valid_text(self, handler, sample_text_file):
        """Test validation of valid text file."""
        result = await handler.validate_file(sample_text_file)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
    
    @pytest.mark.asyncio
    async def test_validate_file_empty_content(self, handler):
        """Test validation of empty file."""
        empty_file = {
            'filename': 'empty.txt',
            'content_type': 'text/plain',
            'content': b''
        }
        
        result = await handler.validate_file(empty_file)
        
        assert result['valid'] is False
        assert 'File is empty' in result['errors']
    
    @pytest.mark.asyncio
    async def test_validate_file_too_large(self, handler):
        """Test validation of oversized file."""
        large_file = {
            'filename': 'large.txt',
            'content_type': 'text/plain',
            'content': b'x' * (handler.max_file_size + 1)
        }
        
        result = await handler.validate_file(large_file)
        
        assert result['valid'] is False
        assert any('exceeds maximum' in error for error in result['errors'])
    
    @pytest.mark.asyncio
    async def test_validate_file_suspicious_extension(self, handler):
        """Test validation of file with suspicious extension."""
        suspicious_file = {
            'filename': 'malware.exe',
            'content_type': 'application/octet-stream',
            'content': b'fake executable content'
        }
        
        result = await handler.validate_file(suspicious_file)
        
        assert result['valid'] is False
        assert any('unsafe file extension' in error for error in result['errors'])
    
    @pytest.mark.asyncio
    async def test_process_text_file(self, handler, sample_text_file):
        """Test processing of text file."""
        processed = await handler._process_single_file(sample_text_file)
        
        assert processed is not None
        assert processed['content'] == 'This is a test document with some content for processing.'
        assert processed['source'] == 'test.txt'
        assert processed['source_type'] == 'upload'
        assert processed['content_type'] == 'text/plain'
        assert processed['metadata']['original_filename'] == 'test.txt'
    
    @pytest.mark.asyncio
    async def test_process_markdown_file(self, handler, sample_markdown_file):
        """Test processing of markdown file."""
        processed = await handler._process_single_file(sample_markdown_file)
        
        assert processed is not None
        assert 'Test Document' in processed['content']
        assert 'markdown' in processed['content']
        assert 'links' in processed['content']
        # Check that markdown syntax is cleaned up
        assert '**' not in processed['content']
        assert '[' not in processed['content']
        assert '```' not in processed['content']
    
    @pytest.mark.asyncio
    async def test_process_multiple_files(self, handler, sample_text_file, sample_markdown_file):
        """Test processing multiple files."""
        files = [sample_text_file, sample_markdown_file]
        
        processed_docs = await handler.process_uploaded_files(files)
        
        assert len(processed_docs) == 2
        assert all(doc['source_type'] == 'upload' for doc in processed_docs)
        assert any(doc['source'] == 'test.txt' for doc in processed_docs)
        assert any(doc['source'] == 'test.md' for doc in processed_docs)
    
    @pytest.mark.asyncio
    async def test_process_too_many_files(self, handler, sample_text_file):
        """Test processing too many files at once."""
        files = [sample_text_file] * (handler.max_files_per_batch + 1)
        
        with pytest.raises(ValueError, match="Too many files"):
            await handler.process_uploaded_files(files)
    
    @pytest.mark.asyncio
    async def test_process_unsupported_file_type(self, handler):
        """Test processing unsupported file type."""
        unsupported_file = {
            'filename': 'test.xyz',
            'content_type': 'application/unknown',
            'content': b'some content'
        }
        
        with pytest.raises(ValueError, match="Unsupported"):
            await handler._process_single_file(unsupported_file)
    
    def test_get_supported_types(self, handler):
        """Test getting supported file types."""
        supported_types = handler.get_supported_types()
        
        assert 'text/plain' in supported_types
        assert 'text/markdown' in supported_types
        assert 'application/pdf' in supported_types
        assert 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in supported_types
    
    def test_get_file_info(self, handler, sample_text_file):
        """Test getting file information."""
        file_info = handler.get_file_info(sample_text_file)
        
        assert file_info['filename'] == 'test.txt'
        assert file_info['content_type'] == 'text/plain'
        assert file_info['file_size'] > 0
        assert file_info['supported'] is True
        assert file_info['processor_available'] is True
    
    @pytest.mark.asyncio
    async def test_text_file_encoding_handling(self, handler):
        """Test handling of different text encodings."""
        # Test UTF-8 with BOM
        utf8_bom_file = {
            'filename': 'utf8_bom.txt',
            'content_type': 'text/plain',
            'content': '\ufeffThis is UTF-8 with BOM'.encode('utf-8-sig')
        }
        
        processed = await handler._process_single_file(utf8_bom_file)
        assert processed['content'] == 'This is UTF-8 with BOM'
        
        # Test Latin-1 encoding
        latin1_file = {
            'filename': 'latin1.txt',
            'content_type': 'text/plain',
            'content': 'Café résumé'.encode('latin-1')
        }
        
        processed = await handler._process_single_file(latin1_file)
        assert 'Café' in processed['content']
    
    @pytest.mark.asyncio
    async def test_markdown_cleanup(self, handler):
        """Test markdown syntax cleanup."""
        markdown_content = b'# Header\n\n**Bold** and *italic* text.\n\n[Link](http://example.com)\n\n```code block```\n\n`inline code`'
        
        result = await handler._process_markdown_file(markdown_content, 'test.md')
        
        # Check that markdown syntax is removed
        assert '#' not in result
        assert '**' not in result
        assert '*' not in result
        assert '[' not in result
        assert ']' not in result
        assert '```' not in result
        assert '`' not in result
        
        # Check that content is preserved
        assert 'Header' in result
        assert 'Bold' in result
        assert 'italic' in result
        assert 'Link' in result
        assert 'inline code' in result


if __name__ == '__main__':
    pytest.main([__file__])