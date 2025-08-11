from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

from .neo4j_service import Neo4jService


class ContextRepository:
    """
    Repository for context-related graph database operations.
    
    This class handles all graph database interactions for:
    - Documents, capabilities, guidelines, business flows
    - Concepts and their relationships
    - Context retrieval and search operations
    """
    
    def __init__(self, neo4j_service: Neo4jService):
        self.neo4j = neo4j_service
        
    async def clear_all_context_data(self):
        """Clear all context data from the graph database"""
        await self.neo4j.clear_database()
        
    # Document operations
    async def create_document(self, document_data: Dict[str, Any]) -> str:
        """Create a document node"""
        document_data["id"] = str(uuid.uuid4())
        document_data["created_at"] = datetime.now().isoformat()
        
        return await self.neo4j.create_node("Document", document_data)
    
    async def create_dynamic_document(self, source_type: str, source_identifier: str, 
                                    content_metadata: Dict[str, Any]) -> str:
        """Create a dynamic document node for uploaded/processed content"""
        document_data = {
            "id": str(uuid.uuid4()),
            "source_type": source_type,  # 'upload', 'url', 'github'
            "source_identifier": source_identifier,
            "capability": "DYNAMIC",
            "type": "dynamic_content",
            "created_at": datetime.now().isoformat(),
            **content_metadata
        }
        
        return await self.neo4j.create_node("DynamicDocument", document_data)
        
    async def get_documents_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """Get all documents for a specific capability"""
        return await self.neo4j.find_nodes("Document", {"capability": capability})
        
    # Capability operations
    async def create_capability(self, capability_name: str) -> str:
        """Create a capability node"""
        capability_data = {
            "id": str(uuid.uuid4()),
            "name": capability_name,
            "created_at": datetime.now().isoformat()
        }
        
        return await self.neo4j.create_node("Capability", capability_data)
        
    async def link_capability_document(self, capability_id: str, document_id: str) -> bool:
        """Link a capability to a document"""
        return await self.neo4j.create_relationship(
            capability_id, document_id, "CONTAINS"
        )
        
    # Guideline operations
    async def create_guideline(self, guideline_data: Dict[str, Any]) -> str:
        """Create a guideline node"""
        guideline_data["id"] = str(uuid.uuid4())
        guideline_data["created_at"] = datetime.now().isoformat()
        
        return await self.neo4j.create_node("Guideline", guideline_data)
        
    # Business flow operations
    async def create_business_flow(self, flow_data: Dict[str, Any]) -> str:
        """Create a business flow node"""
        flow_data["id"] = str(uuid.uuid4())
        flow_data["created_at"] = datetime.now().isoformat()
        
        return await self.neo4j.create_node("BusinessFlow", flow_data)
        
    async def link_document_business_flow(self, document_id: str, flow_id: str) -> bool:
        """Link a document to a business flow"""
        return await self.neo4j.create_relationship(
            document_id, flow_id, "DESCRIBES"
        )
        
    # Concept operations
    async def create_or_merge_concept(self, concept_data: Dict[str, Any]) -> str:
        """Create or merge a concept node"""
        query = """
        MERGE (c:Concept {name: $name})
        ON CREATE SET 
            c.id = $id,
            c.type = $type,
            c.context = $context,
            c.keywords = $keywords,
            c.created_at = $created_at,
            c.relevance_score = 1.0
        ON MATCH SET 
            c.relevance_score = c.relevance_score + 0.1,
            c.updated_at = $created_at
        RETURN c.id as id
        """
        
        params = {
            "id": str(uuid.uuid4()),
            "name": concept_data["name"],
            "type": concept_data.get("type", "general"),
            "context": concept_data.get("context", ""),
            "keywords": concept_data.get("keywords", []),
            "created_at": datetime.now().isoformat()
        }
        
        result = await self.neo4j.execute_write_query(query, params)
        return result[0]["id"] if result else params["id"]
        
    async def link_document_concept(self, document_id: str, concept_name: str) -> bool:
        """Link a document to a concept"""
        query = """
        MATCH (d:Document {id: $document_id}), (c:Concept {name: $concept_name})
        CREATE (d)-[:MENTIONS]->(c)
        RETURN d, c
        """
        
        result = await self.neo4j.execute_write_query(query, {
            "document_id": document_id,
            "concept_name": concept_name
        })
        
        return len(result) > 0
        
    async def link_guideline_concept(self, guideline_id: str, concept_name: str) -> bool:
        """Link a guideline to a concept"""
        query = """
        MATCH (g:Guideline {id: $guideline_id}), (c:Concept {name: $concept_name})
        CREATE (g)-[:DEFINES]->(c)
        RETURN g, c
        """
        
        result = await self.neo4j.execute_write_query(query, {
            "guideline_id": guideline_id,
            "concept_name": concept_name
        })
        
        return len(result) > 0
        
    async def create_concept_relationships(self) -> int:
        """Create relationships between related concepts"""
        query = """
        MATCH (c1:Concept), (c2:Concept)
        WHERE c1.name <> c2.name
        AND (
            c1.context CONTAINS c2.name OR
            c2.context CONTAINS c1.name OR
            any(k1 IN c1.keywords WHERE any(k2 IN c2.keywords WHERE k1 = k2))
        )
        CREATE (c1)-[:RELATED_TO {strength: 0.5}]->(c2)
        RETURN count(*) as relationships_created
        """
        
        result = await self.neo4j.execute_write_query(query)
        return result[0]["relationships_created"] if result else 0
        
    # Search and retrieval operations
    async def find_matching_concepts(self, query_words: List[str]) -> List[Dict[str, Any]]:
        """Find concepts that match query words"""
        query = """
        MATCH (c:Concept)
        WHERE any(word IN $query_words WHERE c.name CONTAINS word)
        RETURN c.name as name, c.type as type, c.relevance_score as relevance_score,
               c.keywords as keywords, c.context as context
        ORDER BY c.relevance_score DESC
        LIMIT 10
        """
        
        return await self.neo4j.execute_query(query, {"query_words": query_words})
        
    async def get_content_for_concept(self, concept_name: str) -> List[Dict[str, Any]]:
        """Get all content (documents, guidelines) related to a concept"""
        query = """
        MATCH (c:Concept {name: $concept_name})
        OPTIONAL MATCH (d:Document)-[:MENTIONS]->(c)
        OPTIONAL MATCH (g:Guideline)-[:DEFINES]->(c)
        OPTIONAL MATCH (bf:BusinessFlow)<-[:DESCRIBES]-(d)
        
        WITH c, collect(DISTINCT {
            id: d.id,
            content: d.content,
            type: 'document',
            source_file: d.source_file,
            capability: d.capability,
            keywords: []
        }) as documents,
        collect(DISTINCT {
            id: g.id,
            content: g.content,
            type: 'guideline',
            source_file: g.source_file,
            capability: 'general',
            keywords: []
        }) as guidelines,
        collect(DISTINCT {
            id: bf.id,
            content: bf.description,
            type: 'business_flow',
            source_file: '',
            capability: bf.capability,
            keywords: []
        }) as flows
        
        RETURN documents + guidelines + flows as content_items
        """
        
        result = await self.neo4j.execute_query(query, {"concept_name": concept_name})
        
        if result and result[0]["content_items"]:
            # Filter out null items and add relevance scores
            content_items = []
            for item in result[0]["content_items"]:
                if item["id"]:  # Filter out null items
                    item["relevance_score"] = 0.8  # Base relevance for concept-related content
                    content_items.append(item)
            return content_items
            
        return []
        
    async def get_concepts_for_document(self, source_file: str) -> List[Dict[str, Any]]:
        """Get all concepts mentioned in a specific document"""
        query = """
        MATCH (d:Document {source_file: $source_file})-[:MENTIONS]->(c:Concept)
        RETURN c.name as name, c.type as type, c.relevance_score as relevance,
               c.keywords as keywords
        ORDER BY c.relevance_score DESC
        """
        
        return await self.neo4j.execute_query(query, {"source_file": source_file})
        
    async def perform_semantic_search(self, query: str, max_items: int) -> List[Dict[str, Any]]:
        """Perform semantic search on document content"""
        # This is a simplified text-based search
        # In a production system, you might want to use Neo4j's full-text search capabilities
        query_words = query.lower().split()
        
        search_query = """
        MATCH (d:Document)
        WHERE any(word IN $query_words WHERE toLower(d.content) CONTAINS word)
        RETURN d.id as id, d.content as content, d.type as type,
               d.source_file as source_file, d.capability as capability,
               [] as keywords,
               0.6 as relevance_score
        ORDER BY size(d.content) DESC
        LIMIT $max_items
        """
        
        return await self.neo4j.execute_query(search_query, {
            "query_words": query_words,
            "max_items": max_items
        })
        
    # Conversation storage
    async def store_conversation(self, conversation_data: Dict[str, Any], 
                               context_used: List[Dict[str, Any]]):
        """Store conversation and link to used context"""
        # Create conversation node
        conversation_data["id"] = str(uuid.uuid4())
        conversation_data["timestamp"] = datetime.now().isoformat()
        
        conv_id = await self.neo4j.create_node("Conversation", conversation_data)
        
        # Link to context items used
        for context_item in context_used:
            if "id" in context_item:
                await self.neo4j.create_relationship(
                    conv_id, context_item["id"], "USED_CONTEXT",
                    {"relevance": context_item.get("relevance_score", 0.5)}
                )
                
    # Statistics and analytics
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get comprehensive graph statistics"""
        stats = await self.neo4j.get_database_stats()
        
        # Add custom statistics
        custom_queries = {
            "top_concepts": """
                MATCH (c:Concept)
                RETURN c.name as concept, c.relevance_score as score
                ORDER BY c.relevance_score DESC
                LIMIT 5
            """,
            "capabilities_with_document_count": """
                MATCH (cap:Capability)-[:CONTAINS]->(d:Document)
                RETURN cap.name as capability, count(d) as document_count
                ORDER BY document_count DESC
            """,
            "most_mentioned_concepts": """
                MATCH (d:Document)-[:MENTIONS]->(c:Concept)
                RETURN c.name as concept, count(d) as mention_count
                ORDER BY mention_count DESC
                LIMIT 5
            """
        }
        
        for stat_name, query in custom_queries.items():
            try:
                result = await self.neo4j.execute_query(query)
                stats[stat_name] = result
            except Exception as e:
                print(f"⚠️ Error getting {stat_name}: {e}")
                stats[stat_name] = []
                
        return stats
        
    # Utility methods
    async def get_related_documents(self, document_id: str, max_items: int = 5) -> List[Dict[str, Any]]:
        """Get documents related to a given document through shared concepts"""
        query = """
        MATCH (d1:Document {id: $document_id})-[:MENTIONS]->(c:Concept)<-[:MENTIONS]-(d2:Document)
        WHERE d1.id <> d2.id
        WITH d2, count(c) as shared_concepts
        RETURN d2.id as id, d2.content as content, d2.type as type,
               d2.source_file as source_file, d2.capability as capability,
               [] as keywords,
               (shared_concepts * 0.2) as relevance_score
        ORDER BY shared_concepts DESC
        LIMIT $max_items
        """
        
        return await self.neo4j.execute_query(query, {
            "document_id": document_id,
            "max_items": max_items
        })
        
    async def get_capability_overview(self, capability_name: str) -> Dict[str, Any]:
        """Get comprehensive overview of a capability"""
        query = """
        MATCH (cap:Capability {name: $capability_name})
        OPTIONAL MATCH (cap)-[:CONTAINS]->(d:Document)
        OPTIONAL MATCH (d)-[:MENTIONS]->(c:Concept)
        OPTIONAL MATCH (d)-[:DESCRIBES]->(bf:BusinessFlow)
        
        RETURN cap.name as capability,
               count(DISTINCT d) as document_count,
               count(DISTINCT c) as concept_count,
               count(DISTINCT bf) as business_flow_count,
               collect(DISTINCT c.name)[0..5] as top_concepts
        """
        
        result = await self.neo4j.execute_query(query, {"capability_name": capability_name})
        return result[0] if result else {}   
 # Dynamic Content Operations
    async def store_dynamic_content(self, source_type: str, source_identifier: str, 
                                  chunks: List[Dict[str, Any]], 
                                  concepts: List[str]) -> Dict[str, Any]:
        """Store dynamic content and its concepts in the graph database"""
        try:
            # Create dynamic document node
            doc_id = await self.create_dynamic_document(
                source_type, source_identifier, 
                {
                    'chunks_count': len(chunks),
                    'concepts_count': len(concepts),
                    'content_preview': chunks[0]['content'][:200] if chunks else ''
                }
            )
            
            # Create or link concepts
            concept_ids = []
            for concept in concepts:
                concept_id = await self.create_dynamic_concept(concept, source_type)
                concept_ids.append(concept_id)
                
                # Link document to concept
                await self.neo4j.create_relationship(
                    doc_id, concept_id, "MENTIONS", 
                    {"confidence": 0.8, "source_type": source_type}
                )
            
            # Store chunk information as properties
            for i, chunk in enumerate(chunks[:5]):  # Store first 5 chunks
                chunk_data = {
                    'chunk_index': i,
                    'content_preview': chunk['content'][:100],
                    'chunk_id': chunk.get('chunk_id', f'chunk_{i}')
                }
                
                await self.neo4j.create_relationship(
                    doc_id, doc_id, "HAS_CHUNK", chunk_data
                )
            
            return {
                'document_id': doc_id,
                'concepts_created': len(concept_ids),
                'chunks_stored': len(chunks),
                'source_type': source_type
            }
            
        except Exception as e:
            print(f"❌ Error storing dynamic content in graph: {e}")
            return {}
    
    async def create_dynamic_concept(self, concept_name: str, source_type: str) -> str:
        """Create or update a dynamic concept"""
        # Check if concept already exists
        existing = await self.neo4j.find_nodes("Concept", {"name": concept_name})
        
        if existing:
            # Update existing concept with dynamic source info
            concept_id = existing[0]["id"]
            await self.neo4j.update_node_properties(concept_id, {
                "dynamic_sources": f"{existing[0].get('dynamic_sources', '')},{source_type}",
                "last_updated": datetime.now().isoformat()
            })
            return concept_id
        else:
            # Create new dynamic concept
            concept_data = {
                "id": str(uuid.uuid4()),
                "name": concept_name,
                "type": "dynamic",
                "source_type": source_type,
                "dynamic_sources": source_type,
                "relevance_score": 0.7,
                "created_at": datetime.now().isoformat()
            }
            
            return await self.neo4j.create_node("Concept", concept_data)
    
    async def get_dynamic_content_by_source(self, source_type: str) -> List[Dict[str, Any]]:
        """Get all dynamic content by source type"""
        query = """
        MATCH (dd:DynamicDocument {source_type: $source_type})
        OPTIONAL MATCH (dd)-[:MENTIONS]->(c:Concept)
        
        RETURN dd.id as id,
               dd.source_identifier as source_identifier,
               dd.created_at as created_at,
               dd.chunks_count as chunks_count,
               collect(c.name) as concepts
        ORDER BY dd.created_at DESC
        """
        
        return await self.neo4j.execute_query(query, {"source_type": source_type})
    
    async def search_dynamic_content(self, query: str, source_types: List[str] = None) -> List[Dict[str, Any]]:
        """Search dynamic content across all or specific source types"""
        query_words = query.upper().split()
        
        # Build the query dynamically based on parameters
        if source_types and query_words:
            search_query = """
            MATCH (dd:DynamicDocument)
            WHERE dd.source_type IN $source_types
            OPTIONAL MATCH (dd)-[:MENTIONS]->(c:Concept)
            WHERE any(word IN $query_words WHERE c.name CONTAINS word)
            
            RETURN DISTINCT dd.id as id,
                   dd.source_type as source_type,
                   dd.source_identifier as source_identifier,
                   dd.content_preview as content_preview,
                   dd.created_at as created_at,
                   collect(c.name) as matching_concepts
            ORDER BY dd.created_at DESC
            LIMIT 10
            """
        elif source_types:
            search_query = """
            MATCH (dd:DynamicDocument)
            WHERE dd.source_type IN $source_types
            OPTIONAL MATCH (dd)-[:MENTIONS]->(c:Concept)
            
            RETURN DISTINCT dd.id as id,
                   dd.source_type as source_type,
                   dd.source_identifier as source_identifier,
                   dd.content_preview as content_preview,
                   dd.created_at as created_at,
                   collect(c.name) as matching_concepts
            ORDER BY dd.created_at DESC
            LIMIT 10
            """
        elif query_words:
            search_query = """
            MATCH (dd:DynamicDocument)
            OPTIONAL MATCH (dd)-[:MENTIONS]->(c:Concept)
            WHERE any(word IN $query_words WHERE c.name CONTAINS word)
            
            RETURN DISTINCT dd.id as id,
                   dd.source_type as source_type,
                   dd.source_identifier as source_identifier,
                   dd.content_preview as content_preview,
                   dd.created_at as created_at,
                   collect(c.name) as matching_concepts
            ORDER BY dd.created_at DESC
            LIMIT 10
            """
        else:
            search_query = """
            MATCH (dd:DynamicDocument)
            OPTIONAL MATCH (dd)-[:MENTIONS]->(c:Concept)
            
            RETURN DISTINCT dd.id as id,
                   dd.source_type as source_type,
                   dd.source_identifier as source_identifier,
                   dd.content_preview as content_preview,
                   dd.created_at as created_at,
                   collect(c.name) as matching_concepts
            ORDER BY dd.created_at DESC
            LIMIT 10
            """
        
        params = {"query_words": query_words}
        if source_types:
            params["source_types"] = source_types
            
        return await self.neo4j.execute_query(search_query, params)
    
    async def get_dynamic_content_stats(self) -> Dict[str, Any]:
        """Get statistics about dynamic content in the graph"""
        query = """
        MATCH (dd:DynamicDocument)
        OPTIONAL MATCH (dd)-[:MENTIONS]->(c:Concept)
        
        RETURN count(DISTINCT dd) as total_documents,
               count(DISTINCT c) as total_concepts,
               collect(DISTINCT dd.source_type) as source_types,
               avg(dd.chunks_count) as avg_chunks_per_document
        """
        
        result = await self.neo4j.execute_query(query)
        return result[0] if result else {}
    
    async def link_dynamic_to_static_content(self, dynamic_doc_id: str, 
                                           static_concepts: List[str]) -> int:
        """Link dynamic content to existing static concepts"""
        links_created = 0
        
        for concept_name in static_concepts:
            # Find existing static concept
            static_concepts = await self.neo4j.find_nodes("Concept", {
                "name": concept_name,
                "type": {"$ne": "dynamic"}
            })
            
            if static_concepts:
                static_concept_id = static_concepts[0]["id"]
                
                # Create relationship between dynamic document and static concept
                success = await self.neo4j.create_relationship(
                    dynamic_doc_id, static_concept_id, "RELATES_TO",
                    {"relationship_type": "dynamic_to_static", "confidence": 0.6}
                )
                
                if success:
                    links_created += 1
        
        return links_created