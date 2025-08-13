"""
Unit tests for URLContentExtractor service.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import aiohttp
from core.processing.url_content_extractor import URLContentExtractor


class TestURLContentExtractor:
    
    @pytest.fixture
    def extractor(self):
        return URLContentExtractor()
    
    @pytest.fixture
    def mock_response(self):
        """Mock aiohttp response."""
        mock = Mock()
        mock.status = 200
        mock.headers = {'content-type': 'text/html; charset=utf-8'}
        mock.url = 'https://example.com'
        mock.read = AsyncMock(return_value=b'<html><head><title>Test Page</title></head><body><h1>Test Content</h1><p>This is test content.</p></body></html>')
        return mock
    
    @pytest.fixture
    def mock_session(self, mock_response):
        """Mock aiohttp session."""
        mock = Mock()
        mock.get = Mock()
        mock.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock.get.return_value.__aexit__ = AsyncMock(return_value=None)
        mock.head = Mock()
        mock.head.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock.head.return_value.__aexit__ = AsyncMock(return_value=None)
        mock.close = AsyncMock()
        return mock
    
    def test_url_validation_valid_urls(self, extractor):
        """Test validation of valid URLs."""
        valid_urls = [
            'https://example.com',
            'http://example.com/path',
            'https://subdomain.example.com/path?query=value'
        ]
        
        for url in valid_urls:
            assert asyncio.run(extractor.validate_url(url)) is True
    
    def test_url_validation_invalid_urls(self, extractor):
        """Test validation of invalid URLs."""
        invalid_urls = [
            'ftp://example.com',
            'https://localhost',
            'http://127.0.0.1',
            'https://192.168.1.1',
            'file:///etc/passwd',
            'javascript:alert(1)'
        ]
        
        for url in invalid_urls:
            assert asyncio.run(extractor.validate_url(url)) is False
    
    @pytest.mark.asyncio
    async def test_html_content_extraction(self, extractor):
        """Test HTML content extraction."""
        html_content = b'<html><head><title>Test Page</title></head><body><h1>Header</h1><p>This is test content.</p><script>alert("test");</script></body></html>'
        
        content_data = {
            'content': html_content,
            'content_type': 'text/html',
            'final_url': 'https://example.com'
        }
        
        result = await extractor._parse_html_content(html_content, content_data)
        
        assert 'Header' in result['text']
        assert 'This is test content.' in result['text']
        assert 'alert' not in result['text']  # Script should be removed
        assert result['title'] == 'Test Page'
        assert result['method'] == 'html_parser'
    
    @pytest.mark.asyncio
    async def test_text_content_extraction(self, extractor):
        """Test plain text content extraction."""
        text_content = b'This is plain text content.\n\nWith multiple paragraphs.'
        
        content_data = {
            'content': text_content,
            'content_type': 'text/plain'
        }
        
        result = await extractor._parse_text_content(text_content, content_data)
        
        assert 'This is plain text content.' in result['text']
        assert 'With multiple paragraphs.' in result['text']
        assert result['method'] == 'text_parser'
    
    @pytest.mark.asyncio
    async def test_content_decoding(self, extractor):
        """Test content decoding with different encodings."""
        # UTF-8 content
        utf8_content = 'Hello, 世界!'.encode('utf-8')
        decoded = extractor._decode_content(utf8_content)
        assert decoded == 'Hello, 世界!'
        
        # Latin-1 content
        latin1_content = 'Café résumé'.encode('latin-1')
        decoded = extractor._decode_content(latin1_content)
        assert 'Café' in decoded
    
    def test_text_cleaning(self, extractor):
        """Test text cleaning functionality."""
        dirty_text = """
        This   is    messy    text.
        
        
        
        With excessive whitespace.
        
        Cookie Policy: Accept all cookies.
        https://example.com/link
        contact@example.com
        """
        
        cleaned = extractor._clean_extracted_text(dirty_text)
        
        # Check whitespace normalization
        assert '   ' not in cleaned
        assert '\n\n\n' not in cleaned
        
        # Check artifact removal
        assert 'Cookie Policy' not in cleaned
        assert 'https://example.com/link' not in cleaned
        assert 'contact@example.com' not in cleaned
        
        # Check content preservation
        assert 'This is messy text.' in cleaned
        assert 'With excessive whitespace.' in cleaned
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, extractor):
        """Test rate limiting functionality."""
        extractor.request_delay = 0.1  # Short delay for testing
        
        start_time = asyncio.get_event_loop().time()
        
        # First request should not be delayed
        await extractor._apply_rate_limit()
        first_time = asyncio.get_event_loop().time()
        
        # Second request should be delayed
        await extractor._apply_rate_limit()
        second_time = asyncio.get_event_loop().time()
        
        # Check that delay was applied
        assert (second_time - first_time) >= extractor.request_delay
    
    @pytest.mark.asyncio
    async def test_context_manager(self, extractor):
        """Test async context manager functionality."""
        async with extractor as ext:
            assert ext.session is not None
            assert isinstance(ext.session, aiohttp.ClientSession)
        
        # Session should be closed after context
        assert extractor.session is None or extractor.session.closed
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_full_extraction_workflow(self, mock_session_class, extractor):
        """Test complete URL extraction workflow."""
        # Mock session and response
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {'content-type': 'text/html'}
        mock_response.url = 'https://example.com'
        mock_response.read = AsyncMock(return_value=b'<html><head><title>Test</title></head><body>Content</body></html>')
        
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.close = AsyncMock()
        
        mock_session_class.return_value = mock_session
        
        # Test extraction
        async with extractor as ext:
            result = await ext.extract_from_url('https://example.com')
        
        assert result['url'] == 'https://example.com'
        assert result['content_type'] == 'text/html'
        assert 'Content' in result['content']
        assert result['title'] == 'Test'
        assert 'metadata' in result
    
    @pytest.mark.asyncio
    async def test_error_handling_http_error(self, extractor):
        """Test handling of HTTP errors."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = Mock()
            mock_response = Mock()
            mock_response.status = 404
            
            # Create a proper ClientResponseError
            from aiohttp import ClientResponseError, RequestInfo
            from yarl import URL
            
            request_info = RequestInfo(
                url=URL('https://example.com'),
                method='GET',
                headers={},
                real_url=URL('https://example.com')
            )
            
            mock_session.get.return_value.__aenter__ = AsyncMock(
                side_effect=ClientResponseError(
                    request_info=request_info,
                    history=(),
                    status=404
                )
            )
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session
            
            async with extractor as ext:
                with pytest.raises(ValueError, match="HTTP 404"):
                    await ext.extract_from_url('https://example.com/notfound')
    
    @pytest.mark.asyncio
    async def test_content_size_limit(self, extractor):
        """Test content size limiting."""
        extractor.max_content_size = 100  # Small limit for testing
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = Mock()
            mock_response = Mock()
            mock_response.status = 200
            mock_response.headers = {'content-type': 'text/plain', 'content-length': '200'}
            
            mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session
            
            async with extractor as ext:
                with pytest.raises(ValueError, match="Content too large"):
                    await ext.extract_from_url('https://example.com/large')
    
    def test_supported_content_types(self, extractor):
        """Test getting supported content types."""
        supported_types = extractor.get_supported_content_types()
        
        assert 'text/html' in supported_types
        assert 'text/plain' in supported_types
        assert 'application/pdf' in supported_types
        assert isinstance(supported_types, dict)
    
    @pytest.mark.asyncio
    async def test_multiple_url_extraction(self, extractor):
        """Test extracting content from multiple URLs."""
        urls = ['https://example1.com', 'https://example2.com']
        
        with patch.object(extractor, '_extract_single_url_safe') as mock_extract:
            mock_extract.side_effect = [
                {'content': 'Content 1', 'success': True},
                {'content': 'Content 2', 'success': True}
            ]
            
            async with extractor as ext:
                results = await ext.extract_multiple_urls(urls)
            
            assert len(results) == 2
            assert results['https://example1.com']['success'] is True
            assert results['https://example2.com']['success'] is True
    
    @pytest.mark.asyncio
    async def test_too_many_urls(self, extractor):
        """Test handling too many URLs."""
        urls = [f'https://example{i}.com' for i in range(15)]  # More than limit
        
        async with extractor as ext:
            with pytest.raises(ValueError, match="Too many URLs"):
                await ext.extract_multiple_urls(urls)


if __name__ == '__main__':
    pytest.main([__file__])