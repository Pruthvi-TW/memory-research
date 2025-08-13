import re
from typing import List, Dict, Any
from pathlib import Path

from services.integration_service import IntegrationService
from core.database.document_processor import DocumentProcessor


class ContextService:
    """
    Enhanced context service that orchestrates integrated vector + graph operations.
    
    This service provides high-level context operations by coordinating
    between vector search and graph database functionality.
    """
    
    def __init__(self, integration_service: IntegrationService):
        self.integration_service = integration_service
        self.document_processor = DocumentProcessor()
        
    async def initialize_integrated_context(self, lending_path: str) -> Dict[str, int]:
        """
        Initialize both vector store and graph database with lending context.
        
        Args:
            lending_path: Path to the lending directory
            
        Returns:
            Dictionary containing initialization statistics
        """
        print(f"🚀 Starting integrated context initialization from: {lending_path}")
        
        # Validate path exists
        lending_dir = Path(lending_path)
        if not lending_dir.exists():
            raise FileNotFoundError(f"Lending directory not found: {lending_path}")
        
        # Initialize vector store
        print("📊 Initializing vector store...")
        vector_stats = await self.integration_service.vector_service.add_documents_from_directory(lending_path)
        
        # Initialize graph database
        print("🕸️ Initializing graph database...")
        graph_stats = await self._initialize_graph_context(lending_path)
        
        # Combined statistics
        combined_stats = {
            "vector_store": vector_stats,
            "graph_database": graph_stats,
            "integration": {
                "total_documents": max(
                    vector_stats.get("documents_processed", 0),
                    graph_stats.get("documents", 0)
                ),
                "processing_method": "integrated_vector_graph"
            }
        }
        
        print(f"✅ Integrated context initialization complete: {combined_stats}")
        return combined_stats
        
    async def _initialize_graph_context(self, lending_path: str) -> Dict[str, int]:
        """Initialize graph database with lending context"""
        lending_dir = Path(lending_path)
        
        # Clear existing graph data
        print("🗑️ Clearing existing graph data...")
        await self.integration_service.context_repository.clear_all_context_data()
        
        stats = {
            "documents": 0,
            "capabilities": 0,
            "guidelines": 0,
            "business_flows": 0,
            "concepts": 0,
            "relationships": 0
        }
        
        # Process common guidelines
        common_prompts_path = lending_dir / "CommonPrompts"
        if common_prompts_path.exists():
            await self._process_common_guidelines(common_prompts_path, stats)
            
        # Process capabilities
        capabilities_path = lending_dir / "Capabilities"
        if capabilities_path.exists():
            await self._process_capabilities(capabilities_path, stats)
            
        # Create concept relationships
        relationships_created = await self.integration_service.context_repository.create_concept_relationships()
        stats["relationships"] = relationships_created
        
        return stats
        
    async def _process_common_guidelines(self, path: Path, stats: Dict[str, int]):
        """Process common guidelines and prompts"""
        for file_path in path.glob("*.txt"):
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # Create guideline
                guideline_data = {
                    "name": file_path.stem,
                    "content": content,
                    "source_file": str(file_path),
                    "type": "common_guideline"
                }
                guideline_id = await self.integration_service.context_repository.create_guideline(guideline_data)
                
                # Extract and create concepts
                concepts = self._extract_concepts(content)
                for concept in concepts:
                    await self.integration_service.context_repository.create_or_merge_concept(concept)
                    await self.integration_service.context_repository.link_guideline_concept(guideline_id, concept["name"])
                    stats["concepts"] += 1
                    
                stats["guidelines"] += 1
                print(f"📄 Processed guideline: {file_path.name}")
                
            except Exception as e:
                print(f"⚠️ Error processing guideline {file_path}: {e}")
                
    async def _process_capabilities(self, path: Path, stats: Dict[str, int]):
        """Process capability-specific prompts and flows"""
        for capability_dir in path.iterdir():
            if not capability_dir.is_dir():
                continue
                
            try:
                capability_name = capability_dir.name
                
                # Create capability
                capability_id = await self.integration_service.context_repository.create_capability(capability_name)
                stats["capabilities"] += 1
                
                # Process prompt files in capability
                for prompt_dir in capability_dir.glob("*-prompt"):
                    await self._process_capability_prompts(
                        prompt_dir, capability_name, capability_id, stats
                    )
                    
                print(f"🎯 Processed capability: {capability_name}")
                
            except Exception as e:
                print(f"⚠️ Error processing capability {capability_dir}: {e}")
                
    async def _process_capability_prompts(self, prompt_dir: Path, capability_name: str, 
                                        capability_id: str, stats: Dict[str, int]):
        """Process individual capability prompt files"""
        for file_path in prompt_dir.glob("*.txt"):
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # Create document
                document_data = {
                    "content": content,
                    "source_file": str(file_path),
                    "type": "capability_prompt",
                    "capability": capability_name
                }
                doc_id = await self.integration_service.context_repository.create_document(document_data)
                
                # Link document to capability
                await self.integration_service.context_repository.link_capability_document(capability_id, doc_id)
                
                # Extract and create business flows
                business_flows = self._extract_business_flows(content)
                for flow in business_flows:
                    flow["capability"] = capability_name
                    flow_id = await self.integration_service.context_repository.create_business_flow(flow)
                    await self.integration_service.context_repository.link_document_business_flow(doc_id, flow_id)
                    stats["business_flows"] += 1
                    
                # Extract and create concepts
                concepts = self._extract_concepts(content)
                for concept in concepts:
                    await self.integration_service.context_repository.create_or_merge_concept(concept)
                    await self.integration_service.context_repository.link_document_concept(doc_id, concept["name"])
                    stats["concepts"] += 1
                    
                stats["documents"] += 1
                
            except Exception as e:
                print(f"⚠️ Error processing prompt file {file_path}: {e}")
                
    def _extract_concepts(self, content: str) -> List[Dict[str, Any]]:
        """Extract key concepts from content using pattern matching"""
        concepts = []
        
        # Extract technical terms and patterns
        patterns = [
            r'\b[A-Z]{2,}\b',  # Acronyms like PAN, OTP, API
            r'\b\w+(?:Service|Controller|Repository|Entity)\b',  # Java class patterns
            r'\b(?:Phase|Step|Trigger|Validation|Response)\s+\d+\b',  # Process steps
            r'\b(?:Request|Response|Payload|Status|Error)\b',  # API terms
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in set(matches):  # Remove duplicates
                if len(match) > 2:  # Filter out very short matches
                    concepts.append({
                        "name": match.upper(),
                        "type": "technical_term",
                        "context": self._get_context_around_match(content, match),
                        "keywords": [match.upper()]
                    })
                    
        return concepts[:10]  # Limit to top 10 concepts per document
        
    def _extract_business_flows(self, content: str) -> List[Dict[str, Any]]:
        """Extract business flow information from content"""
        flows = []
        
        # Look for phase/step patterns
        phase_pattern = r'Phase\s+(\d+):\s*([^\n]+)'
        phases = re.findall(phase_pattern, content, re.IGNORECASE)
        
        for phase_num, phase_title in phases:
            flows.append({
                "name": f"Phase {phase_num}: {phase_title.strip()}",
                "type": "business_phase",
                "order": int(phase_num),
                "description": self._get_context_around_match(content, f"Phase {phase_num}")
            })
            
        return flows
        
    def _get_context_around_match(self, content: str, match: str, context_size: int = 200) -> str:
        """Get context around a matched term"""
        match_pos = content.lower().find(match.lower())
        if match_pos == -1:
            return ""
            
        start = max(0, match_pos - context_size)
        end = min(len(content), match_pos + len(match) + context_size)
        return content[start:end].strip()
        
    async def get_integrated_context(self, query: str, max_items: int = 5) -> List[Dict[str, Any]]:
        """
        Get integrated context using both vector search and graph traversal.
        
        This is the main method that orchestrates the integrated search process.
        
        Args:
            query: User's search query
            max_items: Maximum number of context items to return
            
        Returns:
            List of enriched context items with fusion scores
        """
        return await self.integration_service.get_integrated_context(query, max_items)
        
    async def store_conversation(self, user_message: str, bot_response: str, 
                               session_id: str, context_used: List[Dict[str, Any]]):
        """
        Store conversation in the graph database.
        
        Args:
            user_message: The user's input message
            bot_response: The bot's response
            session_id: Session identifier
            context_used: List of context items used in generating the response
        """
        conversation_data = {
            "user_message": user_message,
            "bot_response": bot_response,
            "session_id": session_id
        }
        
        await self.integration_service.context_repository.store_conversation(
            conversation_data, context_used
        )
        
    async def get_context_statistics(self) -> Dict[str, Any]:
        """Get comprehensive context statistics from both vector and graph stores"""
        try:
            # Get integration statistics
            integration_stats = await self.integration_service.get_integration_statistics()
            
            # Get additional processing statistics
            vector_info = self.integration_service.vector_service.get_collection_info()
            
            return {
                "integration": integration_stats,
                "vector_store": vector_info,
                "status": "healthy" if vector_info.get("count", 0) > 0 else "empty"
            }
            
        except Exception as e:
            return {"error": str(e), "status": "error"}
            
    async def search_by_capability(self, query: str, capability: str, max_items: int = 3) -> List[Dict[str, Any]]:
        """
        Search for context within a specific capability.
        
        Args:
            query: Search query
            capability: Capability name (e.g., 'EKYC', 'PANNSDL')
            max_items: Maximum number of items to return
            
        Returns:
            List of context items from the specified capability
        """
        try:
            # Get vector results for this capability
            vector_results = await self.integration_service.vector_service.search_by_capability(
                query, capability, max_items
            )
            
            # Get graph results for this capability
            graph_documents = await self.integration_service.context_repository.get_documents_by_capability(capability)
            
            # Combine and rank results
            combined_results = []
            
            # Add vector results
            for result in vector_results:
                combined_results.append({
                    'id': f"vector_{result['metadata']['source']}_{result['metadata']['chunk_id']}",
                    'content': result['content'],
                    'type': 'document_chunk',
                    'source_file': result['metadata']['source'],
                    'capability': capability,
                    'vector_score': result['similarity'],
                    'graph_score': 0.0,
                    'fusion_score': result['similarity'] * 0.8,
                    'keywords': []
                })
                
            # Add graph results not already covered
            existing_sources = {item['source_file'] for item in combined_results}
            for doc in graph_documents[:max_items]:
                if doc['source_file'] not in existing_sources:
                    combined_results.append({
                        'id': f"graph_{doc['id']}",
                        'content': doc['content'],
                        'type': doc['type'],
                        'source_file': doc['source_file'],
                        'capability': capability,
                        'vector_score': 0.0,
                        'graph_score': 0.7,
                        'fusion_score': 0.7 * 0.6,
                        'keywords': []
                    })
                    
            # Sort by fusion score and return top results
            combined_results.sort(key=lambda x: x['fusion_score'], reverse=True)
            return combined_results[:max_items]
            
        except Exception as e:
            print(f"❌ Capability search error: {e}")
            return []
            
    async def get_capability_overview(self, capability_name: str) -> Dict[str, Any]:
        """Get comprehensive overview of a capability"""
        try:
            return await self.integration_service.context_repository.get_capability_overview(capability_name)
        except Exception as e:
            print(f"❌ Error getting capability overview: {e}")
            return {"error": str(e)}