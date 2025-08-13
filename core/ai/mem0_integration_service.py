"""
Enhanced Integration Service that combines mem0 memory with existing vector and graph layers.
Provides unified context retrieval with intelligent fusion of multiple data sources.
"""

import asyncio
from typing import List, Dict, Any, Optional
import logging
from concurrent.futures import ThreadPoolExecutor

from .mem0_manager import Mem0Manager

# Import existing services
from ..database.vector_service import VectorService
from ..database.context_repository import ContextRepository
from services.integration_service import IntegrationService

logger = logging.getLogger(__name__)


class Mem0IntegrationService:
    """
    Enhanced integration service that combines mem0 semantic memory 
    with existing vector and graph layers for superior context retrieval.
    """
    
    def __init__(self, memory_manager: Mem0Manager, 
                 vector_service: VectorService, 
                 context_repository: ContextRepository,
                 existing_integration_service: IntegrationService):
        """
        Initialize the enhanced integration service.
        
        Args:
            memory_manager: mem0 memory manager
            vector_service: Vector similarity service
            context_repository: Graph context repository
            existing_integration_service: Existing vector+graph integration
        """
        self.memory_manager = memory_manager
        self.vector_service = vector_service
        self.context_repository = context_repository
        self.existing_integration = existing_integration_service
        self.executor = ThreadPoolExecutor(max_workers=3)
        
    async def get_enhanced_context(self, query: str, max_items: int = 8) -> List[Dict[str, Any]]:
        """
        Get enhanced context by combining mem0, vector, and graph results.
        
        Args:
            query: User query for context retrieval
            max_items: Maximum number of context items to return
            
        Returns:
            List of enhanced context items with fusion scoring
        """
        try:
            logger.info(f"🔍 Getting enhanced context for: {query[:50]}...")
            
            # Run all context retrieval methods concurrently
            tasks = [
                self._get_memory_context(query, max_items // 2),
                self._get_existing_integrated_context(query, max_items // 2),
                self._get_conversation_context(query)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            memory_context = results[0] if not isinstance(results[0], Exception) else []
            integrated_context = results[1] if not isinstance(results[1], Exception) else []
            conversation_context = results[2] if not isinstance(results[2], Exception) else []
            
            # Combine and deduplicate contexts
            all_contexts = self._combine_contexts(
                memory_context, integrated_context, conversation_context
            )
            
            # Apply enhanced fusion scoring
            enhanced_contexts = self._apply_enhanced_fusion_scoring(all_contexts, query)
            
            # Sort by enhanced fusion score and return top items
            enhanced_contexts.sort(key=lambda x: x.get('enhanced_fusion_score', 0), reverse=True)
            
            final_contexts = enhanced_contexts[:max_items]
            
            logger.info(f"📊 Enhanced context retrieval: {len(final_contexts)} items from {len(all_contexts)} candidates")
            
            return final_contexts
            
        except Exception as e:
            logger.error(f"❌ Enhanced context retrieval error: {e}")
            # Fallback to existing integration service
            try:
                return await self.existing_integration.get_integrated_context(query, max_items)
            except:
                return []
                
    async def _get_memory_context(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Get context from mem0 memory"""
        try:
            loop = asyncio.get_event_loop()
            memory_results = await loop.run_in_executor(
                self.executor, 
                self.memory_manager.get_relevant_context, 
                query, 
                limit
            )
            
            # Add source identifier
            for result in memory_results:
                result['context_source'] = 'memory'
                result['memory_score'] = result.get('score', 0.0)
                
            return memory_results
            
        except Exception as e:
            logger.error(f"❌ Memory context error: {e}")
            return []
            
    async def _get_existing_integrated_context(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Get context from existing vector+graph integration"""
        try:
            integrated_results = await self.existing_integration.get_integrated_context(query, limit)
            
            # Add source identifier
            for result in integrated_results:
                result['context_source'] = 'integrated'
                
            return integrated_results
            
        except Exception as e:
            logger.error(f"❌ Integrated context error: {e}")
            return []
            
    async def _get_conversation_context(self, query: str) -> List[Dict[str, Any]]:
        """Get relevant conversation history"""
        try:
            loop = asyncio.get_event_loop()
            conversation_results = await loop.run_in_executor(
                self.executor,
                self.memory_manager.get_conversation_history,
                None,  # session_id
                3      # limit
            )
            
            # Filter conversations relevant to the query
            relevant_conversations = []
            query_words = set(query.lower().split())
            
            for conv in conversation_results:
                conv_content = conv.get('content', '').lower()
                conv_words = set(conv_content.split())
                
                # Calculate relevance based on word overlap
                overlap = len(query_words.intersection(conv_words))
                if overlap > 0:
                    conv['context_source'] = 'conversation'
                    conv['conversation_score'] = overlap / len(query_words)
                    relevant_conversations.append(conv)
                    
            return relevant_conversations
            
        except Exception as e:
            logger.error(f"❌ Conversation context error: {e}")
            return []
            
    def _combine_contexts(self, memory_context: List[Dict[str, Any]], 
                         integrated_context: List[Dict[str, Any]],
                         conversation_context: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Combine contexts from different sources and remove duplicates"""
        
        all_contexts = []
        seen_content = set()
        
        # Add memory contexts
        for ctx in memory_context:
            content_hash = hash(ctx.get('content', '')[:200])
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                all_contexts.append(ctx)
                
        # Add integrated contexts
        for ctx in integrated_context:
            content_hash = hash(ctx.get('content', '')[:200])
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                all_contexts.append(ctx)
                
        # Add conversation contexts
        for ctx in conversation_context:
            content_hash = hash(ctx.get('content', '')[:200])
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                all_contexts.append(ctx)
                
        return all_contexts
        
    def _apply_enhanced_fusion_scoring(self, contexts: List[Dict[str, Any]], 
                                     query: str) -> List[Dict[str, Any]]:
        """Apply enhanced fusion scoring that considers multiple factors"""
        
        query_words = set(query.lower().split())
        
        for ctx in contexts:
            scores = {
                'memory_score': ctx.get('memory_score', 0.0),
                'vector_score': ctx.get('vector_score', 0.0),
                'graph_score': ctx.get('graph_score', 0.0),
                'conversation_score': ctx.get('conversation_score', 0.0),
                'fusion_score': ctx.get('fusion_score', 0.0)
            }
            
            # Calculate content relevance
            content = ctx.get('content', '').lower()
            content_words = set(content.split())
            content_relevance = len(query_words.intersection(content_words)) / max(len(query_words), 1)
            
            # Calculate metadata relevance
            metadata = ctx.get('metadata', {})
            metadata_relevance = self._calculate_metadata_relevance(metadata, query)
            
            # Calculate source reliability
            source_reliability = self._calculate_source_reliability(ctx)
            
            # Calculate recency factor (for conversations)
            recency_factor = self._calculate_recency_factor(ctx)
            
            # Enhanced fusion formula
            enhanced_fusion_score = (
                scores['memory_score'] * 0.25 +
                scores['vector_score'] * 0.20 +
                scores['graph_score'] * 0.20 +
                scores['conversation_score'] * 0.10 +
                scores['fusion_score'] * 0.15 +
                content_relevance * 0.30 +
                metadata_relevance * 0.15 +
                source_reliability * 0.10 +
                recency_factor * 0.05
            )
            
            ctx['enhanced_fusion_score'] = enhanced_fusion_score
            ctx['scoring_breakdown'] = {
                'content_relevance': content_relevance,
                'metadata_relevance': metadata_relevance,
                'source_reliability': source_reliability,
                'recency_factor': recency_factor,
                'original_scores': scores
            }
            
        return contexts
        
    def _calculate_metadata_relevance(self, metadata: Dict[str, Any], query: str) -> float:
        """Calculate relevance based on metadata fields"""
        relevance = 0.0
        query_lower = query.lower()
        
        # Check capability relevance
        capability = metadata.get('capability', '').lower()
        if capability and capability in query_lower:
            relevance += 0.4
            
        # Check type relevance
        ctx_type = metadata.get('type', '').lower()
        if 'spec' in ctx_type and ('api' in query_lower or 'spec' in query_lower):
            relevance += 0.3
        elif 'prompt' in ctx_type and ('prompt' in query_lower or 'guide' in query_lower):
            relevance += 0.3
            
        # Check source relevance
        source = metadata.get('source', '').lower()
        if source:
            source_words = set(source.split('/'))
            query_words = set(query_lower.split())
            if source_words.intersection(query_words):
                relevance += 0.3
                
        return min(relevance, 1.0)
        
    def _calculate_source_reliability(self, ctx: Dict[str, Any]) -> float:
        """Calculate reliability based on context source"""
        source = ctx.get('context_source', '')
        
        reliability_scores = {
            'memory': 0.9,      # mem0 semantic memory is highly reliable
            'integrated': 0.8,   # Vector+graph integration is reliable
            'conversation': 0.6  # Conversation context is less reliable
        }
        
        return reliability_scores.get(source, 0.5)
        
    def _calculate_recency_factor(self, ctx: Dict[str, Any]) -> float:
        """Calculate recency factor for time-sensitive content"""
        # For now, give slight preference to conversation context
        if ctx.get('context_source') == 'conversation':
            return 0.8
        return 0.5
        
    async def store_enhanced_context(self, user_message: str, assistant_response: str,
                                   session_id: str, context_used: List[Dict[str, Any]]):
        """Store conversation with enhanced context tracking"""
        try:
            # Store in mem0 memory
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self.memory_manager.add_conversation,
                user_message,
                assistant_response,
                session_id,
                context_used
            )
            
            # Extract and store key concepts for future retrieval
            await self._extract_and_store_concepts(user_message, assistant_response, context_used)
            
        except Exception as e:
            logger.error(f"❌ Enhanced context storage error: {e}")
            
    async def _extract_and_store_concepts(self, user_message: str, assistant_response: str,
                                        context_used: List[Dict[str, Any]]):
        """Extract and store key concepts from the conversation"""
        try:
            # Extract key concepts from the conversation
            concepts = self._extract_key_concepts(user_message + " " + assistant_response)
            
            if concepts:
                # Store concept relationships in memory
                concept_content = f"Key concepts discussed: {', '.join(concepts)}"
                concept_metadata = {
                    "type": "concept_extraction",
                    "concepts": concepts,
                    "context_sources": [ctx.get('context_source', 'unknown') for ctx in context_used]
                }
                
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self.executor,
                    self.memory_manager._store_memory_item,
                    concept_content,
                    concept_metadata
                )
                
        except Exception as e:
            logger.error(f"❌ Concept extraction error: {e}")
            
    def _extract_key_concepts(self, text: str) -> List[str]:
        """Extract key concepts from text"""
        import re
        
        concepts = []
        text_lower = text.lower()
        
        # Technical concepts
        tech_concepts = [
            'ekyc', 'pan', 'aadhaar', 'otp', 'verification', 'validation',
            'api', 'rest', 'spring boot', 'postgresql', 'database',
            'authentication', 'authorization', 'microservice', 'swagger'
        ]
        
        for concept in tech_concepts:
            if concept in text_lower:
                concepts.append(concept.upper())
                
        # Extract acronyms
        acronyms = re.findall(r'\b[A-Z]{2,}\b', text)
        concepts.extend(acronyms)
        
        # Extract CamelCase terms
        camel_case = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', text)
        concepts.extend(camel_case)
        
        return list(set(concepts))
        
    async def get_context_analytics(self) -> Dict[str, Any]:
        """Get analytics about context usage and effectiveness"""
        try:
            memory_stats = self.memory_manager.get_memory_stats()
            
            # Get vector and graph stats if available
            vector_stats = {}
            graph_stats = {}
            
            try:
                vector_stats = self.vector_service.get_collection_info()
            except:
                pass
                
            try:
                graph_stats = await self.context_repository.get_graph_statistics()
            except:
                pass
                
            return {
                "memory_layer": memory_stats,
                "vector_layer": vector_stats,
                "graph_layer": graph_stats,
                "integration_status": {
                    "memory_available": memory_stats.get("status") == "active",
                    "vector_available": bool(vector_stats),
                    "graph_available": bool(graph_stats)
                },
                "total_context_sources": sum([
                    1 if memory_stats.get("status") == "active" else 0,
                    1 if vector_stats else 0,
                    1 if graph_stats else 0
                ])
            }
            
        except Exception as e:
            logger.error(f"❌ Context analytics error: {e}")
            return {"error": str(e)}
            
    async def optimize_context_retrieval(self, query_patterns: List[str]) -> Dict[str, Any]:
        """Optimize context retrieval based on query patterns"""
        try:
            optimization_results = {
                "analyzed_patterns": len(query_patterns),
                "recommendations": [],
                "performance_insights": {}
            }
            
            # Analyze query patterns
            pattern_analysis = self._analyze_query_patterns(query_patterns)
            
            # Generate optimization recommendations
            if pattern_analysis.get("common_capabilities"):
                optimization_results["recommendations"].append(
                    f"Consider pre-loading context for common capabilities: {', '.join(pattern_analysis['common_capabilities'])}"
                )
                
            if pattern_analysis.get("avg_query_length", 0) > 20:
                optimization_results["recommendations"].append(
                    "Queries are typically long - consider increasing context window size"
                )
                
            return optimization_results
            
        except Exception as e:
            logger.error(f"❌ Context optimization error: {e}")
            return {"error": str(e)}
            
    def _analyze_query_patterns(self, query_patterns: List[str]) -> Dict[str, Any]:
        """Analyze patterns in user queries"""
        analysis = {
            "total_queries": len(query_patterns),
            "avg_query_length": sum(len(q.split()) for q in query_patterns) / max(len(query_patterns), 1),
            "common_capabilities": [],
            "common_terms": []
        }
        
        # Find common capabilities
        capabilities = ['ekyc', 'pan', 'otp', 'verification', 'api']
        for cap in capabilities:
            count = sum(1 for q in query_patterns if cap.lower() in q.lower())
            if count > len(query_patterns) * 0.2:  # Appears in >20% of queries
                analysis["common_capabilities"].append(cap)
                
        return analysis