"""
GitHub Repository Processor for fetching and processing repository content.
Supports documentation extraction from public GitHub repositories.
"""

import asyncio
import aiohttp
import logging
import base64
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class GitHubRepositoryProcessor:
    """
    Service for processing GitHub repositories and extracting documentation.
    """
    
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=60)
        
        # GitHub API settings
        self.api_base_url = "https://api.github.com"
        self.max_file_size = 1024 * 1024  # 1MB per file
        self.max_files_per_repo = 50
        
        # Supported file extensions for documentation
        self.supported_extensions = {
            '.md', '.txt', '.rst', '.py', '.js', '.ts', '.json', '.yml', '.yaml',
            '.java', '.cpp', '.c', '.h', '.hpp', '.go', '.rs', '.php', '.rb'
        }
        
        # Priority documentation files (processed first)
        self.priority_files = [
            'readme.md', 'readme.txt', 'readme.rst',
            'contributing.md', 'changelog.md', 'license.md',
            'docs/readme.md', 'documentation.md', 'api.md'
        ]
        
        # Directories to prioritize
        self.priority_dirs = ['docs', 'documentation', 'examples', 'guides']
        
        # Directories to skip
        self.skip_dirs = {
            '.git', '.github', 'node_modules', '__pycache__', '.pytest_cache',
            'venv', 'env', '.env', 'build', 'dist', 'target', 'bin', 'obj',
            '.vscode', '.idea', 'coverage', '.coverage', 'htmlcov'
        }
        
        logger.info("📚 GitHubRepositoryProcessor initialized")
    
    async def __aenter__(self):
        """Async context manager entry."""
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'DynamicContextBot/1.0'
        }
        
        if self.github_token:
            headers['Authorization'] = f'token {self.github_token}'
        
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            headers=headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def process_repository(self, repo_url: str) -> List[Dict[str, Any]]:
        """
        Process a GitHub repository and extract documentation files.
        
        Args:
            repo_url: GitHub repository URL
            
        Returns:
            List of processed documents with content and metadata
        """
        if not self.session:
            raise RuntimeError("GitHubRepositoryProcessor must be used as async context manager")
        
        try:
            # Parse repository URL
            owner, repo = self._parse_repo_url(repo_url)
            
            # Get repository information
            repo_info = await self._get_repository_info(owner, repo)
            
            # Get repository contents
            contents = await self._get_repository_contents(owner, repo)
            
            # Filter and prioritize files
            filtered_files = self._filter_documentation_files(contents)
            
            # Process files
            processed_docs = await self._process_repository_files(
                owner, repo, filtered_files, repo_info
            )
            
            logger.info(f"📚 Processed {len(processed_docs)} files from {owner}/{repo}")
            return processed_docs
            
        except Exception as e:
            logger.error(f"❌ Repository processing failed for {repo_url}: {e}")
            raise
    
    def _parse_repo_url(self, repo_url: str) -> tuple:
        """Parse GitHub repository URL to extract owner and repo name."""
        try:
            # Handle different URL formats
            if repo_url.startswith('https://github.com/'):
                path = repo_url.replace('https://github.com/', '')
            elif repo_url.startswith('github.com/'):
                path = repo_url.replace('github.com/', '')
            else:
                raise ValueError("Invalid GitHub URL format")
            
            # Remove .git suffix if present
            if path.endswith('.git'):
                path = path[:-4]
            
            # Split owner/repo
            parts = path.split('/')
            if len(parts) < 2:
                raise ValueError("Invalid repository path")
            
            owner, repo = parts[0], parts[1]
            
            # Validate names
            if not owner or not repo:
                raise ValueError("Owner and repository name are required")
            
            return owner, repo
            
        except Exception as e:
            raise ValueError(f"Failed to parse repository URL: {str(e)}")
    
    async def _get_repository_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information from GitHub API."""
        try:
            url = f"{self.api_base_url}/repos/{owner}/{repo}"
            
            async with self.session.get(url) as response:
                if response.status == 404:
                    raise ValueError(f"Repository {owner}/{repo} not found or not accessible")
                elif response.status == 403:
                    raise ValueError("API rate limit exceeded or repository is private")
                elif response.status != 200:
                    raise ValueError(f"GitHub API error: {response.status}")
                
                repo_info = await response.json()
                
                return {
                    'name': repo_info.get('name', repo),
                    'full_name': repo_info.get('full_name', f'{owner}/{repo}'),
                    'description': repo_info.get('description', ''),
                    'language': repo_info.get('language', ''),
                    'stars': repo_info.get('stargazers_count', 0),
                    'forks': repo_info.get('forks_count', 0),
                    'updated_at': repo_info.get('updated_at', ''),
                    'default_branch': repo_info.get('default_branch', 'main'),
                    'topics': repo_info.get('topics', [])
                }
                
        except aiohttp.ClientError as e:
            raise ValueError(f"Network error accessing repository: {str(e)}")
    
    async def _get_repository_contents(self, owner: str, repo: str, path: str = "") -> List[Dict[str, Any]]:
        """Get repository contents recursively."""
        try:
            url = f"{self.api_base_url}/repos/{owner}/{repo}/contents/{path}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"⚠️ Could not access path {path}: {response.status}")
                    return []
                
                contents = await response.json()
                
                # Handle single file response
                if isinstance(contents, dict):
                    contents = [contents]
                
                all_files = []
                
                for item in contents:
                    if item['type'] == 'file':
                        # Check file extension
                        file_path = item['path']
                        file_ext = '.' + file_path.split('.')[-1].lower() if '.' in file_path else ''
                        
                        if file_ext in self.supported_extensions:
                            all_files.append(item)
                    
                    elif item['type'] == 'dir':
                        # Skip certain directories
                        dir_name = item['name'].lower()
                        if dir_name not in self.skip_dirs:
                            # Recursively get directory contents
                            subdir_files = await self._get_repository_contents(
                                owner, repo, item['path']
                            )
                            all_files.extend(subdir_files)
                
                return all_files
                
        except Exception as e:
            logger.warning(f"⚠️ Error getting contents for path {path}: {e}")
            return []
    
    def _filter_documentation_files(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter and prioritize documentation files."""
        if len(files) > self.max_files_per_repo:
            logger.warning(f"⚠️ Repository has {len(files)} files, limiting to {self.max_files_per_repo}")
        
        # Separate priority files
        priority_files = []
        regular_files = []
        
        for file_info in files:
            file_path = file_info['path'].lower()
            file_name = file_info['name'].lower()
            
            # Check if it's a priority file
            is_priority = False
            
            # Check priority file names
            for priority_name in self.priority_files:
                if file_name == priority_name or file_path.endswith(priority_name):
                    is_priority = True
                    break
            
            # Check priority directories
            if not is_priority:
                for priority_dir in self.priority_dirs:
                    if file_path.startswith(f'{priority_dir}/'):
                        is_priority = True
                        break
            
            if is_priority:
                priority_files.append(file_info)
            else:
                regular_files.append(file_info)
        
        # Sort priority files by importance
        priority_files.sort(key=lambda x: self._get_file_priority_score(x['path']))
        
        # Sort regular files by path
        regular_files.sort(key=lambda x: x['path'])
        
        # Combine and limit
        filtered_files = priority_files + regular_files
        return filtered_files[:self.max_files_per_repo]
    
    def _get_file_priority_score(self, file_path: str) -> int:
        """Get priority score for a file (lower is higher priority)."""
        file_path_lower = file_path.lower()
        
        # README files have highest priority
        if 'readme' in file_path_lower:
            return 0
        
        # Documentation files
        if any(doc_word in file_path_lower for doc_word in ['doc', 'guide', 'tutorial']):
            return 1
        
        # API/specification files
        if any(api_word in file_path_lower for api_word in ['api', 'spec', 'schema']):
            return 2
        
        # Configuration files
        if file_path_lower.endswith(('.json', '.yml', '.yaml', '.toml')):
            return 3
        
        # Source code files
        return 4
    
    async def _process_repository_files(self, owner: str, repo: str, 
                                      files: List[Dict[str, Any]], 
                                      repo_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process individual repository files."""
        processed_docs = []
        
        for file_info in files:
            try:
                # Check file size
                if file_info.get('size', 0) > self.max_file_size:
                    logger.warning(f"⚠️ Skipping large file: {file_info['path']} ({file_info['size']} bytes)")
                    continue
                
                # Get file content
                file_content = await self._get_file_content(owner, repo, file_info)
                
                if not file_content:
                    continue
                
                # Create processed document
                processed_doc = {
                    'content': file_content,
                    'source': f"{owner}/{repo}/{file_info['path']}",
                    'source_type': 'github',
                    'file_path': file_info['path'],
                    'repository': f"{owner}/{repo}",
                    'metadata': {
                        'repository_name': repo_info['name'],
                        'repository_full_name': repo_info['full_name'],
                        'repository_description': repo_info['description'],
                        'repository_language': repo_info['language'],
                        'repository_stars': repo_info['stars'],
                        'file_path': file_info['path'],
                        'file_name': file_info['name'],
                        'file_size': file_info.get('size', 0),
                        'file_extension': self._get_file_extension(file_info['path']),
                        'character_count': len(file_content),
                        'word_count': len(file_content.split()),
                        'extraction_timestamp': datetime.now().isoformat(),
                        'github_url': file_info.get('html_url', ''),
                        'repository_topics': repo_info.get('topics', [])
                    }
                }
                
                processed_docs.append(processed_doc)
                logger.info(f"📄 Processed file: {file_info['path']}")
                
            except Exception as e:
                logger.warning(f"⚠️ Error processing file {file_info['path']}: {e}")
                continue
        
        return processed_docs
    
    async def _get_file_content(self, owner: str, repo: str, file_info: Dict[str, Any]) -> Optional[str]:
        """Get content of a specific file."""
        try:
            # Use the download URL for raw content
            download_url = file_info.get('download_url')
            if download_url:
                async with self.session.get(download_url) as response:
                    if response.status == 200:
                        content_bytes = await response.read()
                        return self._decode_file_content(content_bytes, file_info['path'])
            
            # Fallback to API content (base64 encoded)
            url = f"{self.api_base_url}/repos/{owner}/{repo}/contents/{file_info['path']}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                
                file_data = await response.json()
                
                if file_data.get('encoding') == 'base64':
                    content_bytes = base64.b64decode(file_data['content'])
                    return self._decode_file_content(content_bytes, file_info['path'])
                
                return None
                
        except Exception as e:
            logger.warning(f"⚠️ Error getting file content for {file_info['path']}: {e}")
            return None
    
    def _decode_file_content(self, content_bytes: bytes, file_path: str) -> str:
        """Decode file content from bytes to string."""
        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                content = content_bytes.decode(encoding)
                
                # Clean up content
                content = content.replace('\r\n', '\n').replace('\r', '\n')
                
                # For code files, add some context
                if self._is_code_file(file_path):
                    content = f"# File: {file_path}\n\n{content}"
                
                return content.strip()
                
            except UnicodeDecodeError:
                continue
        
        # If all encodings fail, use utf-8 with error handling
        return content_bytes.decode('utf-8', errors='replace')
    
    def _is_code_file(self, file_path: str) -> bool:
        """Check if file is a code file."""
        code_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.hpp', '.go', '.rs', '.php', '.rb'}
        file_ext = '.' + file_path.split('.')[-1].lower() if '.' in file_path else ''
        return file_ext in code_extensions
    
    def _get_file_extension(self, file_path: str) -> str:
        """Get file extension."""
        return '.' + file_path.split('.')[-1].lower() if '.' in file_path else ''
    
    async def validate_repository_url(self, repo_url: str) -> bool:
        """
        Validate GitHub repository URL.
        
        Args:
            repo_url: Repository URL to validate
            
        Returns:
            True if URL is valid and accessible
        """
        try:
            # Parse URL
            owner, repo = self._parse_repo_url(repo_url)
            
            # Check if repository exists and is accessible
            if not self.session:
                async with self:
                    repo_info = await self._get_repository_info(owner, repo)
            else:
                repo_info = await self._get_repository_info(owner, repo)
            
            return repo_info is not None
            
        except Exception as e:
            logger.warning(f"⚠️ Repository validation failed: {e}")
            return False
    
    def get_supported_extensions(self) -> set:
        """Get supported file extensions."""
        return self.supported_extensions.copy()
    
    async def get_repository_summary(self, repo_url: str) -> Dict[str, Any]:
        """
        Get a summary of repository without processing all files.
        
        Args:
            repo_url: Repository URL
            
        Returns:
            Repository summary information
        """
        if not self.session:
            raise RuntimeError("GitHubRepositoryProcessor must be used as async context manager")
        
        try:
            owner, repo = self._parse_repo_url(repo_url)
            repo_info = await self._get_repository_info(owner, repo)
            
            # Get basic contents info
            contents = await self._get_repository_contents(owner, repo)
            filtered_files = self._filter_documentation_files(contents)
            
            return {
                'repository': repo_info,
                'total_files': len(contents),
                'documentation_files': len(filtered_files),
                'file_types': self._analyze_file_types(filtered_files),
                'estimated_processing_time': len(filtered_files) * 2  # seconds
            }
            
        except Exception as e:
            logger.error(f"❌ Repository summary failed: {e}")
            raise
    
    def _analyze_file_types(self, files: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze file types in the repository."""
        file_types = {}
        
        for file_info in files:
            file_ext = self._get_file_extension(file_info['path'])
            file_types[file_ext] = file_types.get(file_ext, 0) + 1
        
        return file_types