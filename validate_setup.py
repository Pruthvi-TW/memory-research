#!/usr/bin/env python3
"""
Setup validation script for the Dynamic Context Ingestion System.
Checks all dependencies, configuration, and system readiness.
"""

import sys
import os
import importlib
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

def check_python_version() -> Tuple[bool, str]:
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        return True, f"✅ Python {version.major}.{version.minor}.{version.micro}"
    else:
        return False, f"❌ Python {version.major}.{version.minor}.{version.micro} (requires 3.8+)"

def check_python_dependencies() -> Tuple[bool, List[str]]:
    """Check if all required Python packages are installed."""
    required_packages = [
        'fastapi', 'uvicorn', 'anthropic', 'chromadb', 'neo4j', 
        'sentence_transformers', 'pandas', 'numpy', 'requests',
        'python_docx', 'PyPDF2', 'beautifulsoup4', 'aiohttp',
        'python_dotenv', 'pydantic'
    ]
    
    results = []
    all_installed = True
    
    for package in required_packages:
        try:
            # Handle package name variations
            import_name = package
            if package == 'python_docx':
                import_name = 'docx'
            elif package == 'python_dotenv':
                import_name = 'dotenv'
            elif package == 'PyPDF2':
                import_name = 'PyPDF2'
            elif package == 'beautifulsoup4':
                import_name = 'bs4'
            
            importlib.import_module(import_name)
            results.append(f"✅ {package}")
        except ImportError:
            results.append(f"❌ {package} (missing)")
            all_installed = False
    
    return all_installed, results

def check_node_and_frontend() -> Tuple[bool, List[str]]:
    """Check Node.js and frontend build status."""
    results = []
    
    # Check Node.js
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            results.append(f"✅ Node.js {version}")
            node_ok = True
        else:
            results.append("❌ Node.js not found")
            node_ok = False
    except FileNotFoundError:
        results.append("❌ Node.js not installed")
        node_ok = False
    
    # Check npm
    try:
        result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            results.append(f"✅ npm {version}")
            npm_ok = True
        else:
            results.append("❌ npm not found")
            npm_ok = False
    except FileNotFoundError:
        results.append("❌ npm not installed")
        npm_ok = False
    
    # Check frontend build
    frontend_dist = Path("frontend/dist")
    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
        results.append("✅ Frontend built")
        frontend_ok = True
    else:
        results.append("❌ Frontend not built (run: cd frontend && npm install && npm run build)")
        frontend_ok = False
    
    return node_ok and npm_ok and frontend_ok, results

def check_configuration() -> Tuple[bool, List[str]]:
    """Check system configuration."""
    results = []
    
    # Check if .env file exists
    env_file = Path(".env")
    if env_file.exists():
        results.append("✅ .env file exists")
        
        # Try to load configuration
        try:
            from config import config, validate_environment
            
            validation = validate_environment()
            if validation["valid"]:
                results.append("✅ Configuration is valid")
                
                # Check enabled features
                features = validation["features_enabled"]
                for feature, enabled in features.items():
                    status = "✅" if enabled else "⚠️"
                    results.append(f"{status} {feature} {'enabled' if enabled else 'disabled'}")
                
                config_ok = True
            else:
                results.append("❌ Configuration validation failed:")
                for error in validation["errors"]:
                    results.append(f"   - {error}")
                config_ok = False
                
        except Exception as e:
            results.append(f"❌ Configuration error: {e}")
            config_ok = False
    else:
        results.append("❌ .env file missing (copy from .env.example)")
        config_ok = False
    
    return config_ok, results

def check_directories() -> Tuple[bool, List[str]]:
    """Check required directories and files."""
    results = []
    all_ok = True
    
    required_paths = [
        ("main.py", "Main application file"),
        ("config.py", "Configuration module"),
        ("requirements.txt", "Python dependencies"),
        ("services/", "Services directory"),
        ("vector/", "Vector service directory"),
        ("graph/", "Graph service directory"),
        ("memory_layer/", "Memory layer directory"),
        ("models/", "Data models directory"),
        ("frontend/", "Frontend directory")
    ]
    
    for path_str, description in required_paths:
        path = Path(path_str)
        if path.exists():
            results.append(f"✅ {description}")
        else:
            results.append(f"❌ {description} missing: {path_str}")
            all_ok = False
    
    return all_ok, results

def check_optional_services() -> Tuple[bool, List[str]]:
    """Check optional external services."""
    results = []
    
    # Check Neo4j (optional)
    try:
        from neo4j import GraphDatabase
        from config import config
        
        if config.database.neo4j_password != "password":
            try:
                driver = GraphDatabase.driver(
                    config.database.neo4j_uri,
                    auth=(config.database.neo4j_user, config.database.neo4j_password)
                )
                with driver.session() as session:
                    session.run("RETURN 1")
                results.append("✅ Neo4j connection successful")
                driver.close()
            except Exception as e:
                results.append(f"⚠️ Neo4j connection failed: {e}")
        else:
            results.append("⚠️ Neo4j not configured (using default password)")
    except Exception as e:
        results.append(f"⚠️ Neo4j check failed: {e}")
    
    # Check Mem0 (optional)
    try:
        from config import config
        if config.ai.mem0_api_key:
            results.append("✅ Mem0 API key configured")
        else:
            results.append("⚠️ Mem0 API key not configured")
    except Exception as e:
        results.append(f"⚠️ Mem0 check failed: {e}")
    
    return True, results  # Optional services don't fail validation

def run_basic_tests() -> Tuple[bool, List[str]]:
    """Run basic functionality tests."""
    results = []
    
    try:
        # Test configuration loading
        from config import config
        results.append("✅ Configuration loading")
        
        # Test service imports
        from services.dynamic_context_service import DynamicContextService
        results.append("✅ Dynamic context service import")
        
        from vector.vector_service import VectorService
        results.append("✅ Vector service import")
        
        from memory_layer.mem0_manager import Mem0Manager
        results.append("✅ Memory manager import")
        
        # Test model imports
        from models.dynamic_context_models import FileUploadRequest
        results.append("✅ Data models import")
        
        return True, results
        
    except Exception as e:
        results.append(f"❌ Basic test failed: {e}")
        return False, results

def main():
    """Run all validation checks."""
    print("🔍 Dynamic Context Ingestion System - Setup Validation")
    print("=" * 60)
    
    checks = [
        ("Python Version", check_python_version),
        ("Python Dependencies", check_python_dependencies),
        ("Node.js & Frontend", check_node_and_frontend),
        ("Configuration", check_configuration),
        ("Directory Structure", check_directories),
        ("Optional Services", check_optional_services),
        ("Basic Tests", run_basic_tests)
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}:")
        print("-" * 30)
        
        try:
            passed, messages = check_func()
            
            for message in messages:
                print(f"   {message}")
            
            if not passed:
                all_passed = False
                
        except Exception as e:
            print(f"   ❌ Check failed with error: {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("🎉 All checks passed! System is ready to run.")
        print("\n🚀 To start the system:")
        print("   ./run_system.sh")
        print("   or")
        print("   python main.py")
        print("\n📖 For more information:")
        print("   • README: DYNAMIC_CONTEXT_README.md")
        print("   • Deployment: DEPLOYMENT_GUIDE.md")
        print("   • Test: python test_dynamic_context.py")
        
        return 0
    else:
        print("❌ Some checks failed. Please address the issues above.")
        print("\n🔧 Common fixes:")
        print("   • Install missing dependencies: pip install -r requirements.txt")
        print("   • Build frontend: cd frontend && npm install && npm run build")
        print("   • Create .env file with required configuration")
        print("   • Check API keys and database connections")
        
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)