"""
URL Content Extractor for fetching and processing web content.
Supports HTML parsing, PDF extraction, and plain text content.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse, urljoin
from datetime import datetime
import re

# HTML parsing
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

# PDF processing for URLs
try:
    import PyPDF2
    import io
    PDF_AVAILABLE = True
except ImportError:
    try:
        import pdfplumber
        import io
        PDF_AVAILABLE = True
        USE_PDFPLUMBER = True
    except ImportError:
        PDF_AVAILABLE = False
        USE_PDFPLUMBER = False

logger = logging.getLogger(__name__)


class URLContentExtractor:
    """
    Service for extracting content from URLs.
    Supports HTML, PDF, and plain text content extraction.
    """
    
    def __init__(self):
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.max_content_size = 5 * 1024 * 1024  # 5MB
        self.max_redirects = 5
        
        # Supported content types
        self.content_parsers = {
            'text/html': self._parse_html_content,
            'application/xhtml+xml': self._parse_html_content,
            'text/plain': self._parse_text_content,
            'application/pdf': self._parse_pdf_content if PDF_AVAILABLE else None,
        }
        
        # Rate limiting
        self.request_delay = 1.0  # seconds between requests
        self.last_request_time = 0
        
        logger.info("🌐 URLContentExtractor initialized")
        if not BS4_AVAILABLE:
            logger.warning("⚠️ HTML parsing not available - install beautifulsoup4")
        if not PDF_AVAILABLE:
            logger.warning("⚠️ PDF parsing not available - install PyPDF2 or pdfplumber")
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; DynamicContextBot/1.0)'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def extract_from_url(self, url: str) -> Dict[str, Any]:
        """
        Extract content from a URL.
        
        Args:
            url: URL to extract content from
            
        Returns:
            Dictionary with extracted content and metadata
        """
        if not self.session:
            raise RuntimeError("URLContentExtractor must be used as async context manager")
        
        try:
            # Rate limiting
            await self._apply_rate_limit()
            
            # Validate URL
            if not await self.validate_url(url):
                raise ValueError(f"Invalid or unsafe URL: {url}")
            
            # Fetch content
            content_data = await self._fetch_url_content(url)
            
            # Parse content based on type
            parsed_content = await self._parse_content(content_data)
            
            return {
                'url': url,
                'content': parsed_content['text'],
                'title': parsed_content.get('title', ''),
                'content_type': content_data['content_type'],
                'size': len(content_data['content']),
                'status_code': content_data['status_code'],
                'final_url': content_data['final_url'],
                'extraction_timestamp': datetime.now().isoformat(),
                'metadata': {
                    'original_url': url,
                    'final_url': content_data['final_url'],
                    'content_type': content_data['content_type'],
                    'content_length': len(content_data['content']),
                    'text_length': len(parsed_content['text']),
                    'word_count': len(parsed_content['text'].split()),
                    'title': parsed_content.get('title', ''),
                    'extraction_method': parsed_content.get('method', 'unknown')
                }
            }
            
        except Exception as e:
            logger.error(f"❌ URL content extraction failed for {url}: {e}")
            raise
    
    async def _apply_rate_limit(self):
        """Apply rate limiting between requests."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            await asyncio.sleep(self.request_delay - time_since_last)
        
        self.last_request_time = asyncio.get_event_loop().time()
    
    async def _fetch_url_content(self, url: str) -> Dict[str, Any]:
        """Fetch raw content from URL."""
        try:
            async with self.session.get(
                url,
                max_redirects=self.max_redirects,
                allow_redirects=True
            ) as response:
                
                # Check response status
                if response.status >= 400:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"HTTP {response.status}"
                    )
                
                # Check content length
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > self.max_content_size:
                    raise ValueError(f"Content too large: {content_length} bytes")
                
                # Read content with size limit
                content = await response.read()
                if len(content) > self.max_content_size:
                    raise ValueError(f"Content too large: {len(content)} bytes")
                
                return {
                    'content': content,
                    'content_type': response.headers.get('content-type', '').split(';')[0].strip(),
                    'status_code': response.status,
                    'final_url': str(response.url),
                    'headers': dict(response.headers)
                }
                
        except asyncio.TimeoutError:
            raise ValueError(f"Request timeout for URL: {url}")
        except aiohttp.ClientError as e:
            raise ValueError(f"Network error: {str(e)}")
    
    async def _parse_content(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse content based on content type."""
        content_type = content_data['content_type'].lower()
        content = content_data['content']
        
        # Find appropriate parser
        parser = None
        for supported_type, parser_func in self.content_parsers.items():
            if content_type.startswith(supported_type):
                parser = parser_func
                break
        
        if not parser:
            # Default to text parsing
            parser = self._parse_text_content
            logger.warning(f"⚠️ No specific parser for {content_type}, using text parser")
        
        return await parser(content, content_data)
    
    async def _parse_html_content(self, content: bytes, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse HTML content and extract text."""
        if not BS4_AVAILABLE:
            raise ValueError("HTML parsing not available - install beautifulsoup4")
        
        try:
            # Decode content
            text_content = self._decode_content(content)
            
            # Parse HTML
            soup = BeautifulSoup(text_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.decompose()
            
            # Extract title
            title = ""
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text().strip()
            
            # Extract main content
            # Try to find main content areas
            main_content = None
            for selector in ['main', 'article', '.content', '#content', '.post', '.entry']:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            if not main_content:
                main_content = soup.find('body') or soup
            
            # Extract text
            text = main_content.get_text()
            
            # Clean up text
            text = self._clean_extracted_text(text)
            
            return {
                'text': text,
                'title': title,
                'method': 'html_parser'
            }
            
        except Exception as e:
            logger.error(f"❌ HTML parsing error: {e}")
            # Fallback to text parsing
            return await self._parse_text_content(content, content_data)
    
    async def _parse_text_content(self, content: bytes, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse plain text content."""
        try:
            text = self._decode_content(content)
            text = self._clean_extracted_text(text)
            
            return {
                'text': text,
                'title': '',
                'method': 'text_parser'
            }
            
        except Exception as e:
            logger.error(f"❌ Text parsing error: {e}")
            raise
    
    async def _parse_pdf_content(self, content: bytes, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse PDF content from URL."""
        if not PDF_AVAILABLE:
            raise ValueError("PDF parsing not available - install PyPDF2 or pdfplumber")
        
        try:
            text_content = []
            
            if 'USE_PDFPLUMBER' in globals() and USE_PDFPLUMBER:
                # Use pdfplumber
                import pdfplumber
                
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_content.append(page_text)
            else:
                # Use PyPDF2
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text_content.append(page_text)
            
            if not text_content:
                raise ValueError("No text content extracted from PDF")
            
            # Join all pages and clean up
            full_text = '\n\n'.join(text_content)
            full_text = self._clean_extracted_text(full_text)
            
            return {
                'text': full_text,
                'title': '',
                'method': 'pdf_parser'
            }
            
        except Exception as e:
            logger.error(f"❌ PDF parsing error: {e}")
            raise
    
    def _decode_content(self, content: bytes) -> str:
        """Decode bytes content to string."""
        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        
        # If all fail, use utf-8 with error handling
        return content.decode('utf-8', errors='replace')
    
    def _clean_extracted_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive line breaks
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        
        # Remove common web artifacts
        text = re.sub(r'(Cookie|Privacy Policy|Terms of Service|Subscribe|Newsletter)', '', text, flags=re.IGNORECASE)
        
        # Remove URLs
        text = re.sub(r'https?://[^\s]+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+\.\S+', '', text)
        
        return text.strip()
    
    async def validate_url(self, url: str) -> bool:
        """
        Validate URL for safety and format.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid and safe
        """
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Check for localhost/private IPs (basic security)
            hostname = parsed.hostname
            if hostname:
                hostname = hostname.lower()
                
                # Block localhost
                if hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
                    return False
                
                # Block private IP ranges (basic check)
                if hostname.startswith(('192.168.', '10.', '172.')):
                    return False
                
                # Block file:// and other suspicious schemes
                if parsed.scheme not in ['http', 'https']:
                    return False
            
            return True
            
        except Exception:
            return False
    
    async def detect_content_type(self, url: str) -> Optional[str]:
        """
        Detect content type of URL without downloading full content.
        
        Args:
            url: URL to check
            
        Returns:
            Content type string or None
        """
        if not self.session:
            raise RuntimeError("URLContentExtractor must be used as async context manager")
        
        try:
            async with self.session.head(url, allow_redirects=True) as response:
                return response.headers.get('content-type', '').split(';')[0].strip()
                
        except Exception as e:
            logger.warning(f"⚠️ Could not detect content type for {url}: {e}")
            return None
    
    def get_supported_content_types(self) -> Dict[str, str]:
        """Get supported content types and their descriptions."""
        return {
            'text/html': 'HTML web pages',
            'application/xhtml+xml': 'XHTML web pages',
            'text/plain': 'Plain text content',
            'application/pdf': 'PDF documents' if PDF_AVAILABLE else 'PDF documents (not available)'
        }
    
    async def extract_multiple_urls(self, urls: list) -> Dict[str, Any]:
        """
        Extract content from multiple URLs concurrently.
        
        Args:
            urls: List of URLs to process
            
        Returns:
            Dictionary mapping URLs to extraction results
        """
        if len(urls) > 10:  # Limit concurrent requests
            raise ValueError("Too many URLs. Maximum 10 URLs allowed per batch")
        
        results = {}
        
        # Create tasks for concurrent processing
        tasks = []
        for url in urls:
            task = asyncio.create_task(self._extract_single_url_safe(url))
            tasks.append((url, task))
        
        # Wait for all tasks to complete
        for url, task in tasks:
            try:
                result = await task
                results[url] = result
            except Exception as e:
                results[url] = {
                    'error': str(e),
                    'success': False
                }
        
        return results
    
    async def _extract_single_url_safe(self, url: str) -> Dict[str, Any]:
        """Safely extract content from a single URL with error handling."""
        try:
            result = await self.extract_from_url(url)
            result['success'] = True
            return result
        except Exception as e:
            return {
                'error': str(e),
                'success': False,
                'url': url
            }