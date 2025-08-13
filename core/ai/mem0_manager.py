"""
Lending Memory Manager using mem0 for semantic memory management.
Integrates with existing vector and graph layers for enhanced context retrieval.
"""

import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    print("⚠️ mem0 not available. Install with: pip install mem0ai")

logger = logging.getLogger(__name__)


class Mem0Manager:
    """
    Memory manager for lending chatbot using mem0 for semantic memory.
    Provides persistent memory across conversations and enhanced context retrieval.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the memory manager with mem0 configuration.
        
        Args:
            config: Optional configuration for mem0 setup
        """
        self.memory = None
        self.fallback_memory = {}  # In-memory fallback when mem0 unavailable
        self.user_id = "lending_user"
        
        # Default configuration for mem0
        self.config = config or {
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "path": "./memory_chroma_db"
                }
            },
            "llm": {
                "provider": "openai",
                "config": {
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.1
                }
            }
        }
        
        self._initialize_memory()
        
    def _initialize_memory(self):
        """Initialize mem0 memory system with fallback"""
        if not MEM0_AVAILABLE:
            logger.warning("mem0 not available, using fallback memory")
            return
            
        try:
            # Check if OpenAI API key is available for mem0
            if not os.getenv("OPENAI_API_KEY"):
                logger.warning("OpenAI API key not found, mem0 requires it for LLM operations")
                logger.info("📝 Using fallback in-memory storage")
                return
                
            # Try to initialize mem0 with error handling
            self.memory = Memory(self.config)
            logger.info("✅ mem0 memory system initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize mem0: {e}")
            logger.info("📝 Using fallback in-memory storage")
            # Ensure memory is None so fallback is used
            self.memory = None
            
    def store_lending_context(self, context_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Store lending context data in memory.
        
        Args:
            context_data: Structured context data from context extractor
            
        Returns:
            Dictionary with storage statistics
        """
        stats = {
            "capability_prompts": 0,
            "capability_specs": 0,
            "common_prompts": 0,
            "total_stored": 0
        }
        
        try:
            # Store capability prompts
            if "capabilities" in context_data:
                for capability, cap_data in context_data["capabilities"].items():
                    if "prompts" in cap_data:
                        for prompt_type, prompt_content in cap_data["prompts"].items():
                            self._store_memory_item(
                                content=prompt_content,
                                metadata={
                                    "type": "capability_prompt",
                                    "capability": capability,
                                    "prompt_type": prompt_type,
                                    "source": f"{capability}/{prompt_type}"
                                }
                            )
                            stats["capability_prompts"] += 1
                    
                    # Store capability specs
                    if "specs" in cap_data:
                        for spec_name, spec_content in cap_data["specs"].items():
                            # Convert spec to string if it's a dict
                            if isinstance(spec_content, dict):
                                spec_content = json.dumps(spec_content, indent=2)
                            
                            self._store_memory_item(
                                content=spec_content,
                                metadata={
                                    "type": "capability_spec",
                                    "capability": capability,
                                    "spec_name": spec_name,
                                    "source": f"{capability}/specs/{spec_name}"
                                }
                            )
                            stats["capability_specs"] += 1
            
            # Store common prompts
            if "common_prompts" in context_data:
                for prompt_name, prompt_content in context_data["common_prompts"].items():
                    self._store_memory_item(
                        content=prompt_content,
                        metadata={
                            "type": "common_prompt",
                            "prompt_name": prompt_name,
                            "source": f"common/{prompt_name}"
                        }
                    )
                    stats["common_prompts"] += 1
            
            stats["total_stored"] = sum(stats.values())
            logger.info(f"📊 Stored {stats['total_stored']} items in memory")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error storing context in memory: {e}")
            return stats
            
    def _store_memory_item(self, content: str, metadata: Dict[str, Any]):
        """Store a single memory item with fallback"""
        if self.memory:
            try:
                self.memory.add(
                    content,
                    user_id=self.user_id,
                    metadata=metadata
                )
            except Exception as e:
                logger.error(f"❌ mem0 storage error: {e}")
                self._store_locally(content, metadata)
        else:
            self._store_locally(content, metadata)
            
    def _store_locally(self, content: str, metadata: Dict[str, Any]):
        """Store in fallback local memory"""
        item_id = f"{metadata.get('type', 'unknown')}_{len(self.fallback_memory)}"
        self.fallback_memory[item_id] = {
            "content": content,
            "metadata": metadata
        }
        
    def get_relevant_context(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get relevant context from memory based on query.
        
        Args:
            query: User query for context retrieval
            limit: Maximum number of context items to return
            
        Returns:
            List of relevant context items with metadata
        """
        if self.memory:
            try:
                results = self.memory.search(
                    query,
                    user_id=self.user_id,
                    limit=limit
                )
                
                # Format results for consistency
                formatted_results = []
                for result in results:
                    formatted_results.append({
                        "content": result.get("memory", ""),
                        "metadata": result.get("metadata", {}),
                        "score": result.get("score", 0.0),
                        "source": "mem0"
                    })
                
                return formatted_results
                
            except Exception as e:
                logger.error(f"❌ mem0 search error: {e}")
                return self._search_locally(query, limit)
        else:
            return self._search_locally(query, limit)
            
    def _search_locally(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search in fallback local memory using keyword matching"""
        query_words = query.lower().split()
        results = []
        
        for item_id, item in self.fallback_memory.items():
            content = item["content"].lower()
            score = sum(1 for word in query_words if word in content) / len(query_words)
            
            if score > 0:
                results.append({
                    "content": item["content"],
                    "metadata": item["metadata"],
                    "score": score,
                    "source": "fallback"
                })
        
        # Sort by score and return top results
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
        
    def add_conversation(self, user_message: str, assistant_response: str, 
                        session_id: str, context_used: List[Dict[str, Any]] = None):
        """
        Store conversation turn in memory for future context.
        
        Args:
            user_message: User's message
            assistant_response: Assistant's response
            session_id: Session identifier
            context_used: Context items that were used in the response
        """
        conversation_content = f"User: {user_message}\nAssistant: {assistant_response}"
        
        metadata = {
            "type": "conversation",
            "session_id": session_id,
            "user_message": user_message,
            "assistant_response": assistant_response,
            "context_count": len(context_used) if context_used else 0
        }
        
        # Add context sources if available
        if context_used:
            metadata["context_sources"] = [
                item.get("metadata", {}).get("source", "unknown") 
                for item in context_used[:3]
            ]
        
        self._store_memory_item(conversation_content, metadata)
        
    def get_conversation_history(self, session_id: str = None, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Get recent conversation history.
        
        Args:
            session_id: Optional session ID to filter by
            limit: Maximum number of conversations to return
            
        Returns:
            List of recent conversation items
        """
        if self.memory:
            try:
                # Search for conversations
                results = self.memory.search(
                    "conversation",
                    user_id=self.user_id,
                    limit=limit * 2  # Get more to filter by session
                )
                
                # Filter by session if specified
                if session_id:
                    results = [
                        r for r in results 
                        if r.get("metadata", {}).get("session_id") == session_id
                    ]
                
                return results[:limit]
                
            except Exception as e:
                logger.error(f"❌ Error retrieving conversation history: {e}")
                return []
        else:
            # Fallback search
            conversations = [
                item for item in self.fallback_memory.values()
                if item["metadata"].get("type") == "conversation"
            ]
            
            if session_id:
                conversations = [
                    c for c in conversations
                    if c["metadata"].get("session_id") == session_id
                ]
            
            return conversations[-limit:]  # Return most recent
            
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive memory statistics.
        
        Returns:
            Dictionary with memory statistics
        """
        if self.memory:
            try:
                # Get all memories to analyze
                all_memories = self.memory.get_all(user_id=self.user_id)
                
                stats = {
                    "total_memories": len(all_memories),
                    "by_type": {},
                    "by_capability": {},
                    "memory_system": "mem0",
                    "status": "active"
                }
                
                # Analyze by type and capability
                for memory in all_memories:
                    metadata = memory.get("metadata", {})
                    mem_type = metadata.get("type", "unknown")
                    capability = metadata.get("capability", "general")
                    
                    stats["by_type"][mem_type] = stats["by_type"].get(mem_type, 0) + 1
                    stats["by_capability"][capability] = stats["by_capability"].get(capability, 0) + 1
                
                return stats
                
            except Exception as e:
                logger.error(f"❌ Error getting memory stats: {e}")
                return self._get_fallback_stats()
        else:
            return self._get_fallback_stats()
            
    def _get_fallback_stats(self) -> Dict[str, Any]:
        """Get statistics from fallback memory"""
        stats = {
            "total_memories": len(self.fallback_memory),
            "by_type": {},
            "by_capability": {},
            "memory_system": "fallback",
            "status": "limited"
        }
        
        for item in self.fallback_memory.values():
            metadata = item["metadata"]
            mem_type = metadata.get("type", "unknown")
            capability = metadata.get("capability", "general")
            
            stats["by_type"][mem_type] = stats["by_type"].get(mem_type, 0) + 1
            stats["by_capability"][capability] = stats["by_capability"].get(capability, 0) + 1
            
        return stats
        
    def clear_memory(self, memory_type: str = None) -> bool:
        """
        Clear memory items, optionally filtered by type.
        
        Args:
            memory_type: Optional type filter (e.g., 'conversation', 'capability_prompt')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.memory:
                if memory_type:
                    # Delete specific type (mem0 doesn't have direct type filtering)
                    # This would need to be implemented based on mem0's API
                    logger.warning("Type-specific deletion not implemented for mem0")
                    return False
                else:
                    # Clear all memories for user
                    self.memory.delete_all(user_id=self.user_id)
                    logger.info("🗑️ Cleared all memories from mem0")
                    return True
            else:
                if memory_type:
                    # Clear specific type from fallback
                    to_delete = [
                        k for k, v in self.fallback_memory.items()
                        if v["metadata"].get("type") == memory_type
                    ]
                    for k in to_delete:
                        del self.fallback_memory[k]
                else:
                    # Clear all fallback memory
                    self.fallback_memory.clear()
                
                logger.info(f"🗑️ Cleared {memory_type or 'all'} memories from fallback")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error clearing memory: {e}")
            return False
            
    def update_memory_config(self, new_config: Dict[str, Any]) -> bool:
        """
        Update memory configuration and reinitialize.
        
        Args:
            new_config: New configuration dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.config.update(new_config)
            self._initialize_memory()
            logger.info("🔄 Memory configuration updated")
            return True
        except Exception as e:
            logger.error(f"❌ Error updating memory config: {e}")
            return False
            
    def export_memory(self, output_path: str) -> bool:
        """
        Export memory data to file for backup/analysis.
        
        Args:
            output_path: Path to save the exported data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            export_data = {
                "config": self.config,
                "stats": self.get_memory_stats(),
                "memories": []
            }
            
            if self.memory:
                try:
                    all_memories = self.memory.get_all(user_id=self.user_id)
                    export_data["memories"] = all_memories
                except Exception as e:
                    logger.error(f"❌ Error exporting from mem0: {e}")
                    export_data["memories"] = list(self.fallback_memory.values())
            else:
                export_data["memories"] = list(self.fallback_memory.values())
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Memory exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error exporting memory: {e}")
            return False