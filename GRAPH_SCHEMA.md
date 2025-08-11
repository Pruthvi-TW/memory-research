# Neo4j Graph Database Schema

## Overview

The graph database uses Neo4j to store and manage relationships between documents, concepts, capabilities, guidelines, business flows, and conversations. It supports both static content (from the lending directory) and dynamic content (uploaded files, URLs, GitHub repositories).

## Node Types

### 1. **Document** 📄
Static documents from the lending context directory.

**Properties:**
- `id` (string, unique): UUID identifier
- `content` (string): Document content
- `source_file` (string): Path to source file
- `capability` (string): Associated capability (e.g., "EKYC", "PANNSDL")
- `type` (string): Document type
- `created_at` (string): ISO timestamp

**Constraints:**
- `document_id_unique`: Unique constraint on `id`

**Indexes:**
- `document_content_index`: Index on `content` for text search

### 2. **DynamicDocument** 🔄
Documents from dynamic content sources (uploads, URLs, GitHub).

**Properties:**
- `id` (string, unique): UUID identifier
- `source_type` (string): Source type ("upload", "url", "github")
- `source_identifier` (string): Original source identifier
- `capability` (string): Always "DYNAMIC"
- `type` (string): Always "dynamic_content"
- `chunks_count` (integer): Number of content chunks
- `concepts_count` (integer): Number of extracted concepts
- `content_preview` (string): Preview of content (first 200 chars)
- `created_at` (string): ISO timestamp
- Additional metadata from content processing

### 3. **Capability** 🎯
Business capabilities or functional areas.

**Properties:**
- `id` (string, unique): UUID identifier
- `name` (string): Capability name (e.g., "EKYC", "PANNSDL")
- `created_at` (string): ISO timestamp

**Constraints:**
- `capability_id_unique`: Unique constraint on `id`

### 4. **Concept** 💡
Key concepts, terms, and entities extracted from content.

**Properties:**
- `id` (string): UUID identifier
- `name` (string, unique): Concept name
- `type` (string): Concept type ("general", "dynamic", etc.)
- `relevance_score` (float): Relevance score (0.0-1.0)
- `context` (string): Contextual information
- `keywords` (array): Related keywords
- `dynamic_sources` (string): Comma-separated dynamic source types
- `last_updated` (string): ISO timestamp of last update
- `created_at` (string): ISO timestamp

**Constraints:**
- `concept_name_unique`: Unique constraint on `name`

**Indexes:**
- `concept_keywords_index`: Index on `keywords`

### 5. **Guideline** 📋
Guidelines and rules from the lending context.

**Properties:**
- `id` (string, unique): UUID identifier
- `content` (string): Guideline content
- `type` (string): Guideline type
- `source_file` (string): Source file path
- `created_at` (string): ISO timestamp

**Constraints:**
- `guideline_id_unique`: Unique constraint on `id`

**Indexes:**
- `guideline_type_index`: Index on `type`

### 6. **BusinessFlow** 🔄
Business process flows and workflows.

**Properties:**
- `id` (string, unique): UUID identifier
- `name` (string): Flow name
- `description` (string): Flow description
- `capability` (string): Associated capability
- `order` (integer): Step order in process
- `created_at` (string): ISO timestamp

**Constraints:**
- `business_flow_id_unique`: Unique constraint on `id`

**Indexes:**
- `business_flow_order_index`: Index on `order`

### 7. **Conversation** 💬
Chat conversations and their context.

**Properties:**
- `id` (string, unique): UUID identifier
- `user_message` (string): User's message
- `bot_response` (string): Bot's response
- `session_id` (string): Session identifier
- `timestamp` (string): ISO timestamp

**Constraints:**
- `conversation_id_unique`: Unique constraint on `id`

## Relationship Types

### 1. **CONTAINS** 📦
Links capabilities to their documents.
- **From:** Capability
- **To:** Document
- **Properties:** None
- **Usage:** `(Capability)-[:CONTAINS]->(Document)`

### 2. **MENTIONS** 🏷️
Links documents to concepts they mention.
- **From:** Document, DynamicDocument
- **To:** Concept
- **Properties:** 
  - `confidence` (float): Confidence score (0.0-1.0)
  - `source_type` (string): For dynamic content
- **Usage:** `(Document)-[:MENTIONS]->(Concept)`

### 3. **DEFINES** 📖
Links guidelines to concepts they define.
- **From:** Guideline
- **To:** Concept
- **Properties:** None
- **Usage:** `(Guideline)-[:DEFINES]->(Concept)`

### 4. **DESCRIBES** 📝
Links documents to business flows they describe.
- **From:** Document
- **To:** BusinessFlow
- **Properties:** None
- **Usage:** `(Document)-[:DESCRIBES]->(BusinessFlow)`

### 5. **RELATED_TO** 🔗
Links related concepts together.
- **From:** Concept
- **To:** Concept
- **Properties:**
  - `strength` (float): Relationship strength (0.0-1.0)
- **Usage:** `(Concept)-[:RELATED_TO]->(Concept)`

### 6. **USED_CONTEXT** 🎯
Links conversations to context items used.
- **From:** Conversation
- **To:** Document, Concept, etc.
- **Properties:**
  - `relevance` (float): Context relevance score
- **Usage:** `(Conversation)-[:USED_CONTEXT]->(Document)`

### 7. **HAS_CHUNK** 📄
Links dynamic documents to their content chunks.
- **From:** DynamicDocument
- **To:** DynamicDocument (self-reference)
- **Properties:**
  - `chunk_index` (integer): Chunk sequence number
  - `content_preview` (string): Preview of chunk content
  - `chunk_id` (string): Chunk identifier
- **Usage:** `(DynamicDocument)-[:HAS_CHUNK]->(DynamicDocument)`

### 8. **RELATES_TO** 🌉
Links dynamic content to existing static concepts.
- **From:** DynamicDocument
- **To:** Concept
- **Properties:**
  - `relationship_type` (string): "dynamic_to_static"
  - `confidence` (float): Confidence score
- **Usage:** `(DynamicDocument)-[:RELATES_TO]->(Concept)`

## Schema Patterns

### Static Content Pattern
```cypher
(Capability)-[:CONTAINS]->(Document)-[:MENTIONS]->(Concept)
(Document)-[:DESCRIBES]->(BusinessFlow)
(Guideline)-[:DEFINES]->(Concept)
(Concept)-[:RELATED_TO]->(Concept)
```

### Dynamic Content Pattern
```cypher
(DynamicDocument)-[:MENTIONS]->(Concept)
(DynamicDocument)-[:HAS_CHUNK]->(DynamicDocument)
(DynamicDocument)-[:RELATES_TO]->(Concept)
```

### Conversation Pattern
```cypher
(Conversation)-[:USED_CONTEXT]->(Document)
(Conversation)-[:USED_CONTEXT]->(Concept)
(Conversation)-[:USED_CONTEXT]->(DynamicDocument)
```

## Common Queries

### Find Documents by Capability
```cypher
MATCH (cap:Capability {name: "EKYC"})-[:CONTAINS]->(doc:Document)
RETURN doc
```

### Find Concepts in Dynamic Content
```cypher
MATCH (dd:DynamicDocument)-[:MENTIONS]->(c:Concept)
WHERE dd.source_type = "upload"
RETURN c.name, count(dd) as mention_count
ORDER BY mention_count DESC
```

### Find Related Documents through Concepts
```cypher
MATCH (d1:Document)-[:MENTIONS]->(c:Concept)<-[:MENTIONS]-(d2:Document)
WHERE d1.id = $document_id AND d1.id <> d2.id
RETURN d2, count(c) as shared_concepts
ORDER BY shared_concepts DESC
```

### Search Dynamic Content
```cypher
MATCH (dd:DynamicDocument)
OPTIONAL MATCH (dd)-[:MENTIONS]->(c:Concept)
WHERE dd.source_type IN ["upload", "url", "github"]
AND any(word IN $query_words WHERE c.name CONTAINS word)
RETURN dd, collect(c.name) as concepts
```

### Get Conversation Context
```cypher
MATCH (conv:Conversation)-[:USED_CONTEXT]->(context)
WHERE conv.session_id = $session_id
RETURN conv, context
ORDER BY conv.timestamp DESC
```

## Performance Considerations

### Indexes
- Content search: `document_content_index`
- Concept lookup: `concept_keywords_index`
- Guideline filtering: `guideline_type_index`
- Business flow ordering: `business_flow_order_index`

### Constraints
- All node types have unique ID constraints
- Concept names are unique across the system
- Prevents duplicate relationships

### Query Optimization
- Use parameterized queries for better performance
- Limit result sets with `LIMIT` clauses
- Use `OPTIONAL MATCH` for optional relationships
- Index on frequently queried properties

## Dynamic Content Integration

### Content Processing Flow
1. **Upload/URL/GitHub** → Extract content
2. **Create DynamicDocument** node
3. **Extract concepts** → Create/update Concept nodes
4. **Link relationships** → MENTIONS, HAS_CHUNK
5. **Cross-link** → RELATES_TO existing concepts

### Source Type Tracking
- `source_type`: "upload", "url", "github"
- `source_identifier`: Original source reference
- `dynamic_sources`: Tracks which dynamic sources mention concepts

### Temporal Aspects
- `created_at`: When content was added
- `last_updated`: When concepts were updated
- `processing_timestamp`: When content was processed

This schema supports both static lending documentation and dynamic user-generated content, enabling comprehensive context retrieval and relationship discovery across all content sources.