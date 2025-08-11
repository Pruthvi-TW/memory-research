import os
import re
from typing import List, Dict, Any
from pathlib import Path


class DocumentProcessor:
    """
    Document processor for extracting and chunking text documents
    from the lending directory structure.
    """
    
    def __init__(self):
        self.supported_extensions = {'.txt', '.md', '.xml', '.java', '.py', '.js', '.json', '.yml', '.yaml'}
        self.chunk_size = 1000  # Characters per chunk
        self.chunk_overlap = 200  # Overlap between chunks
        
    def extract_documents(self, lending_dir: str) -> List[Dict[str, Any]]:
        """
        Extract all supported documents from the lending directory.
        
        Args:
            lending_dir: Path to the lending directory
            
        Returns:
            List of document chunks with metadata
        """
        documents = []
        lending_path = Path(lending_dir)
        
        if not lending_path.exists():
            raise FileNotFoundError(f"Lending directory not found: {lending_dir}")
            
        print(f"📁 Scanning directory: {lending_path}")
        
        # Walk through all files in the directory
        for file_path in self._get_all_files(lending_path):
            try:
                # Determine capability from path
                capability = self._extract_capability_from_path(file_path)
                
                # Read and process file
                content = self._read_file(file_path)
                if content:
                    chunks = self._chunk_content(content, str(file_path), capability)
                    documents.extend(chunks)
                    print(f"📄 Processed: {file_path.name} ({len(chunks)} chunks)")
                    
            except Exception as e:
                print(f"⚠️ Error processing {file_path}: {e}")
                continue
                
        print(f"✅ Extracted {len(documents)} document chunks from {len(set(doc['source'] for doc in documents))} files")
        return documents
        
    def _get_all_files(self, directory: Path) -> List[Path]:
        """Get all supported files from directory recursively"""
        files = []
        
        for item in directory.rglob('*'):
            if item.is_file() and item.suffix.lower() in self.supported_extensions:
                # Skip hidden files and common non-content files
                if not item.name.startswith('.') and not self._is_excluded_file(item):
                    files.append(item)
                    
        return files
        
    def _is_excluded_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from processing"""
        excluded_patterns = [
            'package-lock.json',
            'node_modules',
            '.git',
            '__pycache__',
            '.pyc',
            '/test/',
            '/spec/',
            'test.py',
            'spec.py'
        ]
        
        file_str = str(file_path).lower()
        return any(pattern in file_str for pattern in excluded_patterns)
        
    def _read_file(self, file_path: Path) -> str:
        """Read file content with proper encoding handling"""
        encodings = ['utf-8', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    
                # Basic content validation
                if len(content.strip()) < 10:  # Skip very short files
                    return None
                    
                return content
                
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"⚠️ Error reading {file_path}: {e}")
                return None
                
        print(f"⚠️ Could not decode {file_path} with any encoding")
        return None
        
    def _extract_capability_from_path(self, file_path: Path) -> str:
        """Extract capability name from file path"""
        path_parts = file_path.parts
        
        # Look for capability indicators in path
        capability_indicators = ['EKYC', 'PANNSDL', 'OTP', 'VERIFICATION']
        
        for part in path_parts:
            part_upper = part.upper()
            for indicator in capability_indicators:
                if indicator in part_upper:
                    return indicator
                    
        # Check if it's in Capabilities directory
        if 'Capabilities' in path_parts:
            # Find the capability directory name
            cap_index = path_parts.index('Capabilities')
            if cap_index + 1 < len(path_parts):
                return path_parts[cap_index + 1].upper()
                
        # Check if it's in CommonPrompts
        if 'CommonPrompts' in path_parts:
            return 'COMMON'
            
        return 'GENERAL'
        
    def _chunk_content(self, content: str, source_file: str, capability: str) -> List[Dict[str, Any]]:
        """
        Split content into manageable chunks with overlap.
        
        Args:
            content: File content to chunk
            source_file: Source file path
            capability: Capability category
            
        Returns:
            List of document chunks
        """
        # Clean and normalize content
        cleaned_content = self._clean_content(content)
        
        if len(cleaned_content) <= self.chunk_size:
            # Content is small enough to be a single chunk
            return [{
                'content': cleaned_content,
                'source': source_file,
                'chunk_id': 0,
                'type': self._determine_content_type(source_file),
                'capability': capability,
                'metadata': {
                    'file_size': len(content),
                    'chunk_count': 1
                }
            }]
            
        # Split into overlapping chunks
        chunks = []
        start = 0
        chunk_id = 0
        
        while start < len(cleaned_content):
            # Calculate chunk end
            end = start + self.chunk_size
            
            # If this isn't the last chunk, try to break at a sentence or paragraph
            if end < len(cleaned_content):
                # Look for good break points (sentence endings, paragraphs)
                break_points = [
                    cleaned_content.rfind('\n\n', start, end),  # Paragraph break
                    cleaned_content.rfind('. ', start, end),    # Sentence break
                    cleaned_content.rfind('\n', start, end),    # Line break
                ]
                
                # Use the best break point found
                for break_point in break_points:
                    if break_point > start + self.chunk_size // 2:  # Don't break too early
                        end = break_point + 1
                        break
                        
            chunk_content = cleaned_content[start:end].strip()
            
            if chunk_content:  # Only add non-empty chunks
                chunks.append({
                    'content': chunk_content,
                    'source': source_file,
                    'chunk_id': chunk_id,
                    'type': self._determine_content_type(source_file),
                    'capability': capability,
                    'metadata': {
                        'file_size': len(content),
                        'chunk_count': -1,  # Will be updated after all chunks are created
                        'start_pos': start,
                        'end_pos': end
                    }
                })
                chunk_id += 1
                
            # Move start position with overlap
            start = max(start + self.chunk_size - self.chunk_overlap, end)
            
        # Update chunk count in metadata
        for chunk in chunks:
            chunk['metadata']['chunk_count'] = len(chunks)
            
        return chunks
        
    def _clean_content(self, content: str) -> str:
        """Clean and normalize content for better processing"""
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove common file artifacts
        content = re.sub(r'^\s*#.*$', '', content, flags=re.MULTILINE)  # Remove comment lines
        content = re.sub(r'^\s*//.*$', '', content, flags=re.MULTILINE)  # Remove // comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)  # Remove /* */ comments
        
        # Normalize line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove excessive blank lines
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        return content.strip()
        
    def _determine_content_type(self, file_path: str) -> str:
        """Determine content type based on file extension and path"""
        file_path_lower = file_path.lower()
        
        if file_path_lower.endswith('.java'):
            return 'java_code'
        elif file_path_lower.endswith('.py'):
            return 'python_code'
        elif file_path_lower.endswith('.js'):
            return 'javascript_code'
        elif file_path_lower.endswith('.json'):
            return 'json_config'
        elif file_path_lower.endswith(('.yml', '.yaml')):
            return 'yaml_config'
        elif file_path_lower.endswith('.xml'):
            return 'xml_config'
        elif file_path_lower.endswith('.md'):
            return 'markdown_doc'
        elif 'prompt' in file_path_lower:
            return 'prompt_template'
        elif 'guideline' in file_path_lower:
            return 'guideline_doc'
        else:
            return 'text_document'
            
    def get_processing_stats(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about processed documents"""
        if not documents:
            return {"total_documents": 0, "total_chunks": 0}
            
        # Count by capability
        capability_counts = {}
        type_counts = {}
        source_files = set()
        
        for doc in documents:
            capability = doc.get('capability', 'UNKNOWN')
            doc_type = doc.get('type', 'unknown')
            
            capability_counts[capability] = capability_counts.get(capability, 0) + 1
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
            source_files.add(doc['source'])
            
        return {
            "total_documents": len(source_files),
            "total_chunks": len(documents),
            "capabilities": capability_counts,
            "content_types": type_counts,
            "average_chunks_per_document": len(documents) / len(source_files) if source_files else 0
        }