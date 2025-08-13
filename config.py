"""
Configuration management for the Dynamic Context Ingestion System.
Centralizes all configuration settings with environment variable support.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    # Neo4j Graph Database
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "password")
    
    # Chroma Vector Database
    chroma_persist_directory: str = os.getenv("CHROMA_PERSIST_DIR", "./core/database/chroma_db")
    chroma_collection_name: str = os.getenv("CHROMA_COLLECTION", "lending_context")

@dataclass
class AIConfig:
    """AI service configuration."""
    # Anthropic Claude
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    anthropic_max_tokens: int = int(os.getenv("ANTHROPIC_MAX_TOKENS", "1500"))
    anthropic_temperature: float = float(os.getenv("ANTHROPIC_TEMPERATURE", "0.7"))
    
    # Mem0 Memory Layer
    mem0_api_key: str = os.getenv("MEM0_API_KEY", "")
    mem0_user_id: str = os.getenv("MEM0_USER_ID", "lending_chatbot")
    
    # Sentence Transformers
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

@dataclass
class ProcessingConfig:
    """Content processing configuration."""
    # File processing limits
    max_file_size: int = int(os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024)))  # 10MB
    max_files_per_upload: int = int(os.getenv("MAX_FILES_PER_UPLOAD", "10"))
    
    # URL processing limits
    max_url_content_size: int = int(os.getenv("MAX_URL_CONTENT_SIZE", str(5 * 1024 * 1024)))  # 5MB
    url_timeout: int = int(os.getenv("URL_TIMEOUT", "30"))
    
    # GitHub processing limits
    max_repo_files: int = int(os.getenv("MAX_REPO_FILES", "100"))
    github_timeout: int = int(os.getenv("GITHUB_TIMEOUT", "60"))
    
    # Concurrent processing
    max_concurrent_tasks: int = int(os.getenv("MAX_CONCURRENT_TASKS", "5"))
    
    # Content chunking
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "200"))

@dataclass
class ContextConfig:
    """Context retrieval configuration."""
    # Context limits
    max_context_items: int = int(os.getenv("MAX_CONTEXT_ITEMS", "8"))
    
    # Fusion scoring weights
    vector_weight: float = float(os.getenv("VECTOR_WEIGHT", "0.6"))
    graph_weight: float = float(os.getenv("GRAPH_WEIGHT", "0.4"))
    memory_weight: float = float(os.getenv("MEMORY_WEIGHT", "0.25"))
    
    # Context paths
    lending_context_path: str = os.getenv("LENDING_CONTEXT_PATH", "./Lending")

@dataclass
class ServerConfig:
    """Server configuration."""
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # CORS settings
    cors_origins: list = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(","))
    
    # Frontend settings
    frontend_dist_path: str = os.getenv("FRONTEND_DIST_PATH", "frontend/dist")

@dataclass
class LoggingConfig:
    """Logging configuration."""
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: Optional[str] = os.getenv("LOG_FILE")
    log_format: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

class SystemConfig:
    """Main system configuration class."""
    
    def __init__(self):
        self.database = DatabaseConfig()
        self.ai = AIConfig()
        self.processing = ProcessingConfig()
        self.context = ContextConfig()
        self.server = ServerConfig()
        self.logging = LoggingConfig()
        
        # Validate critical configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate critical configuration settings."""
        errors = []
        
        # Check required API keys
        if not self.ai.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY is required")
        
        # Check file size limits
        if self.processing.max_file_size <= 0:
            errors.append("MAX_FILE_SIZE must be positive")
        
        # Check context limits
        if self.context.max_context_items <= 0:
            errors.append("MAX_CONTEXT_ITEMS must be positive")
        
        # Check fusion weights sum to reasonable value
        total_weight = (self.context.vector_weight + 
                       self.context.graph_weight + 
                       self.context.memory_weight)
        if total_weight <= 0:
            errors.append("Fusion weights must sum to positive value")
        
        if errors:
            raise ValueError(f"Configuration errors: {'; '.join(errors)}")
    
    def get_supported_file_types(self) -> Dict[str, list]:
        """Get supported file types for different processors."""
        return {
            "upload": [
                "text/plain",
                "text/markdown", 
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/msword"
            ],
            "url": [
                "text/html",
                "text/plain",
                "application/json",
                "text/xml",
                "application/xml"
            ],
            "github": [
                ".md", ".txt", ".rst", ".py", ".js", ".json", 
                ".yml", ".yaml", ".xml", ".html", ".css"
            ]
        }
    
    def get_processing_limits(self) -> Dict[str, Any]:
        """Get processing limits for validation."""
        return {
            "max_file_size": self.processing.max_file_size,
            "max_files_per_upload": self.processing.max_files_per_upload,
            "max_url_content_size": self.processing.max_url_content_size,
            "max_repo_files": self.processing.max_repo_files,
            "max_concurrent_tasks": self.processing.max_concurrent_tasks
        }
    
    def get_database_urls(self) -> Dict[str, str]:
        """Get database connection URLs."""
        return {
            "neo4j": f"{self.database.neo4j_uri}",
            "chroma": self.database.chroma_persist_directory
        }
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled based on configuration."""
        feature_checks = {
            "neo4j": bool(self.database.neo4j_password and self.database.neo4j_password != "password"),
            "mem0": bool(self.ai.mem0_api_key),
            "github": True,  # Always enabled
            "url_processing": True,  # Always enabled
            "file_upload": True,  # Always enabled
        }
        
        return feature_checks.get(feature, False)
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get environment information for debugging."""
        return {
            "python_version": os.sys.version,
            "environment_variables": {
                key: "***" if "key" in key.lower() or "password" in key.lower() else value
                for key, value in os.environ.items()
                if key.startswith(("ANTHROPIC_", "NEO4J_", "MEM0_", "CHROMA_", "MAX_", "CORS_"))
            },
            "features_enabled": {
                feature: self.is_feature_enabled(feature)
                for feature in ["neo4j", "mem0", "github", "url_processing", "file_upload"]
            },
            "processing_limits": self.get_processing_limits(),
            "supported_file_types": self.get_supported_file_types()
        }

# Global configuration instance
config = SystemConfig()

# Convenience functions for common configuration access
def get_anthropic_config() -> Dict[str, Any]:
    """Get Anthropic API configuration."""
    return {
        "api_key": config.ai.anthropic_api_key,
        "model": config.ai.anthropic_model,
        "max_tokens": config.ai.anthropic_max_tokens,
        "temperature": config.ai.anthropic_temperature
    }

def get_database_config() -> Dict[str, Any]:
    """Get database configuration."""
    return {
        "neo4j": {
            "uri": config.database.neo4j_uri,
            "user": config.database.neo4j_user,
            "password": config.database.neo4j_password
        },
        "chroma": {
            "persist_directory": config.database.chroma_persist_directory,
            "collection_name": config.database.chroma_collection_name
        }
    }

def get_processing_config() -> Dict[str, Any]:
    """Get processing configuration."""
    return {
        "max_file_size": config.processing.max_file_size,
        "max_files_per_upload": config.processing.max_files_per_upload,
        "max_url_content_size": config.processing.max_url_content_size,
        "max_concurrent_tasks": config.processing.max_concurrent_tasks,
        "chunk_size": config.processing.chunk_size,
        "chunk_overlap": config.processing.chunk_overlap
    }

def validate_environment() -> Dict[str, Any]:
    """Validate the environment and return status."""
    try:
        config._validate_config()
        return {
            "valid": True,
            "errors": [],
            "warnings": [],
            "features_enabled": {
                feature: config.is_feature_enabled(feature)
                for feature in ["neo4j", "mem0", "github", "url_processing", "file_upload"]
            }
        }
    except ValueError as e:
        return {
            "valid": False,
            "errors": [str(e)],
            "warnings": [],
            "features_enabled": {}
        }

if __name__ == "__main__":
    # Print configuration summary when run directly
    print("🔧 Dynamic Context System Configuration")
    print("=" * 50)
    
    validation = validate_environment()
    if validation["valid"]:
        print("✅ Configuration is valid")
    else:
        print("❌ Configuration errors:")
        for error in validation["errors"]:
            print(f"   - {error}")
    
    print(f"\n📊 Features enabled:")
    for feature, enabled in validation["features_enabled"].items():
        status = "✅" if enabled else "❌"
        print(f"   {status} {feature}")
    
    print(f"\n⚙️  Processing limits:")
    limits = config.get_processing_limits()
    for key, value in limits.items():
        if "size" in key:
            value_mb = value / (1024 * 1024)
            print(f"   - {key}: {value_mb:.1f}MB")
        else:
            print(f"   - {key}: {value}")
    
    print(f"\n🗄️  Database configuration:")
    db_config = get_database_config()
    print(f"   - Neo4j: {db_config['neo4j']['uri']}")
    print(f"   - Chroma: {db_config['chroma']['persist_directory']}")
    
    print(f"\n🤖 AI configuration:")
    ai_config = get_anthropic_config()
    print(f"   - Model: {ai_config['model']}")
    print(f"   - Max tokens: {ai_config['max_tokens']}")
    print(f"   - Temperature: {ai_config['temperature']}")
    print(f"   - API key: {'✅ Set' if ai_config['api_key'] else '❌ Missing'}")