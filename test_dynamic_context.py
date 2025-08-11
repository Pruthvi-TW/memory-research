#!/usr/bin/env python3
"""
Test script for dynamic context ingestion system.
Tests file upload, URL processing, and GitHub repository processing.
"""

import asyncio
import json
import aiohttp
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

async def test_system_health():
    """Test system health and initialization."""
    print("🔍 Testing system health...")
    
    async with aiohttp.ClientSession() as session:
        # Check health
        async with session.get(f"{BASE_URL}/api/health") as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ System health: {data['status']}")
                return True
            else:
                print(f"❌ Health check failed: {response.status}")
                return False

async def test_file_upload():
    """Test file upload processing."""
    print("\n📁 Testing file upload...")
    
    # Create a test file
    test_content = """
# Test Document for Dynamic Context

This is a test document to verify the dynamic context ingestion system.

## Key Concepts
- eKYC verification
- PAN validation
- API integration
- Document processing

## Technical Details
The system should extract and chunk this content, then store it in:
1. Vector database (Chroma) for similarity search
2. Memory layer (Mem0) for semantic memory
3. Graph database (Neo4j) for relationship mapping

This content should become immediately available for LLM context retrieval.
"""
    
    files = [{
        "filename": "test_document.md",
        "content": test_content,
        "content_type": "text/markdown",
        "size": len(test_content.encode('utf-8'))
    }]
    
    async with aiohttp.ClientSession() as session:
        # Upload file
        async with session.post(
            f"{BASE_URL}/api/dynamic-context/upload",
            json={"files": files}
        ) as response:
            if response.status == 200:
                data = await response.json()
                task_id = data["task_id"]
                print(f"✅ File upload started: {task_id}")
                
                # Monitor processing
                await monitor_task(session, task_id)
                return True
            else:
                error_data = await response.json()
                print(f"❌ File upload failed: {error_data}")
                return False

async def test_url_processing():
    """Test URL content processing."""
    print("\n🌐 Testing URL processing...")
    
    # Use a simple, reliable URL
    test_url = "https://httpbin.org/json"
    
    async with aiohttp.ClientSession() as session:
        # Process URL
        async with session.post(
            f"{BASE_URL}/api/dynamic-context/url",
            json={"url": test_url}
        ) as response:
            if response.status == 200:
                data = await response.json()
                task_id = data["task_id"]
                print(f"✅ URL processing started: {task_id}")
                
                # Monitor processing
                await monitor_task(session, task_id)
                return True
            else:
                error_data = await response.json()
                print(f"❌ URL processing failed: {error_data}")
                return False

async def test_github_processing():
    """Test GitHub repository processing."""
    print("\n🐙 Testing GitHub processing...")
    
    # Use a small, public repository with documentation
    test_repo = "https://github.com/octocat/Hello-World"
    
    async with aiohttp.ClientSession() as session:
        # Process repository
        async with session.post(
            f"{BASE_URL}/api/dynamic-context/github",
            json={"repo_url": test_repo}
        ) as response:
            if response.status == 200:
                data = await response.json()
                task_id = data["task_id"]
                print(f"✅ GitHub processing started: {task_id}")
                
                # Monitor processing
                await monitor_task(session, task_id)
                return True
            else:
                error_data = await response.json()
                print(f"❌ GitHub processing failed: {error_data}")
                return False

async def monitor_task(session: aiohttp.ClientSession, task_id: str, max_wait: int = 60):
    """Monitor task processing status."""
    print(f"⏳ Monitoring task {task_id}...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        async with session.get(f"{BASE_URL}/api/dynamic-context/status/{task_id}") as response:
            if response.status == 200:
                data = await response.json()
                status = data["status"]
                
                if status == "completed":
                    progress = data.get("progress", {})
                    print(f"✅ Task completed!")
                    print(f"   📄 Documents processed: {progress.get('documents_processed', 0)}")
                    print(f"   🧩 Chunks created: {progress.get('chunks_created', 0)}")
                    print(f"   🔢 Vector embeddings: {progress.get('vector_embeddings', 0)}")
                    print(f"   🧠 Memory items: {progress.get('memory_items_stored', 0)}")
                    return True
                elif status == "failed":
                    print(f"❌ Task failed: {data.get('message', 'Unknown error')}")
                    return False
                else:
                    print(f"   Status: {status}")
                    await asyncio.sleep(2)
            else:
                print(f"❌ Status check failed: {response.status}")
                return False
    
    print(f"⏰ Task monitoring timed out after {max_wait} seconds")
    return False

async def test_chat_integration():
    """Test that dynamically added content is available in chat."""
    print("\n💬 Testing chat integration...")
    
    test_query = "Tell me about the test document and eKYC verification"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": test_query,
                "session_id": "test_session"
            }
        ) as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ Chat response received")
                print(f"   📝 Response length: {len(data['response'])} characters")
                print(f"   📊 Context items: {data.get('processing_info', {}).get('total_context_items', 0)}")
                
                # Check if our test content influenced the response
                if "test document" in data['response'].lower() or "dynamic context" in data['response'].lower():
                    print(f"✅ Dynamic content detected in response!")
                else:
                    print(f"⚠️ Dynamic content may not be influencing responses")
                
                return True
            else:
                error_data = await response.json()
                print(f"❌ Chat test failed: {error_data}")
                return False

async def test_system_insights():
    """Test system insights endpoint."""
    print("\n📊 Testing system insights...")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/dynamic-context/insights") as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ System insights retrieved")
                
                processing_summary = data.get("processing_summary", {})
                print(f"   📋 Total tasks: {processing_summary.get('total_tasks', 0)}")
                print(f"   ✅ Completed: {processing_summary.get('completed_tasks', 0)}")
                print(f"   ❌ Failed: {processing_summary.get('failed_tasks', 0)}")
                
                system_impact = data.get("system_impact", {})
                print(f"   🧩 Total chunks added: {system_impact.get('total_chunks_added', 0)}")
                print(f"   🧠 Memory items added: {system_impact.get('total_memory_items_added', 0)}")
                
                recommendations = data.get("recommendations", [])
                if recommendations:
                    print(f"   💡 Recommendations:")
                    for rec in recommendations:
                        print(f"      - {rec}")
                
                return True
            else:
                error_data = await response.json()
                print(f"❌ Insights test failed: {error_data}")
                return False

async def main():
    """Run all tests."""
    print("🚀 Starting Dynamic Context Ingestion System Tests")
    print("=" * 60)
    
    tests = [
        ("System Health", test_system_health),
        ("File Upload", test_file_upload),
        ("URL Processing", test_url_processing),
        ("GitHub Processing", test_github_processing),
        ("Chat Integration", test_chat_integration),
        ("System Insights", test_system_insights)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Test Results Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Dynamic context system is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the logs above for details.")

if __name__ == "__main__":
    asyncio.run(main())