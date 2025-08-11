#!/usr/bin/env python3
"""
Comprehensive test script for mem0, vector, and graph components integration.
Tests each component individually and their integration with dynamic data.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config
from vector.vector_service import VectorService
from graph.neo4j_service import Neo4jService
from graph.context_repository import ContextRepository
from memory_layer.mem0_manager import Mem0Manager
from services.integration_service import IntegrationService


class ComponentTester:
    """Comprehensive tester for all system components"""
    
    def __init__(self):
        self.vector_service = None
        self.neo4j_service = None
        self.context_repository = None
        self.mem0_manager = None
        self.integration_service = None
        self.test_results = {}
        
    async def initialize_services(self):
        """Initialize all services for testing"""
        print("🔧 Initializing services...")
        
        try:
            # Initialize vector service
            self.vector_service = VectorService()
            await self.vector_service.initialize()
            print("✅ Vector service initialized")
            
            # Initialize Neo4j service
            self.neo4j_service = Neo4jService()
            await self.neo4j_service.initialize()
            print("✅ Neo4j service initialized")
            
            # Initialize context repository
            self.context_repository = ContextRepository(self.neo4j_service)
            print("✅ Context repository initialized")
            
            # Initialize mem0 manager
            self.mem0_manager = Mem0Manager()
            print("✅ Mem0 manager initialized")
            
            # Initialize integration service
            self.integration_service = IntegrationService(
                self.vector_service, 
                self.context_repository
            )
            print("✅ Integration service initialized")
            
            return True
            
        except Exception as e:
            print(f"❌ Service initialization failed: {e}")
            return False
    
    async def test_vector_service(self) -> Dict[str, Any]:
        """Test vector service functionality"""
        print("\n📊 Testing Vector Service...")
        results = {"passed": 0, "failed": 0, "details": []}
        
        try:
            # Test 1: Add test documents
            test_docs = [
                {
                    "content": "eKYC verification is a digital process for customer identity verification using Aadhaar and PAN documents.",
                    "source": "test_ekyc_doc.md",
                    "chunk_id": "chunk_1",
                    "type": "guideline",
                    "capability": "EKYC",
                    "source_type": "dynamic",
                    "metadata": {
                        "processing_timestamp": datetime.now().isoformat(),
                        "content_type": "text/markdown"
                    }
                },
                {
                    "content": "PAN validation involves checking PAN card details against NSDL database for authenticity.",
                    "source": "test_pan_doc.md", 
                    "chunk_id": "chunk_1",
                    "type": "specification",
                    "capability": "PANNSDL",
                    "source_type": "dynamic",
                    "metadata": {
                        "processing_timestamp": datetime.now().isoformat(),
                        "content_type": "text/markdown"
                    }
                },
                {
                    "content": "Lending process requires comprehensive document verification including income proof and credit history.",
                    "source": "test_lending_doc.md",
                    "chunk_id": "chunk_1", 
                    "type": "process",
                    "capability": "LENDING",
                    "source_type": "dynamic",
                    "metadata": {
                        "processing_timestamp": datetime.now().isoformat(),
                        "content_type": "text/markdown"
                    }
                }
            ]
            
            await self.vector_service._add_document_batch(test_docs)
            results["details"].append("✅ Added test documents to vector store")
            results["passed"] += 1
            
            # Test 2: Basic search
            search_results = await self.vector_service.search("eKYC verification", n_results=2)
            if search_results and len(search_results) > 0:
                results["details"].append(f"✅ Basic search returned {len(search_results)} results")
                results["passed"] += 1
            else:
                results["details"].append("❌ Basic search returned no results")
                results["failed"] += 1
            
            # Test 3: Dynamic content search
            dynamic_results = await self.vector_service.search_dynamic_content("PAN validation", n_results=2)
            if dynamic_results and len(dynamic_results) > 0:
                results["details"].append(f"✅ Dynamic content search returned {len(dynamic_results)} results")
                results["passed"] += 1
            else:
                results["details"].append("❌ Dynamic content search returned no results")
                results["failed"] += 1
            
            # Test 4: Capability-specific search
            capability_results = await self.vector_service.search_by_capability("verification", "EKYC", n_results=2)
            if capability_results and len(capability_results) > 0:
                results["details"].append(f"✅ Capability search returned {len(capability_results)} results")
                results["passed"] += 1
            else:
                results["details"].append("❌ Capability search returned no results")
                results["failed"] += 1
            
            # Test 5: Get collection info
            info = self.vector_service.get_collection_info()
            if info.get("count", 0) > 0:
                results["details"].append(f"✅ Vector store contains {info['count']} documents")
                results["passed"] += 1
            else:
                results["details"].append("❌ Vector store appears empty")
                results["failed"] += 1
            
            # Test 6: Dynamic content stats
            dynamic_stats = await self.vector_service.get_dynamic_content_stats()
            if dynamic_stats.get("total_dynamic_chunks", 0) > 0:
                results["details"].append(f"✅ Dynamic content stats: {dynamic_stats['total_dynamic_chunks']} chunks")
                results["passed"] += 1
            else:
                results["details"].append("❌ No dynamic content found in stats")
                results["failed"] += 1
                
        except Exception as e:
            results["details"].append(f"❌ Vector service test error: {e}")
            results["failed"] += 1
        
        return results
    
    async def test_graph_service(self) -> Dict[str, Any]:
        """Test graph service and context repository functionality"""
        print("\n🕸️ Testing Graph Service...")
        results = {"passed": 0, "failed": 0, "details": []}
        
        try:
            # Test 1: Basic Neo4j connection
            connection_test = await self.neo4j_service.test_connection()
            if connection_test:
                results["details"].append("✅ Neo4j connection successful")
                results["passed"] += 1
            else:
                results["details"].append("❌ Neo4j connection failed")
                results["failed"] += 1
                return results
            
            # Test 2: Create test nodes
            test_concept_id = await self.neo4j_service.create_node("Concept", {
                "name": "EKYC_VERIFICATION",
                "description": "Electronic Know Your Customer verification process",
                "keywords": ["ekyc", "verification", "digital", "identity"],
                "capability": "EKYC"
            })
            
            if test_concept_id:
                results["details"].append("✅ Created test concept node")
                results["passed"] += 1
            else:
                results["details"].append("❌ Failed to create test concept node")
                results["failed"] += 1
            
            # Test 3: Create test document node
            test_doc_id = await self.neo4j_service.create_node("Document", {
                "source_identifier": "test_dynamic_doc_123",
                "source_type": "upload",
                "content_preview": "This is a test document about eKYC verification process...",
                "created_at": datetime.now().isoformat(),
                "chunk_count": 3
            })
            
            if test_doc_id:
                results["details"].append("✅ Created test document node")
                results["passed"] += 1
            else:
                results["details"].append("❌ Failed to create test document node")
                results["failed"] += 1
            
            # Test 4: Create relationship
            if test_concept_id and test_doc_id:
                relationship_created = await self.neo4j_service.create_relationship(
                    test_doc_id, test_concept_id, "MENTIONS",
                    {"relevance": 0.9, "context": "document discusses eKYC verification"}
                )
                
                if relationship_created:
                    results["details"].append("✅ Created test relationship")
                    results["passed"] += 1
                else:
                    results["details"].append("❌ Failed to create test relationship")
                    results["failed"] += 1
            
            # Test 5: Search for concepts
            matching_concepts = await self.context_repository.find_matching_concepts(["EKYC", "VERIFICATION"])
            if matching_concepts and len(matching_concepts) > 0:
                results["details"].append(f"✅ Found {len(matching_concepts)} matching concepts")
                results["passed"] += 1
            else:
                results["details"].append("❌ No matching concepts found")
                results["failed"] += 1
            
            # Test 6: Search dynamic content
            dynamic_content = await self.context_repository.search_dynamic_content("eKYC")
            if dynamic_content and len(dynamic_content) > 0:
                results["details"].append(f"✅ Found {len(dynamic_content)} dynamic content items")
                results["passed"] += 1
            else:
                results["details"].append("❌ No dynamic content found")
                results["failed"] += 1
            
            # Test 7: Get database stats
            stats = await self.neo4j_service.get_database_stats()
            if stats.get("total_nodes", 0) > 0:
                results["details"].append(f"✅ Database contains {stats['total_nodes']} nodes, {stats['total_relationships']} relationships")
                results["passed"] += 1
            else:
                results["details"].append("❌ Database appears empty")
                results["failed"] += 1
                
        except Exception as e:
            results["details"].append(f"❌ Graph service test error: {e}")
            results["failed"] += 1
        
        return results
    
    async def test_mem0_service(self) -> Dict[str, Any]:
        """Test mem0 memory management functionality"""
        print("\n🧠 Testing Mem0 Service...")
        results = {"passed": 0, "failed": 0, "details": []}
        
        try:
            # Test 1: Store test context data
            test_context = {
                "capabilities": {
                    "EKYC": {
                        "prompts": {
                            "verification_prompt": "Verify customer identity using eKYC process with Aadhaar and PAN documents.",
                            "validation_prompt": "Validate document authenticity and extract customer information."
                        },
                        "specs": {
                            "api_spec": {
                                "endpoint": "/api/ekyc/verify",
                                "method": "POST",
                                "required_fields": ["aadhaar_number", "pan_number"]
                            }
                        }
                    }
                },
                "common_prompts": {
                    "greeting": "Hello! I'm here to help with your lending and verification needs.",
                    "error_handling": "I apologize for the error. Let me help you resolve this issue."
                }
            }
            
            storage_stats = self.mem0_manager.store_lending_context(test_context)
            if storage_stats["total_stored"] > 0:
                results["details"].append(f"✅ Stored {storage_stats['total_stored']} items in memory")
                results["passed"] += 1
            else:
                results["details"].append("❌ Failed to store context in memory")
                results["failed"] += 1
            
            # Test 2: Retrieve relevant context
            relevant_context = self.mem0_manager.get_relevant_context("eKYC verification process", limit=3)
            if relevant_context and len(relevant_context) > 0:
                results["details"].append(f"✅ Retrieved {len(relevant_context)} relevant context items")
                results["passed"] += 1
            else:
                results["details"].append("❌ No relevant context retrieved")
                results["failed"] += 1
            
            # Test 3: Add conversation
            self.mem0_manager.add_conversation(
                user_message="How does eKYC verification work?",
                assistant_response="eKYC verification is a digital process that uses Aadhaar and PAN documents to verify customer identity.",
                session_id="test_session_123",
                context_used=relevant_context
            )
            results["details"].append("✅ Added test conversation to memory")
            results["passed"] += 1
            
            # Test 4: Get conversation history
            conversation_history = self.mem0_manager.get_conversation_history("test_session_123", limit=2)
            if conversation_history and len(conversation_history) > 0:
                results["details"].append(f"✅ Retrieved {len(conversation_history)} conversation items")
                results["passed"] += 1
            else:
                results["details"].append("❌ No conversation history retrieved")
                results["failed"] += 1
            
            # Test 5: Get memory statistics
            memory_stats = self.mem0_manager.get_memory_stats()
            if memory_stats["total_memories"] > 0:
                results["details"].append(f"✅ Memory contains {memory_stats['total_memories']} items ({memory_stats['memory_system']})")
                results["passed"] += 1
            else:
                results["details"].append("❌ Memory appears empty")
                results["failed"] += 1
                
        except Exception as e:
            results["details"].append(f"❌ Mem0 service test error: {e}")
            results["failed"] += 1
        
        return results
    
    async def test_integration_service(self) -> Dict[str, Any]:
        """Test integration service functionality"""
        print("\n🔗 Testing Integration Service...")
        results = {"passed": 0, "failed": 0, "details": []}
        
        try:
            # Test 1: Basic integrated search
            integrated_results = await self.integration_service.get_integrated_context(
                "eKYC verification process", max_items=5, include_dynamic=True
            )
            
            if integrated_results and len(integrated_results) > 0:
                results["details"].append(f"✅ Integrated search returned {len(integrated_results)} results")
                results["passed"] += 1
                
                # Check if results have fusion scores
                has_fusion_scores = all('fusion_score' in item for item in integrated_results)
                if has_fusion_scores:
                    results["details"].append("✅ All results have fusion scores")
                    results["passed"] += 1
                else:
                    results["details"].append("❌ Some results missing fusion scores")
                    results["failed"] += 1
            else:
                results["details"].append("❌ Integrated search returned no results")
                results["failed"] += 1
            
            # Test 2: Dynamic content only search
            dynamic_only_results = await self.integration_service.search_dynamic_content_only(
                "PAN validation", max_items=3
            )
            
            if dynamic_only_results and len(dynamic_only_results) > 0:
                results["details"].append(f"✅ Dynamic-only search returned {len(dynamic_only_results)} results")
                results["passed"] += 1
            else:
                results["details"].append("❌ Dynamic-only search returned no results")
                results["failed"] += 1
            
            # Test 3: Get integration statistics
            integration_stats = await self.integration_service.get_integration_statistics()
            if "vector_store" in integration_stats and "graph_database" in integration_stats:
                results["details"].append("✅ Integration statistics retrieved successfully")
                results["passed"] += 1
            else:
                results["details"].append("❌ Failed to retrieve integration statistics")
                results["failed"] += 1
            
            # Test 4: Dynamic content overview
            dynamic_overview = await self.integration_service.get_dynamic_content_overview()
            if "integration_summary" in dynamic_overview:
                total_chunks = dynamic_overview["integration_summary"].get("total_dynamic_chunks", 0)
                results["details"].append(f"✅ Dynamic content overview: {total_chunks} chunks")
                results["passed"] += 1
            else:
                results["details"].append("❌ Failed to get dynamic content overview")
                results["failed"] += 1
                
        except Exception as e:
            results["details"].append(f"❌ Integration service test error: {e}")
            results["failed"] += 1
        
        return results
    
    async def test_dynamic_data_flow(self) -> Dict[str, Any]:
        """Test end-to-end dynamic data processing flow"""
        print("\n🔄 Testing Dynamic Data Flow...")
        results = {"passed": 0, "failed": 0, "details": []}
        
        try:
            # Simulate dynamic data ingestion
            dynamic_documents = [
                {
                    "content": "New lending policy: All loan applications must include recent salary slips and bank statements for the last 6 months.",
                    "source": "dynamic_policy_update_2024.pdf",
                    "chunk_id": "policy_chunk_1",
                    "type": "policy",
                    "capability": "LENDING",
                    "source_type": "upload",
                    "metadata": {
                        "processing_timestamp": datetime.now().isoformat(),
                        "content_type": "application/pdf",
                        "upload_session": "test_session_456"
                    }
                },
                {
                    "content": "Updated eKYC guidelines: Video verification is now mandatory for high-value transactions above 5 lakhs.",
                    "source": "ekyc_guidelines_v2.docx",
                    "chunk_id": "guideline_chunk_1", 
                    "type": "guideline",
                    "capability": "EKYC",
                    "source_type": "url",
                    "metadata": {
                        "processing_timestamp": datetime.now().isoformat(),
                        "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "source_url": "https://example.com/ekyc-guidelines"
                    }
                }
            ]
            
            # Test 1: Add dynamic documents to vector store
            await self.vector_service._add_document_batch(dynamic_documents)
            results["details"].append("✅ Added dynamic documents to vector store")
            results["passed"] += 1
            
            # Test 2: Create corresponding graph nodes
            for doc in dynamic_documents:
                doc_node_id = await self.neo4j_service.create_node("Document", {
                    "source_identifier": doc["source"],
                    "source_type": doc["source_type"],
                    "content_preview": doc["content"][:200] + "...",
                    "created_at": datetime.now().isoformat(),
                    "capability": doc["capability"]
                })
                
                if doc_node_id:
                    results["details"].append(f"✅ Created graph node for {doc['source']}")
                    results["passed"] += 1
                else:
                    results["details"].append(f"❌ Failed to create graph node for {doc['source']}")
                    results["failed"] += 1
            
            # Test 3: Store dynamic context in mem0
            dynamic_context = {
                "capabilities": {
                    "LENDING": {
                        "prompts": {
                            "policy_prompt": "Apply the latest lending policy requiring 6 months of financial documents."
                        }
                    },
                    "EKYC": {
                        "prompts": {
                            "video_verification_prompt": "For transactions above 5 lakhs, ensure video verification is completed."
                        }
                    }
                }
            }
            
            mem0_stats = self.mem0_manager.store_lending_context(dynamic_context)
            if mem0_stats["total_stored"] > 0:
                results["details"].append(f"✅ Stored {mem0_stats['total_stored']} dynamic context items in mem0")
                results["passed"] += 1
            else:
                results["details"].append("❌ Failed to store dynamic context in mem0")
                results["failed"] += 1
            
            # Test 4: Test integrated retrieval of dynamic data
            integrated_results = await self.integration_service.get_integrated_context(
                "lending policy bank statements", max_items=3, include_dynamic=True
            )
            
            dynamic_results_found = sum(1 for result in integrated_results if result.get('is_dynamic', False))
            if dynamic_results_found > 0:
                results["details"].append(f"✅ Found {dynamic_results_found} dynamic results in integrated search")
                results["passed"] += 1
            else:
                results["details"].append("❌ No dynamic results found in integrated search")
                results["failed"] += 1
            
            # Test 5: Test mem0 retrieval of dynamic context
            mem0_results = self.mem0_manager.get_relevant_context("video verification high value", limit=2)
            if mem0_results and len(mem0_results) > 0:
                results["details"].append(f"✅ Mem0 retrieved {len(mem0_results)} relevant dynamic context items")
                results["passed"] += 1
            else:
                results["details"].append("❌ Mem0 failed to retrieve dynamic context")
                results["failed"] += 1
                
        except Exception as e:
            results["details"].append(f"❌ Dynamic data flow test error: {e}")
            results["failed"] += 1
        
        return results
    
    async def cleanup_test_data(self):
        """Clean up test data from all services"""
        print("\n🧹 Cleaning up test data...")
        
        try:
            # Clean up vector store test documents
            test_sources = [
                "test_ekyc_doc.md",
                "test_pan_doc.md", 
                "test_lending_doc.md",
                "dynamic_policy_update_2024.pdf",
                "ekyc_guidelines_v2.docx"
            ]
            
            for source in test_sources:
                try:
                    await self.vector_service.delete_documents_by_source(source)
                except:
                    pass  # Ignore errors during cleanup
            
            # Clean up graph database test nodes
            cleanup_queries = [
                "MATCH (n:Concept {name: 'EKYC_VERIFICATION'}) DETACH DELETE n",
                "MATCH (n:Document) WHERE n.source_identifier STARTS WITH 'test_' DETACH DELETE n",
                "MATCH (n:Document) WHERE n.source_identifier IN ['dynamic_policy_update_2024.pdf', 'ekyc_guidelines_v2.docx'] DETACH DELETE n"
            ]
            
            for query in cleanup_queries:
                try:
                    await self.neo4j_service.execute_write_query(query)
                except:
                    pass  # Ignore errors during cleanup
            
            # Clean up mem0 test data
            try:
                self.mem0_manager.clear_memory()
            except:
                pass  # Ignore errors during cleanup
            
            print("✅ Test data cleanup completed")
            
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
    
    async def run_all_tests(self):
        """Run all component tests"""
        print("🚀 Starting Comprehensive Component Testing")
        print("=" * 60)
        
        # Initialize services
        if not await self.initialize_services():
            print("❌ Failed to initialize services. Exiting.")
            return
        
        # Run individual component tests
        test_functions = [
            ("Vector Service", self.test_vector_service),
            ("Graph Service", self.test_graph_service),
            ("Mem0 Service", self.test_mem0_service),
            ("Integration Service", self.test_integration_service),
            ("Dynamic Data Flow", self.test_dynamic_data_flow)
        ]
        
        all_results = {}
        total_passed = 0
        total_failed = 0
        
        for test_name, test_func in test_functions:
            try:
                results = await test_func()
                all_results[test_name] = results
                total_passed += results["passed"]
                total_failed += results["failed"]
                
                # Print test details
                for detail in results["details"]:
                    print(f"   {detail}")
                    
            except Exception as e:
                print(f"❌ {test_name} test failed with exception: {e}")
                all_results[test_name] = {"passed": 0, "failed": 1, "details": [f"Exception: {e}"]}
                total_failed += 1
        
        # Cleanup
        await self.cleanup_test_data()
        
        # Final summary
        print("\n" + "=" * 60)
        print("📋 Component Test Results Summary:")
        print("-" * 40)
        
        for test_name, results in all_results.items():
            passed = results["passed"]
            failed = results["failed"]
            total_tests = passed + failed
            status = "✅ PASSED" if failed == 0 else f"⚠️ PARTIAL ({passed}/{total_tests})" if passed > 0 else "❌ FAILED"
            print(f"   {test_name}: {status}")
        
        print(f"\n🎯 Overall: {total_passed}/{total_passed + total_failed} tests passed")
        
        if total_failed == 0:
            print("🎉 All component tests passed! System is fully functional.")
        elif total_passed > total_failed:
            print("⚠️ Most tests passed, but some issues detected. Check details above.")
        else:
            print("❌ Multiple test failures detected. System may need attention.")
        
        # Close services
        try:
            if self.neo4j_service:
                await self.neo4j_service.close()
        except:
            pass


async def main():
    """Main test execution"""
    tester = ComponentTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())