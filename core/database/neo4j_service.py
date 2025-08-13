import os
from neo4j import AsyncGraphDatabase
from typing import Dict, List, Any, Optional
import asyncio


class Neo4jService:
    """
    Neo4j database service for graph operations.
    
    Handles connection management, basic CRUD operations,
    and database initialization.
    """
    
    def __init__(self):
        self.driver = None
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")
        
    async def initialize(self):
        """Initialize Neo4j connection and create constraints"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri, 
                auth=(self.username, self.password)
            )
            
            # Test connection
            await self.test_connection()
            
            # Create database constraints and indexes
            await self._create_constraints()
            
            print("✅ Neo4j service initialized successfully")
            
        except Exception as e:
            print(f"❌ Neo4j initialization failed: {e}")
            raise
            
    async def close(self):
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()
            print("✅ Neo4j connection closed")
            
    async def test_connection(self) -> bool:
        """Test Neo4j connection"""
        try:
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 as test")
                record = await result.single()
                return record["test"] == 1
        except Exception as e:
            print(f"❌ Neo4j connection test failed: {e}")
            return False
            
    async def _create_constraints(self):
        """Create database constraints and indexes"""
        constraints = [
            # Unique constraints
            "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT capability_id_unique IF NOT EXISTS FOR (c:Capability) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT guideline_id_unique IF NOT EXISTS FOR (g:Guideline) REQUIRE g.id IS UNIQUE",
            "CREATE CONSTRAINT business_flow_id_unique IF NOT EXISTS FOR (bf:BusinessFlow) REQUIRE bf.id IS UNIQUE",
            "CREATE CONSTRAINT concept_name_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT conversation_id_unique IF NOT EXISTS FOR (conv:Conversation) REQUIRE conv.id IS UNIQUE",
            
            # Indexes for performance
            "CREATE INDEX document_content_index IF NOT EXISTS FOR (d:Document) ON (d.content)",
            "CREATE INDEX concept_keywords_index IF NOT EXISTS FOR (c:Concept) ON (c.keywords)",
            "CREATE INDEX guideline_type_index IF NOT EXISTS FOR (g:Guideline) ON (g.type)",
            "CREATE INDEX business_flow_order_index IF NOT EXISTS FOR (bf:BusinessFlow) ON (bf.order)",
        ]
        
        async with self.driver.session() as session:
            for constraint in constraints:
                try:
                    await session.run(constraint)
                except Exception as e:
                    # Constraint might already exist
                    if "already exists" not in str(e).lower():
                        print(f"⚠️ Constraint creation warning: {e}")
                        
    async def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            List of result records as dictionaries
        """
        if not self.driver:
            raise RuntimeError("Neo4j service not initialized")
            
        async with self.driver.session() as session:
            try:
                result = await session.run(query, parameters or {})
                records = []
                async for record in result:
                    records.append(dict(record))
                return records
            except Exception as e:
                print(f"❌ Query execution error: {e}")
                print(f"Query: {query}")
                print(f"Parameters: {parameters}")
                raise
                
    async def execute_write_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Execute a write query (CREATE, UPDATE, DELETE).
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            List of result records as dictionaries
        """
        if not self.driver:
            raise RuntimeError("Neo4j service not initialized")
            
        async with self.driver.session() as session:
            try:
                result = await session.run(query, parameters or {})
                records = []
                async for record in result:
                    records.append(dict(record))
                return records
            except Exception as e:
                print(f"❌ Write query execution error: {e}")
                print(f"Query: {query}")
                print(f"Parameters: {parameters}")
                raise
                
    async def clear_database(self):
        """Clear all data from the database (use with caution)"""
        query = "MATCH (n) DETACH DELETE n"
        await self.execute_write_query(query)
        print("🗑️ Database cleared")
        
    async def get_node_count(self, label: str = None) -> int:
        """
        Get count of nodes, optionally filtered by label.
        
        Args:
            label: Optional node label to filter by
            
        Returns:
            Number of nodes
        """
        if label:
            query = f"MATCH (n:{label}) RETURN count(n) as count"
        else:
            query = "MATCH (n) RETURN count(n) as count"
            
        result = await self.execute_query(query)
        return result[0]["count"] if result else 0
        
    async def get_relationship_count(self, rel_type: str = None) -> int:
        """
        Get count of relationships, optionally filtered by type.
        
        Args:
            rel_type: Optional relationship type to filter by
            
        Returns:
            Number of relationships
        """
        if rel_type:
            query = f"MATCH ()-[r:{rel_type}]-() RETURN count(r) as count"
        else:
            query = "MATCH ()-[r]-() RETURN count(r) as count"
            
        result = await self.execute_query(query)
        return result[0]["count"] if result else 0
        
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        stats = {}
        
        # Node counts by label
        node_labels = ["Document", "Capability", "Guideline", "BusinessFlow", "Concept", "Conversation"]
        for label in node_labels:
            stats[f"{label.lower()}_count"] = await self.get_node_count(label)
            
        # Relationship counts by type
        rel_types = ["CONTAINS", "DESCRIBES", "MENTIONS", "DEFINES", "RELATED_TO", "USED_CONTEXT"]
        for rel_type in rel_types:
            stats[f"{rel_type.lower()}_relationships"] = await self.get_relationship_count(rel_type)
            
        # Total counts
        stats["total_nodes"] = await self.get_node_count()
        stats["total_relationships"] = await self.get_relationship_count()
        
        return stats
        
    async def create_node(self, label: str, properties: Dict[str, Any]) -> str:
        """
        Create a node with given label and properties.
        
        Args:
            label: Node label
            properties: Node properties
            
        Returns:
            Created node ID
        """
        # Generate ID if not provided
        if "id" not in properties:
            import uuid
            properties["id"] = str(uuid.uuid4())
            
        # Build property string for query
        prop_items = []
        for key, value in properties.items():
            if isinstance(value, str):
                prop_items.append(f"{key}: ${key}")
            else:
                prop_items.append(f"{key}: ${key}")
                
        prop_string = "{" + ", ".join(prop_items) + "}"
        
        query = f"CREATE (n:{label} {prop_string}) RETURN n.id as id"
        result = await self.execute_write_query(query, properties)
        
        return result[0]["id"] if result else properties["id"]
        
    async def create_relationship(self, from_id: str, to_id: str, rel_type: str, 
                                properties: Dict[str, Any] = None) -> bool:
        """
        Create a relationship between two nodes.
        
        Args:
            from_id: Source node ID
            to_id: Target node ID
            rel_type: Relationship type
            properties: Optional relationship properties
            
        Returns:
            True if relationship was created
        """
        prop_string = ""
        params = {"from_id": from_id, "to_id": to_id}
        
        if properties:
            prop_items = []
            for key, value in properties.items():
                prop_items.append(f"{key}: ${key}")
                params[key] = value
            prop_string = "{" + ", ".join(prop_items) + "}"
            
        query = f"""
        MATCH (a), (b)
        WHERE a.id = $from_id AND b.id = $to_id
        CREATE (a)-[r:{rel_type} {prop_string}]->(b)
        RETURN r
        """
        
        result = await self.execute_write_query(query, params)
        return len(result) > 0
        
    async def find_nodes(self, label: str, properties: Dict[str, Any] = None, 
                        limit: int = None) -> List[Dict[str, Any]]:
        """
        Find nodes by label and optional properties.
        
        Args:
            label: Node label
            properties: Optional property filters
            limit: Optional result limit
            
        Returns:
            List of matching nodes
        """
        where_clauses = []
        params = {}
        
        if properties:
            for key, value in properties.items():
                where_clauses.append(f"n.{key} = ${key}")
                params[key] = value
                
        where_string = " AND ".join(where_clauses)
        if where_string:
            where_string = "WHERE " + where_string
            
        limit_string = f"LIMIT {limit}" if limit else ""
        
        query = f"MATCH (n:{label}) {where_string} RETURN n {limit_string}"
        
        result = await self.execute_query(query, params)
        return [record["n"] for record in result]
        
    async def update_node(self, node_id: str, properties: Dict[str, Any]) -> bool:
        """
        Update node properties.
        
        Args:
            node_id: Node ID to update
            properties: Properties to update
            
        Returns:
            True if node was updated
        """
        set_clauses = []
        params = {"node_id": node_id}
        
        for key, value in properties.items():
            set_clauses.append(f"n.{key} = ${key}")
            params[key] = value
            
        set_string = ", ".join(set_clauses)
        
        query = f"""
        MATCH (n)
        WHERE n.id = $node_id
        SET {set_string}
        RETURN n
        """
        
        result = await self.execute_write_query(query, params)
        return len(result) > 0
    
    async def update_node_properties(self, node_id: str, properties: Dict[str, Any]) -> bool:
        """
        Update node properties (alias for update_node).
        
        Args:
            node_id: Node ID to update
            properties: Properties to update
            
        Returns:
            True if node was updated
        """
        return await self.update_node(node_id, properties)