from typing import List, Dict, Any
import asyncio
from collections import defaultdict

from vector.vector_service import VectorService
from graph.context_repository import ContextRepository


class IntegrationService:
    """
    Integration service that combines vector search and graph database queries
    to provide enhanced context retrieval.
    
    Processing Flow:
    1. Parallel execution of vector search and graph concept matching
    2. Cross-reference and enrich results using graph relationships
    3. Fusion scoring combining vector similarity and graph relevance
    4. Ranked context items for LLM consumption
    """
    
    def __init__(self, vector_service: VectorService, context_repository: ContextRepository):
        self.vector_service = vector_service
        self.context_repository = context_repository
        
        # Scoring weights for fusion
        self.vector_weight = 0.6
        self.graph_weight = 0.4
        
    async def get_integrated_context(self, query: str, max_items: int = 5, 
                                   include_dynamic: bool = True) -> List[Dict[str, Any]]:
        """
        Get integrated context using both vector search and graph traversal.
        
        Args:
            query: User's search query
            max_items: Maximum number of context items to return
            include_dynamic: Whether to include dynamic content in results
            
        Returns:
            List of enriched context items with fusion scores
        """
        print(f"🔍 Starting integrated search for: '{query}' (dynamic: {include_dynamic})")
        
        # Step 1: Parallel execution of vector and graph searches
        search_tasks = [
            self._get_vector_context(query, max_items * 2),
            self._get_graph_concepts(query)
        ]
        
        # Add dynamic content search if requested
        if include_dynamic:
            search_tasks.append(self._get_dynamic_vector_context(query, max_items))
            search_tasks.append(self._get_dynamic_graph_context(query))
        
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        vector_results = results[0] if not isinstance(results[0], Exception) else []
        graph_concepts = results[1] if not isinstance(results[1], Exception) else []
        
        dynamic_vector_results = []
        dynamic_graph_results = []
        
        if include_dynamic and len(results) > 2:
            dynamic_vector_results = results[2] if not isinstance(results[2], Exception) else []
            dynamic_graph_results = results[3] if not isinstance(results[3], Exception) else []
        
        # Handle exceptions
        if isinstance(vector_results, Exception):
            print(f"⚠️ Vector search failed: {vector_results}")
            vector_results = []
        if isinstance(graph_concepts, Exception):
            print(f"⚠️ Graph search failed: {graph_concepts}")
            graph_concepts = []
            
        # Combine static and dynamic results
        all_vector_results = vector_results + dynamic_vector_results
        all_graph_concepts = graph_concepts  # Dynamic graph results are handled separately
        
        print(f"📊 Vector results: {len(vector_results)} static + {len(dynamic_vector_results)} dynamic, Graph concepts: {len(graph_concepts)}")
        
        # Step 2: Enrich vector results with graph relationships
        enriched_items = await self._enrich_with_graph_relationships(
            all_vector_results, all_graph_concepts, query
        )
        
        # Step 2.5: Add dynamic graph results as separate items
        for dynamic_result in dynamic_graph_results:
            dynamic_result['fusion_score'] = dynamic_result['graph_score'] * self.graph_weight
            enriched_items.append(dynamic_result)
        
        # Step 3: Get additional graph-only content for concepts not covered by vector search
        additional_graph_content = await self._get_additional_graph_content(
            graph_concepts, enriched_items, max_items
        )
        
        # Step 4: Combine and rank all results
        all_items = enriched_items + additional_graph_content
        ranked_items = self._rank_integrated_results(all_items, query)
        
        print(f"✅ Returning {len(ranked_items[:max_items])} integrated context items")
        return ranked_items[:max_items]
        
    async def _get_vector_context(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Get context from vector search"""
        try:
            results = await self.vector_service.search(query, n_results=max_results)
            
            # Normalize vector results to standard format
            normalized_results = []
            for result in results:
                normalized_results.append({
                    'id': f"vector_{result['metadata']['source']}_{result['metadata']['chunk_id']}",
                    'content': result['content'],
                    'type': 'document_chunk',
                    'source_file': result['metadata']['source'],
                    'vector_score': 1.0 - result['distance'],  # Convert distance to similarity
                    'graph_score': 0.0,
                    'fusion_score': 0.0,
                    'metadata': result['metadata'],
                    'keywords': self._extract_keywords_from_content(result['content'])
                })
                
            return normalized_results
            
        except Exception as e:
            print(f"❌ Vector search error: {e}")
            return []
            
    async def _get_graph_concepts(self, query: str) -> List[Dict[str, Any]]:
        """Get matching concepts from graph database"""
        try:
            query_words = query.upper().split()
            concepts = await self.context_repository.find_matching_concepts(query_words)
            return concepts
            
        except Exception as e:
            print(f"❌ Graph concept search error: {e}")
            return []
            
    async def _enrich_with_graph_relationships(self, vector_results: List[Dict[str, Any]], 
                                             graph_concepts: List[Dict[str, Any]], 
                                             query: str) -> List[Dict[str, Any]]:
        """Enrich vector results with graph relationship information"""
        enriched_items = []
        
        for vector_item in vector_results:
            # Start with the vector item
            enriched_item = vector_item.copy()
            
            # Find related graph concepts for this document
            related_concepts = await self._find_related_concepts_for_document(
                vector_item['source_file'], graph_concepts
            )
            
            # Calculate graph score based on concept matches and relationships
            graph_score = self._calculate_graph_score(related_concepts, query)
            enriched_item['graph_score'] = graph_score
            
            # Add related concepts information
            enriched_item['related_concepts'] = [c['name'] for c in related_concepts[:3]]
            
            # Calculate fusion score
            enriched_item['fusion_score'] = (
                self.vector_weight * enriched_item['vector_score'] +
                self.graph_weight * enriched_item['graph_score']
            )
            
            enriched_items.append(enriched_item)
            
        return enriched_items
        
    async def _find_related_concepts_for_document(self, source_file: str, 
                                                graph_concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find graph concepts related to a specific document"""
        try:
            # Get concepts mentioned in this document
            document_concepts = await self.context_repository.get_concepts_for_document(source_file)
            
            # Find intersection with query-matched concepts
            related_concepts = []
            for doc_concept in document_concepts:
                for graph_concept in graph_concepts:
                    if doc_concept['name'] == graph_concept['name']:
                        related_concepts.append({
                            **graph_concept,
                            'document_relevance': doc_concept.get('relevance', 1.0)
                        })
                        
            return related_concepts
            
        except Exception as e:
            print(f"⚠️ Error finding related concepts: {e}")
            return []
            
    async def _get_additional_graph_content(self, graph_concepts: List[Dict[str, Any]], 
                                          existing_items: List[Dict[str, Any]], 
                                          max_additional: int) -> List[Dict[str, Any]]:
        """Get additional content from graph for concepts not covered by vector search"""
        additional_items = []
        existing_sources = {item['source_file'] for item in existing_items}
        
        for concept in graph_concepts[:max_additional]:
            try:
                # Get content for this concept that wasn't already retrieved
                concept_content = await self.context_repository.get_content_for_concept(concept['name'])
                
                for content_item in concept_content:
                    if content_item['source_file'] not in existing_sources:
                        additional_items.append({
                            'id': f"graph_{content_item['id']}",
                            'content': content_item['content'],
                            'type': content_item['type'],
                            'source_file': content_item['source_file'],
                            'vector_score': 0.0,
                            'graph_score': concept.get('relevance_score', 0.8),
                            'fusion_score': self.graph_weight * concept.get('relevance_score', 0.8),
                            'related_concepts': [concept['name']],
                            'keywords': content_item.get('keywords', [])
                        })
                        existing_sources.add(content_item['source_file'])
                        
                        if len(additional_items) >= max_additional:
                            break
                            
            except Exception as e:
                print(f"⚠️ Error getting content for concept {concept['name']}: {e}")
                continue
                
        return additional_items
        
    def _calculate_graph_score(self, related_concepts: List[Dict[str, Any]], query: str) -> float:
        """Calculate graph relevance score based on concept matches and relationships"""
        if not related_concepts:
            return 0.0
            
        # Base score from concept matches
        base_score = min(len(related_concepts) * 0.3, 1.0)
        
        # Boost score based on concept relevance (handle None values)
        relevance_scores = [c.get('relevance_score', 0.5) or 0.5 for c in related_concepts]
        relevance_boost = sum(relevance_scores) / len(related_concepts) if relevance_scores else 0.5
        
        # Boost for exact query term matches in concept names
        query_terms = query.upper().split()
        exact_matches = sum(1 for c in related_concepts if c.get('name', '') in query_terms)
        exact_match_boost = min(exact_matches * 0.2, 0.4)
        
        return min(base_score + relevance_boost * 0.3 + exact_match_boost, 1.0)
        
    def _rank_integrated_results(self, items: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Rank integrated results by fusion score with additional relevance factors"""
        
        # Add query-specific relevance boosts
        query_lower = query.lower()
        for item in items:
            # Boost for query terms in content
            content_lower = item['content'].lower()
            query_term_matches = sum(1 for term in query_lower.split() if term in content_lower)
            query_boost = min(query_term_matches * 0.1, 0.3)
            
            # Boost for capability-specific content
            capability_boost = 0.1 if any(cap in item.get('source_file', '') 
                                        for cap in ['EKYC', 'PANNSDL', 'Capabilities']) else 0.0
            
            # Update fusion score with boosts
            item['fusion_score'] += query_boost + capability_boost
            
        # Sort by fusion score (descending) and remove duplicates
        seen_content = set()
        unique_items = []
        
        for item in sorted(items, key=lambda x: x['fusion_score'], reverse=True):
            content_hash = hash(item['content'][:200])  # Use first 200 chars as hash
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_items.append(item)
                
        return unique_items
        
    def _extract_keywords_from_content(self, content: str) -> List[str]:
        """Extract keywords from content for better matching"""
        import re
        
        # Extract technical terms, acronyms, and important words
        keywords = []
        
        # Acronyms (2+ uppercase letters)
        acronyms = re.findall(r'\b[A-Z]{2,}\b', content)
        keywords.extend(acronyms)
        
        # Technical terms
        tech_terms = re.findall(r'\b(?:API|Service|Controller|Repository|Entity|Phase|Step|Validation|Request|Response)\b', content, re.IGNORECASE)
        keywords.extend([term.upper() for term in tech_terms])
        
        # Remove duplicates and limit
        return list(set(keywords))[:10]
        
    async def get_integration_statistics(self) -> Dict[str, Any]:
        """Get statistics about the integration performance"""
        try:
            vector_stats = self.vector_service.get_collection_info()
            graph_stats = await self.context_repository.get_graph_statistics()
            
            return {
                "vector_store": vector_stats,
                "graph_database": graph_stats,
                "integration_config": {
                    "vector_weight": self.vector_weight,
                    "graph_weight": self.graph_weight,
                    "fusion_enabled": True
                }
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_dynamic_vector_context(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Get dynamic content from vector search"""
        try:
            results = await self.vector_service.search_dynamic_content(query, n_results=max_results)
            
            # Normalize dynamic vector results
            normalized_results = []
            for result in results:
                normalized_results.append({
                    'id': f"dynamic_vector_{result['metadata']['source']}_{result['metadata']['chunk_id']}",
                    'content': result['content'],
                    'type': 'dynamic_content',
                    'source_file': result['metadata']['source'],
                    'vector_score': result['similarity'],
                    'graph_score': 0.0,
                    'fusion_score': 0.0,
                    'metadata': result['metadata'],
                    'keywords': self._extract_keywords_from_content(result['content']),
                    'is_dynamic': True,
                    'source_type': result['metadata'].get('source_type', 'unknown')
                })
                
            return normalized_results
            
        except Exception as e:
            print(f"❌ Dynamic vector search error: {e}")
            return []
    
    async def _get_dynamic_graph_context(self, query: str) -> List[Dict[str, Any]]:
        """Get dynamic content from graph database"""
        try:
            # Search for dynamic content in graph
            dynamic_content = await self.context_repository.search_dynamic_content(query)
            
            # Normalize dynamic graph results
            normalized_results = []
            for content in dynamic_content:
                normalized_results.append({
                    'id': f"dynamic_graph_{content['id']}",
                    'content': content.get('content_preview', ''),
                    'type': 'dynamic_graph_content',
                    'source_file': content['source_identifier'],
                    'vector_score': 0.0,
                    'graph_score': 0.8,  # High graph score for direct matches
                    'fusion_score': 0.0,
                    'metadata': {
                        'source_type': content['source_type'],
                        'created_at': content['created_at'],
                        'matching_concepts': content.get('matching_concepts', [])
                    },
                    'keywords': content.get('matching_concepts', []),
                    'is_dynamic': True,
                    'source_type': content['source_type']
                })
                
            return normalized_results
            
        except Exception as e:
            print(f"❌ Dynamic graph search error: {e}")
            return []
    
    async def get_dynamic_content_overview(self) -> Dict[str, Any]:
        """Get overview of all dynamic content in the system"""
        try:
            # Get stats from both vector and graph stores
            vector_stats = await self.vector_service.get_dynamic_content_stats()
            graph_stats = await self.context_repository.get_dynamic_content_stats()
            
            return {
                "vector_store": vector_stats,
                "graph_database": graph_stats,
                "integration_summary": {
                    "total_dynamic_chunks": vector_stats.get('total_dynamic_chunks', 0),
                    "total_dynamic_documents": graph_stats.get('total_documents', 0),
                    "source_types_vector": list(vector_stats.get('source_types', {}).keys()),
                    "source_types_graph": graph_stats.get('source_types', []),
                    "content_types": list(vector_stats.get('content_types', {}).keys())
                }
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def search_dynamic_content_only(self, query: str, source_types: List[str] = None, 
                                        max_items: int = 5) -> List[Dict[str, Any]]:
        """Search only dynamic content across vector and graph stores"""
        try:
            # Search both stores for dynamic content
            vector_results, graph_results = await asyncio.gather(
                self.vector_service.search_dynamic_content(query, source_types, max_items),
                self.context_repository.search_dynamic_content(query, source_types),
                return_exceptions=True
            )
            
            if isinstance(vector_results, Exception):
                vector_results = []
            if isinstance(graph_results, Exception):
                graph_results = []
            
            # Combine and normalize results
            all_results = []
            
            # Add vector results
            for result in vector_results:
                all_results.append({
                    'content': result['content'],
                    'source': result['metadata']['source'],
                    'source_type': result['metadata'].get('source_type', 'unknown'),
                    'similarity': result['similarity'],
                    'type': 'vector_dynamic',
                    'metadata': result['metadata']
                })
            
            # Add graph results
            for result in graph_results:
                all_results.append({
                    'content': result.get('content_preview', ''),
                    'source': result['source_identifier'],
                    'source_type': result['source_type'],
                    'similarity': 0.8,  # Base similarity for graph matches
                    'type': 'graph_dynamic',
                    'metadata': {
                        'created_at': result['created_at'],
                        'concepts': result.get('matching_concepts', [])
                    }
                })
            
            # Sort by similarity and return top results
            all_results.sort(key=lambda x: x['similarity'], reverse=True)
            return all_results[:max_items]
            
        except Exception as e:
            print(f"❌ Dynamic content search error: {e}")
            return []