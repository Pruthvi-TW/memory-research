import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
import os
import asyncio
from pathlib import Path

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ SentenceTransformers import error: {e}")
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

from .document_processor import DocumentProcessor


class VectorService:
    """
    Vector service for semantic document search using Chroma DB.
    
    This service handles:
    - Document embedding and storage
    - Semantic similarity search
    - Vector database management
    """
    
    def __init__(self, persist_directory: str = "./vector/chroma_db"):
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                print(f"⚠️ Failed to load SentenceTransformer model: {e}")
                self.encoder = None
        else:
            self.encoder = None
            
        self.document_processor = DocumentProcessor()
        
    async def initialize(self):
        """Initialize the vector database"""
        try:
            # Ensure directory exists
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # Initialize Chroma client
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            self.collection = self.client.get_or_create_collection(
                name="lending_context",
                metadata={"hnsw:space": "cosine"}
            )
            
            print(f"📊 Vector store initialized with {self.collection.count()} documents")
            
        except Exception as e:
            print(f"❌ Vector service initialization error: {e}")
            raise
            
    async def add_documents_from_directory(self, lending_path: str) -> Dict[str, int]:
        """
        Add documents from lending directory to vector store.
        
        Args:
            lending_path: Path to the lending directory
            
        Returns:
            Dictionary with processing statistics
        """
        print(f"📁 Processing documents from: {lending_path}")
        
        # Clear existing documents
        if self.collection.count() > 0:
            print("🗑️ Clearing existing vector store...")
            self.client.delete_collection("lending_context")
            self.collection = self.client.create_collection(
                name="lending_context",
                metadata={"hnsw:space": "cosine"}
            )
        
        # Extract documents
        documents = await asyncio.to_thread(
            self.document_processor.extract_documents, lending_path
        )
        
        if not documents:
            print("⚠️ No documents found to process")
            return {"documents_processed": 0, "chunks_created": 0}
            
        # Process documents in batches
        batch_size = 50
        total_chunks = 0
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            await self._add_document_batch(batch)
            total_chunks += len(batch)
            print(f"📊 Processed {total_chunks}/{len(documents)} document chunks")
            
        stats = {
            "documents_processed": len(set(doc['source'] for doc in documents)),
            "chunks_created": total_chunks,
            "vector_store_count": self.collection.count()
        }
        
        print(f"✅ Vector store populated: {stats}")
        return stats
        
    async def _add_document_batch(self, documents: List[Dict[str, Any]]):
        """Add a batch of documents to the vector store"""
        if not documents:
            return
            
        if not self.encoder:
            print("⚠️ Cannot add documents: SentenceTransformer encoder not available")
            return
            
        try:
            # Generate embeddings
            contents = [doc['content'] for doc in documents]
            embeddings = await asyncio.to_thread(
                self.encoder.encode, contents
            )
            
            # Prepare data for Chroma
            ids = [f"{doc['source']}_{doc['chunk_id']}" for doc in documents]
            metadatas = [
                {
                    'source': doc['source'],
                    'chunk_id': doc['chunk_id'],
                    'type': doc.get('type', 'document'),
                    'capability': doc.get('capability', 'general'),
                    'source_type': doc.get('source_type', 'static'),  # Track if dynamic content
                    'processing_timestamp': doc.get('metadata', {}).get('processing_timestamp', ''),
                    'content_type': doc.get('metadata', {}).get('content_type', 'text/plain')
                } 
                for doc in documents
            ]
            
            # Add to collection
            self.collection.add(
                embeddings=embeddings.tolist(),
                documents=contents,
                metadatas=metadatas,
                ids=ids
            )
            
        except Exception as e:
            print(f"❌ Error adding document batch: {e}")
            raise
            
    async def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for semantically similar documents.
        
        Args:
            query: Search query
            n_results: Number of results to return
            
        Returns:
            List of matching documents with similarity scores
        """
        if not self.collection:
            print("⚠️ Vector service not initialized")
            return []
            
        if not self.encoder:
            print("⚠️ SentenceTransformer encoder not available")
            return []
            
        try:
            # Generate query embedding
            query_embedding = await asyncio.to_thread(
                self.encoder.encode, [query]
            )
            
            # Search in collection
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for doc, meta, dist in zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                ):
                    formatted_results.append({
                        'content': doc,
                        'metadata': meta,
                        'distance': dist,
                        'similarity': 1.0 - dist  # Convert distance to similarity
                    })
                    
            return formatted_results
            
        except Exception as e:
            print(f"❌ Vector search error: {e}")
            return []
            
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the vector collection"""
        if not self.collection:
            return {"count": 0, "name": "not_initialized"}
            
        try:
            return {
                "count": self.collection.count(),
                "name": self.collection.name,
                "metadata": self.collection.metadata
            }
        except Exception as e:
            return {"error": str(e)}
            
    async def search_by_capability(self, query: str, capability: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Search within a specific capability.
        
        Args:
            query: Search query
            capability: Capability name (e.g., 'EKYC', 'PANNSDL')
            n_results: Number of results to return
            
        Returns:
            List of matching documents from the specified capability
        """
        if not self.collection:
            raise RuntimeError("Vector service not initialized")
            
        try:
            # Generate query embedding
            query_embedding = await asyncio.to_thread(
                self.encoder.encode, [query]
            )
            
            # Search with capability filter
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=n_results * 2,  # Get more results to filter
                where={"capability": capability},
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format and limit results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for doc, meta, dist in zip(
                    results['documents'][0][:n_results],
                    results['metadatas'][0][:n_results],
                    results['distances'][0][:n_results]
                ):
                    formatted_results.append({
                        'content': doc,
                        'metadata': meta,
                        'distance': dist,
                        'similarity': 1.0 - dist
                    })
                    
            return formatted_results
            
        except Exception as e:
            print(f"❌ Capability search error: {e}")
            return []
            
    async def get_similar_documents(self, document_id: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Find documents similar to a given document.
        
        Args:
            document_id: ID of the reference document
            n_results: Number of similar documents to return
            
        Returns:
            List of similar documents
        """
        if not self.collection:
            raise RuntimeError("Vector service not initialized")
            
        try:
            # Get the reference document
            ref_doc = self.collection.get(ids=[document_id])
            
            if not ref_doc['documents']:
                return []
                
            # Use the reference document content as query
            ref_content = ref_doc['documents'][0]
            return await self.search(ref_content, n_results + 1)  # +1 to exclude self
            
        except Exception as e:
            print(f"❌ Similar documents search error: {e}")
            return []
            
    async def update_document(self, document_id: str, new_content: str, metadata: Dict[str, Any] = None):
        """
        Update an existing document in the vector store.
        
        Args:
            document_id: ID of the document to update
            new_content: New content for the document
            metadata: Optional metadata updates
        """
        if not self.collection:
            raise RuntimeError("Vector service not initialized")
            
        try:
            # Generate new embedding
            new_embedding = await asyncio.to_thread(
                self.encoder.encode, [new_content]
            )
            
            # Update the document
            update_data = {
                "ids": [document_id],
                "embeddings": new_embedding.tolist(),
                "documents": [new_content]
            }
            
            if metadata:
                update_data["metadatas"] = [metadata]
                
            self.collection.update(**update_data)
            
        except Exception as e:
            print(f"❌ Document update error: {e}")
            raise
            
    async def delete_documents_by_source(self, source_path: str):
        """
        Delete all documents from a specific source.
        
        Args:
            source_path: Source file path to delete documents from
        """
        if not self.collection:
            raise RuntimeError("Vector service not initialized")
            
        try:
            # Find documents from this source
            results = self.collection.get(
                where={"source": source_path}
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                print(f"🗑️ Deleted {len(results['ids'])} documents from {source_path}")
                
        except Exception as e:
            print(f"❌ Document deletion error: {e}")
            raise
    
    async def search_dynamic_content(self, query: str, source_types: List[str] = None, 
                                   n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search specifically for dynamic content.
        
        Args:
            query: Search query
            source_types: Filter by source types ('upload', 'url', 'github')
            n_results: Number of results to return
            
        Returns:
            List of matching dynamic documents with similarity scores
        """
        if not self.collection:
            print("⚠️ Vector service not initialized")
            return []
            
        if not self.encoder:
            print("⚠️ SentenceTransformer encoder not available")
            return []
            
        try:
            # Generate query embedding
            query_embedding = await asyncio.to_thread(
                self.encoder.encode, [query]
            )
            
            # Build where clause for dynamic content
            where_clause = {"source_type": {"$ne": "static"}}
            if source_types:
                where_clause["source_type"] = {"$in": source_types}
            
            # Search in collection with dynamic content filter
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=n_results * 2,  # Get more to filter
                where=where_clause,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for doc, meta, dist in zip(
                    results['documents'][0][:n_results],
                    results['metadatas'][0][:n_results],
                    results['distances'][0][:n_results]
                ):
                    formatted_results.append({
                        'content': doc,
                        'metadata': meta,
                        'distance': dist,
                        'similarity': 1.0 - dist,
                        'is_dynamic': True
                    })
                    
            return formatted_results
            
        except Exception as e:
            print(f"❌ Dynamic content search error: {e}")
            return []
    
    async def get_dynamic_content_stats(self) -> Dict[str, Any]:
        """Get statistics about dynamic content in the vector store"""
        if not self.collection:
            return {"error": "Vector service not initialized"}
            
        try:
            # Get all dynamic content
            dynamic_results = self.collection.get(
                where={"source_type": {"$ne": "static"}},
                include=['metadatas']
            )
            
            if not dynamic_results['metadatas']:
                return {
                    "total_dynamic_chunks": 0,
                    "source_types": [],
                    "content_types": []
                }
            
            # Analyze metadata
            source_types = {}
            content_types = {}
            
            for meta in dynamic_results['metadatas']:
                source_type = meta.get('source_type', 'unknown')
                content_type = meta.get('content_type', 'unknown')
                
                source_types[source_type] = source_types.get(source_type, 0) + 1
                content_types[content_type] = content_types.get(content_type, 0) + 1
            
            return {
                "total_dynamic_chunks": len(dynamic_results['metadatas']),
                "source_types": source_types,
                "content_types": content_types,
                "capabilities": list(set(meta.get('capability', 'DYNAMIC') for meta in dynamic_results['metadatas']))
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def delete_dynamic_content_by_source(self, source_identifier: str):
        """Delete all dynamic content from a specific source"""
        if not self.collection:
            raise RuntimeError("Vector service not initialized")
            
        try:
            # Find documents from this source
            results = self.collection.get(
                where={"source": source_identifier}
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                print(f"🗑️ Deleted {len(results['ids'])} dynamic chunks from {source_identifier}")
                return len(results['ids'])
            
            return 0
                
        except Exception as e:
            print(f"❌ Dynamic content deletion error: {e}")
            raise