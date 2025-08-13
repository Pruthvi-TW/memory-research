"""
Unit tests for GitHubRepositoryProcessor service.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import aiohttp
from core.processing.github_repository_processor import GitHubRepositoryProcessor


class TestGitHubRepositoryProcessor:
    
    @pytest.fixture
    def processor(self):
        return GitHubRepositoryProcessor()
    
    @pytest.fixture
    def mock_repo_info(self):
        return {
            'name': 'test-repo',
            'full_name': 'testuser/test-repo',
            'description': 'A test repository',
            'language': 'Python',
            'stargazers_count': 100,
            'forks_count': 20,
            'updated_at': '2023-01-01T00:00:00Z',
            'default_branch': 'main',
            'topics': ['python', 'testing']
        }
    
    @pytest.fixture
    def mock_file_contents(self):
        return [
            {
                'name': 'README.md',
                'path': 'README.md',
                'type': 'file',
                'size': 1000,
                'download_url': 'https://raw.githubusercontent.com/testuser/test-repo/main/README.md',
                'html_url': 'https://github.com/testuser/test-repo/blob/main/README.md'
            },
            {
                'name': 'main.py',
                'path': 'src/main.py',
                'type': 'file',
                'size': 2000,
                'download_url': 'https://raw.githubusercontent.com/testuser/test-repo/main/src/main.py',
                'html_url': 'https://github.com/testuser/test-repo/blob/main/src/main.py'
            },
            {
                'name': 'docs',
                'path': 'docs',
                'type': 'dir'
            }
        ]
    
    def test_parse_repo_url_valid_urls(self, processor):
        """Test parsing valid GitHub repository URLs."""
        test_cases = [
            ('https://github.com/user/repo', ('user', 'repo')),
            ('https://github.com/user/repo.git', ('user', 'repo')),
            ('github.com/user/repo', ('user', 'repo')),
            ('https://github.com/org-name/repo-name', ('org-name', 'repo-name'))
        ]
        
        for url, expected in test_cases:
            result = processor._parse_repo_url(url)
            assert result == expected
    
    def test_parse_repo_url_invalid_urls(self, processor):
        """Test parsing invalid GitHub repository URLs."""
        invalid_urls = [
            'https://gitlab.com/user/repo',
            'https://github.com/user',
            'https://github.com/',
            'not-a-url',
            ''
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValueError):
                processor._parse_repo_url(url)
    
    def test_filter_documentation_files(self, processor):
        """Test filtering and prioritizing documentation files."""
        files = [
            {'name': 'main.py', 'path': 'src/main.py', 'type': 'file'},
            {'name': 'README.md', 'path': 'README.md', 'type': 'file'},
            {'name': 'api.md', 'path': 'docs/api.md', 'type': 'file'},
            {'name': 'test.py', 'path': 'tests/test.py', 'type': 'file'},
            {'name': 'config.json', 'path': 'config.json', 'type': 'file'}
        ]
        
        filtered = processor._filter_documentation_files(files)
        
        # README should be first (highest priority)
        assert filtered[0]['name'] == 'README.md'
        
        # API docs should be prioritized
        api_file = next((f for f in filtered if f['name'] == 'api.md'), None)
        assert api_file is not None
        
        # All files should be included (under limit)
        assert len(filtered) == len(files)
    
    def test_get_file_priority_score(self, processor):
        """Test file priority scoring."""
        # README files should have highest priority (lowest score)
        assert processor._get_file_priority_score('README.md') == 0
        assert processor._get_file_priority_score('docs/readme.txt') == 0
        
        # Documentation files should have high priority
        assert processor._get_file_priority_score('docs/guide.md') < processor._get_file_priority_score('src/main.py')
        
        # API files should be prioritized
        assert processor._get_file_priority_score('api.md') < processor._get_file_priority_score('utils.py')
    
    def test_is_code_file(self, processor):
        """Test code file detection."""
        code_files = ['main.py', 'app.js', 'Component.tsx', 'Main.java', 'lib.cpp']
        non_code_files = ['README.md', 'config.json', 'data.csv', 'image.png']
        
        for file_path in code_files:
            assert processor._is_code_file(file_path) is True
        
        for file_path in non_code_files:
            assert processor._is_code_file(file_path) is False
    
    def test_get_file_extension(self, processor):
        """Test file extension extraction."""
        test_cases = [
            ('file.py', '.py'),
            ('README.md', '.md'),
            ('config.json', '.json'),
            ('no_extension', ''),
            ('path/to/file.txt', '.txt')
        ]
        
        for file_path, expected_ext in test_cases:
            assert processor._get_file_extension(file_path) == expected_ext
    
    def test_decode_file_content(self, processor):
        """Test file content decoding."""
        # UTF-8 content
        utf8_content = 'Hello, 世界!'.encode('utf-8')
        decoded = processor._decode_file_content(utf8_content, 'test.txt')
        assert decoded == 'Hello, 世界!'
        
        # Code file with context
        code_content = 'print("Hello, World!")'.encode('utf-8')
        decoded = processor._decode_file_content(code_content, 'main.py')
        assert decoded.startswith('# File: main.py')
        assert 'print("Hello, World!")' in decoded
    
    def test_analyze_file_types(self, processor):
        """Test file type analysis."""
        files = [
            {'path': 'README.md'},
            {'path': 'main.py'},
            {'path': 'config.json'},
            {'path': 'another.py'},
            {'path': 'docs.md'}
        ]
        
        file_types = processor._analyze_file_types(files)
        
        assert file_types['.py'] == 2
        assert file_types['.md'] == 2
        assert file_types['.json'] == 1
    
    @pytest.mark.asyncio
    async def test_context_manager(self, processor):
        """Test async context manager functionality."""
        async with processor as proc:
            assert proc.session is not None
            assert isinstance(proc.session, aiohttp.ClientSession)
        
        # Session should be closed after context
        assert processor.session is None or processor.session.closed
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_get_repository_info_success(self, mock_session_class, processor, mock_repo_info):
        """Test successful repository info retrieval."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_repo_info)
        
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.close = AsyncMock()
        
        mock_session_class.return_value = mock_session
        
        async with processor as proc:
            result = await proc._get_repository_info('testuser', 'test-repo')
        
        assert result['name'] == 'test-repo'
        assert result['full_name'] == 'testuser/test-repo'
        assert result['description'] == 'A test repository'
        assert result['language'] == 'Python'
        assert result['stars'] == 100
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_get_repository_info_not_found(self, mock_session_class, processor):
        """Test repository not found error."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status = 404
        
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.close = AsyncMock()
        
        mock_session_class.return_value = mock_session
        
        async with processor as proc:
            with pytest.raises(ValueError, match="not found or not accessible"):
                await proc._get_repository_info('testuser', 'nonexistent-repo')
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_get_repository_contents(self, mock_session_class, processor, mock_file_contents):
        """Test repository contents retrieval."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_file_contents)
        
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.close = AsyncMock()
        
        mock_session_class.return_value = mock_session
        
        async with processor as proc:
            # Mock recursive call for directory
            with patch.object(proc, '_get_repository_contents', side_effect=[
                mock_file_contents,  # Initial call
                [{'name': 'guide.md', 'path': 'docs/guide.md', 'type': 'file', 'size': 500}]  # Recursive call
            ]):
                result = await proc._get_repository_contents('testuser', 'test-repo')
        
        # Should include files from root and subdirectory
        assert len(result) >= 2
        file_names = [f['name'] for f in result]
        assert 'README.md' in file_names
        assert 'main.py' in file_names
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_get_file_content_success(self, mock_session_class, processor):
        """Test successful file content retrieval."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b'# Test README\n\nThis is a test file.')
        
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.close = AsyncMock()
        
        mock_session_class.return_value = mock_session
        
        file_info = {
            'path': 'README.md',
            'download_url': 'https://raw.githubusercontent.com/testuser/test-repo/main/README.md'
        }
        
        async with processor as proc:
            result = await proc._get_file_content('testuser', 'test-repo', file_info)
        
        assert result is not None
        assert '# Test README' in result
        assert 'This is a test file.' in result
    
    @pytest.mark.asyncio
    async def test_validate_repository_url_valid(self, processor):
        """Test validation of valid repository URL."""
        with patch.object(processor, '_get_repository_info') as mock_get_info:
            mock_get_info.return_value = {'name': 'test-repo'}
            
            result = await processor.validate_repository_url('https://github.com/testuser/test-repo')
            assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_repository_url_invalid(self, processor):
        """Test validation of invalid repository URL."""
        with patch.object(processor, '_get_repository_info') as mock_get_info:
            mock_get_info.side_effect = ValueError("Repository not found")
            
            result = await processor.validate_repository_url('https://github.com/testuser/nonexistent')
            assert result is False
    
    def test_supported_extensions(self, processor):
        """Test getting supported file extensions."""
        extensions = processor.get_supported_extensions()
        
        assert '.md' in extensions
        assert '.py' in extensions
        assert '.js' in extensions
        assert '.json' in extensions
        assert isinstance(extensions, set)
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_get_repository_summary(self, mock_session_class, processor, mock_repo_info, mock_file_contents):
        """Test repository summary generation."""
        mock_session = Mock()
        
        # Mock repository info response
        mock_repo_response = Mock()
        mock_repo_response.status = 200
        mock_repo_response.json = AsyncMock(return_value=mock_repo_info)
        
        # Mock contents response
        mock_contents_response = Mock()
        mock_contents_response.status = 200
        mock_contents_response.json = AsyncMock(return_value=mock_file_contents)
        
        mock_session.get.return_value.__aenter__ = AsyncMock(side_effect=[
            mock_repo_response,  # Repository info call
            mock_contents_response  # Contents call
        ])
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.close = AsyncMock()
        
        mock_session_class.return_value = mock_session
        
        async with processor as proc:
            summary = await proc.get_repository_summary('https://github.com/testuser/test-repo')
        
        assert 'repository' in summary
        assert 'total_files' in summary
        assert 'documentation_files' in summary
        assert 'file_types' in summary
        assert 'estimated_processing_time' in summary
        
        assert summary['repository']['name'] == 'test-repo'
        assert summary['total_files'] >= 0
        assert summary['documentation_files'] >= 0
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_process_repository_full_workflow(self, mock_session_class, processor, mock_repo_info):
        """Test complete repository processing workflow."""
        mock_session = Mock()
        
        # Mock all required responses
        mock_repo_response = Mock()
        mock_repo_response.status = 200
        mock_repo_response.json = AsyncMock(return_value=mock_repo_info)
        
        mock_contents_response = Mock()
        mock_contents_response.status = 200
        mock_contents_response.json = AsyncMock(return_value=[
            {
                'name': 'README.md',
                'path': 'README.md',
                'type': 'file',
                'size': 500,
                'download_url': 'https://raw.githubusercontent.com/testuser/test-repo/main/README.md'
            }
        ])
        
        mock_file_response = Mock()
        mock_file_response.status = 200
        mock_file_response.read = AsyncMock(return_value=b'# Test Repository\n\nThis is a test repository.')
        
        mock_session.get.return_value.__aenter__ = AsyncMock(side_effect=[
            mock_repo_response,  # Repository info
            mock_contents_response,  # Contents
            mock_file_response  # File content
        ])
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.close = AsyncMock()
        
        mock_session_class.return_value = mock_session
        
        async with processor as proc:
            result = await proc.process_repository('https://github.com/testuser/test-repo')
        
        assert len(result) == 1
        doc = result[0]
        
        assert doc['source_type'] == 'github'
        assert doc['repository'] == 'testuser/test-repo'
        assert 'Test Repository' in doc['content']
        assert doc['metadata']['repository_name'] == 'test-repo'
        assert doc['metadata']['file_path'] == 'README.md'


if __name__ == '__main__':
    pytest.main([__file__])