"""
Configuration settings for the mem0 memory layer.
Provides flexible configuration for different deployment environments.
"""

import os
from typing import Dict, Any


class MemoryConfig:
    """Configuration class for mem0 memory system"""
    
    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """Get default mem0 configuration"""
        return {
            "embedder": {
                "provider": "huggingface",
                "config": {
                    "model": os.getenv("MEMORY_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
                }
            },
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "host": os.getenv("QDRANT_HOST", "localhost"),
                    "port": int(os.getenv("QDRANT_PORT", 6333)),
                    "collection_name": os.getenv("MEMORY_COLLECTION_NAME", "lending_memory")
                }
            }
        }
    
    @staticmethod
    def get_development_config() -> Dict[str, Any]:
        """Get development-specific configuration"""
        config = MemoryConfig.get_default_config()
        
        # Use in-memory vector store for development
        if os.getenv("MEMORY_DEV_MODE", "false").lower() == "true":
            config["vector_store"] = {
                "provider": "chroma",
                "config": {
                    "path": "./memory_dev_db"
                }
            }
        
        return config
    
    @staticmethod
    def get_production_config() -> Dict[str, Any]:
        """Get production-specific configuration"""
        config = MemoryConfig.get_default_config()
        
        # Production-specific settings
        config["vector_store"]["config"].update({
            "timeout": int(os.getenv("QDRANT_TIMEOUT", 30)),
            "prefer_grpc": os.getenv("QDRANT_USE_GRPC", "false").lower() == "true"
        })
        
        return config
    
    @staticmethod
    def get_config() -> Dict[str, Any]:
        """Get configuration based on environment"""
        env = os.getenv("ENVIRONMENT", "development").lower()
        
        if env == "production":
            return MemoryConfig.get_production_config()
        else:
            return MemoryConfig.get_development_config()


class LendingContextConfig:
    """Configuration for lending context extraction"""
    
    @staticmethod
    def get_default_paths() -> Dict[str, str]:
        """Get default paths for lending context"""
        base_path = os.getenv("LENDING_CONTEXT_PATH", "./Lending")
        
        return {
            "base_path": base_path,
            "capabilities_path": os.path.join(base_path, "Capabilities"),
            "common_prompts_path": os.path.join(base_path, "CommonPrompts"),
            "specs_path": base_path
        }
    
    @staticmethod
    def get_extraction_settings() -> Dict[str, Any]:
        """Get settings for context extraction"""
        return {
            "max_file_size": int(os.getenv("MAX_CONTEXT_FILE_SIZE", 1024 * 1024)),  # 1MB
            "supported_extensions": [".txt", ".yaml", ".yml", ".json"],
            "encoding": "utf-8",
            "ignore_patterns": ["*.log", "*.tmp", "__pycache__", ".git"]
        }


class ChatbotConfig:
    """Configuration for the chatbot"""
    
    @staticmethod
    def get_claude_config() -> Dict[str, Any]:
        """Get Claude API configuration"""
        return {
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
            "model": os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022"),
            "max_tokens": int(os.getenv("CLAUDE_MAX_TOKENS", 2000)),
            "temperature": float(os.getenv("CLAUDE_TEMPERATURE", 0.7)),
            "timeout": int(os.getenv("CLAUDE_TIMEOUT", 30))
        }
    
    @staticmethod
    def get_context_settings() -> Dict[str, Any]:
        """Get context processing settings"""
        return {
            "max_context_items": int(os.getenv("MAX_CONTEXT_ITEMS", 8)),
            "context_window_size": int(os.getenv("CONTEXT_WINDOW_SIZE", 4000)),
            "conversation_history_limit": int(os.getenv("CONVERSATION_HISTORY_LIMIT", 3)),
            "enable_concept_extraction": os.getenv("ENABLE_CONCEPT_EXTRACTION", "true").lower() == "true"
        }


class IntegrationConfig:
    """Configuration for service integration"""
    
    @staticmethod
    def get_fusion_weights() -> Dict[str, float]:
        """Get weights for context fusion scoring"""
        return {
            "memory_weight": float(os.getenv("MEMORY_WEIGHT", 0.25)),
            "vector_weight": float(os.getenv("VECTOR_WEIGHT", 0.20)),
            "graph_weight": float(os.getenv("GRAPH_WEIGHT", 0.20)),
            "conversation_weight": float(os.getenv("CONVERSATION_WEIGHT", 0.10)),
            "fusion_weight": float(os.getenv("FUSION_WEIGHT", 0.15)),
            "content_relevance_weight": float(os.getenv("CONTENT_RELEVANCE_WEIGHT", 0.30)),
            "metadata_relevance_weight": float(os.getenv("METADATA_RELEVANCE_WEIGHT", 0.15)),
            "source_reliability_weight": float(os.getenv("SOURCE_RELIABILITY_WEIGHT", 0.10)),
            "recency_weight": float(os.getenv("RECENCY_WEIGHT", 0.05))
        }
    
    @staticmethod
    def get_performance_settings() -> Dict[str, Any]:
        """Get performance-related settings"""
        return {
            "max_concurrent_requests": int(os.getenv("MAX_CONCURRENT_REQUESTS", 3)),
            "request_timeout": int(os.getenv("REQUEST_TIMEOUT", 30)),
            "enable_caching": os.getenv("ENABLE_CACHING", "true").lower() == "true",
            "cache_ttl": int(os.getenv("CACHE_TTL", 300))  # 5 minutes
        }


def validate_config() -> Dict[str, Any]:
    """Validate all configuration settings"""
    validation_results = {
        "valid": True,
        "errors": [],
        "warnings": []
    }
    
    # Validate required environment variables
    required_vars = ["ANTHROPIC_API_KEY"]
    for var in required_vars:
        if not os.getenv(var):
            validation_results["valid"] = False
            validation_results["errors"].append(f"Required environment variable {var} is not set")
    
    # Validate numeric settings
    numeric_settings = [
        ("QDRANT_PORT", 6333),
        ("MAX_CONTEXT_ITEMS", 8),
        ("CLAUDE_MAX_TOKENS", 2000)
    ]
    
    for var_name, default_value in numeric_settings:
        try:
            int(os.getenv(var_name, default_value))
        except ValueError:
            validation_results["warnings"].append(f"{var_name} is not a valid integer, using default")
    
    # Validate float settings
    float_settings = [
        ("CLAUDE_TEMPERATURE", 0.7),
        ("MEMORY_WEIGHT", 0.25)
    ]
    
    for var_name, default_value in float_settings:
        try:
            float(os.getenv(var_name, default_value))
        except ValueError:
            validation_results["warnings"].append(f"{var_name} is not a valid float, using default")
    
    return validation_results


def get_all_configs() -> Dict[str, Any]:
    """Get all configuration settings"""
    return {
        "memory": MemoryConfig.get_config(),
        "lending_context": {
            "paths": LendingContextConfig.get_default_paths(),
            "extraction": LendingContextConfig.get_extraction_settings()
        },
        "chatbot": {
            "claude": ChatbotConfig.get_claude_config(),
            "context": ChatbotConfig.get_context_settings()
        },
        "integration": {
            "fusion_weights": IntegrationConfig.get_fusion_weights(),
            "performance": IntegrationConfig.get_performance_settings()
        },
        "validation": validate_config()
    }