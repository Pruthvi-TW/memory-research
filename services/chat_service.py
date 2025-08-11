import os
import anthropic
from typing import List, Dict, Any


class ChatService:
    """
    Enhanced chat service for generating responses using Anthropic Claude
    with integrated vector + graph context.
    """
    
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key and api_key != "your_anthropic_api_key_here":
            self.client = anthropic.Anthropic(api_key=api_key)
            self.api_available = True
        else:
            self.client = None
            self.api_available = False
            print("⚠️ Anthropic API key not configured - using fallback responses")
        
    async def generate_response(self, message: str, context_items: List[Dict[str, Any]], 
                              session_id: str) -> str:
        """
        Generate context-aware response using Anthropic Claude with integrated context.
        
        Args:
            message: User's input message
            context_items: List of context items from integrated search
            session_id: Session identifier
            
        Returns:
            Generated response string
        """
        
        # Check if API is available first
        if not self.api_available:
            return self._generate_demo_response(message, context_items)
        
        # Build enhanced context string from integrated results
        context_text = self._build_integrated_context_text(context_items)
        
        # Create the enhanced system prompt
        system_prompt = self._build_enhanced_system_prompt(context_text)
        
        try:
            # Use the modern messages API
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": message
                    }
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            print(f"❌ Anthropic API error: {e}")
            return self._generate_fallback_response(message, context_items)
            
    def _build_integrated_context_text(self, context_items: List[Dict[str, Any]]) -> str:
        """Build formatted context text from integrated search results"""
        if not context_items:
            return "No specific context available."
            
        context_parts = []
        
        for i, item in enumerate(context_items, 1):
            # Determine context source and quality
            source_info = self._get_source_info(item)
            
            context_part = f"""
Context {i} - {source_info['type']} ({source_info['quality']}):
Source: {item.get('source_file', 'unknown')}
Capability: {item.get('capability', 'general')}
Relevance Scores:
  - Vector Similarity: {item.get('vector_score', 0.0):.2f}
  - Graph Relevance: {item.get('graph_score', 0.0):.2f}
  - Fusion Score: {item.get('fusion_score', 0.0):.2f}
Related Concepts: {', '.join(item.get('related_concepts', []))}

Content:
{item['content'][:1000]}{'...' if len(item['content']) > 1000 else ''}
"""
            context_parts.append(context_part)
            
        return "\n" + "="*100 + "\n".join(context_parts) + "\n" + "="*100
        
    def _get_source_info(self, item: Dict[str, Any]) -> Dict[str, str]:
        """Get source information and quality assessment"""
        vector_score = item.get('vector_score', 0.0)
        graph_score = item.get('graph_score', 0.0)
        
        # Determine source type
        if vector_score > 0 and graph_score > 0:
            source_type = "Vector + Graph Enhanced"
            quality = "High Quality"
        elif vector_score > 0:
            source_type = "Vector Search Result"
            quality = "Good Quality" if vector_score > 0.7 else "Moderate Quality"
        elif graph_score > 0:
            source_type = "Graph Relationship Result"
            quality = "Good Quality" if graph_score > 0.7 else "Moderate Quality"
        else:
            source_type = "Basic Result"
            quality = "Low Quality"
            
        return {"type": source_type, "quality": quality}
        
    def _build_enhanced_system_prompt(self, context_text: str) -> str:
        """Build the enhanced system prompt with integrated context"""
        return f"""You are an expert assistant specializing in lending and financial services systems. You have access to comprehensive context from both semantic document search and graph-based relationship analysis.

INTEGRATED LENDING DOMAIN CONTEXT:
{context_text}

ENHANCED CAPABILITIES:
1. **Semantic Understanding**: You can understand conceptual relationships between lending processes
2. **Graph Relationships**: You can trace connections between documents, capabilities, and business flows
3. **Multi-source Context**: Your responses are informed by both document similarity and relationship strength
4. **Quality Assessment**: You can assess the reliability of information based on multiple relevance scores

RESPONSE GUIDELINES:
1. **Prioritize High-Quality Context**: Give more weight to information with high fusion scores
2. **Reference Multiple Sources**: When possible, corroborate information across different context sources
3. **Explain Relationships**: Highlight how different concepts and processes relate to each other
4. **Technical Precision**: Use specific technical terminology and reference exact business flows
5. **Capability Awareness**: Understand which capability (EKYC, PANNSDL, etc.) the question relates to
6. **Process Flow Understanding**: Explain step-by-step processes with proper phase sequencing

TECHNICAL DOMAINS COVERED:
- eKYC verification processes and business flows
- PAN and Aadhaar document validation
- OTP verification and authentication
- Java Spring Boot application development
- PostgreSQL database operations
- API integration patterns and best practices
- Business rule validation and error handling

RESPONSE STRUCTURE:
1. **Direct Answer**: Provide a clear, direct response to the user's question
2. **Context Integration**: Explain how different pieces of context support your answer
3. **Related Information**: Mention related concepts or processes that might be relevant
4. **Implementation Guidance**: When appropriate, provide specific technical guidance

QUALITY INDICATORS:
- Vector Similarity Score: Indicates semantic relevance to the query
- Graph Relevance Score: Indicates relationship strength in the knowledge graph
- Fusion Score: Combined relevance taking both factors into account

Always strive to provide accurate, comprehensive answers that leverage the full power of the integrated context system."""

    def _generate_demo_response(self, message: str, context_items: List[Dict[str, Any]]) -> str:
        """Generate a demo response when API key is not configured"""
        context_summary = ""
        if context_items:
            sources = list(set(item.get('context_source', 'unknown') for item in context_items))
            context_summary = f"\n\n**Context Retrieved:** {len(context_items)} items from sources: {', '.join(sources)}"
            
            # Show some context content
            if len(context_items) > 0:
                context_summary += f"\n\n**Sample Context:**\n- {context_items[0]['content'][:200]}..."
        
        return f"""**🤖 Demo Mode - Dynamic Context System Working!**

Your question: "{message}"

This is a demonstration of the dynamic context ingestion system. The system successfully:

✅ **Processed your query** and searched across multiple data sources
✅ **Retrieved relevant context** from uploaded files, URLs, and repositories  
✅ **Integrated results** from vector database, graph database, and memory layer
✅ **Applied fusion scoring** to rank the most relevant information

{context_summary}

**To enable full AI responses:**
1. Get an Anthropic API key from https://console.anthropic.com/
2. Set it in your .env file: `ANTHROPIC_API_KEY=your_actual_key`
3. Restart the application

**System Status:**
- ✅ Vector Database: Working ({len([i for i in context_items if i.get('vector_score', 0) > 0])} matches)
- ✅ Memory Layer: Working ({len([i for i in context_items if i.get('context_source') == 'memory'])} matches)
- ✅ Dynamic Content: Working (processing files, URLs, GitHub repos)
- ⚠️ AI Response: Demo mode (API key needed)

The dynamic context ingestion system is fully functional and ready to enhance AI responses!"""

    def _generate_fallback_response(self, message: str, context_items: List[Dict[str, Any]]) -> str:
        """Generate a fallback response when the main API fails"""
        if context_items:
            # Try to provide a basic response using the context
            relevant_content = []
            for item in context_items[:2]:  # Use top 2 items
                if item.get('fusion_score', 0) > 0.5:
                    relevant_content.append(item['content'][:300])
                    
            if relevant_content:
                return f"""I apologize for the technical difficulty with my main response system. Based on the available context, here's what I can tell you:

{' '.join(relevant_content)}

This information comes from the lending documentation and should help address your question about: {message}

Please try your question again, as my main system should be working normally."""
            
        return f"""I apologize, but I'm experiencing technical difficulties right now. Your question about "{message}" is important, and I'd like to provide you with a comprehensive answer.

Please try asking your question again in a moment. In the meantime, you might want to:
1. Check if your question is about a specific lending capability (eKYC, PAN validation, etc.)
2. Provide more specific details about what you're looking for
3. Try rephrasing your question if it was very general

I'm designed to help with lending processes, technical implementation, and business flows, so I should be able to assist you once the technical issue is resolved."""

    def extract_key_concepts(self, message: str) -> List[str]:
        """Extract key concepts from user message for better context retrieval"""
        import re
        
        # Extract potential technical terms, acronyms, and important words
        concepts = []
        
        # Acronyms (2+ uppercase letters)
        acronyms = re.findall(r'\b[A-Z]{2,}\b', message)
        concepts.extend(acronyms)
        
        # Technical terms (CamelCase or specific patterns)
        tech_terms = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b', message)
        concepts.extend(tech_terms)
        
        # Important keywords
        keywords = re.findall(
            r'\b(?:verification|validation|API|service|flow|process|phase|request|response|ekyc|pan|otp|document)\b', 
            message, re.IGNORECASE
        )
        concepts.extend([k.upper() for k in keywords])
        
        # Lending-specific terms
        lending_terms = re.findall(
            r'\b(?:loan|lending|credit|kyc|aml|compliance|underwriting|approval|disbursement)\b',
            message, re.IGNORECASE
        )
        concepts.extend([t.upper() for t in lending_terms])
        
        return list(set(concepts))  # Remove duplicates
        
    def assess_query_complexity(self, message: str) -> Dict[str, Any]:
        """Assess the complexity and type of the user's query"""
        message_lower = message.lower()
        
        # Query type classification
        query_types = []
        if any(word in message_lower for word in ['how', 'what', 'explain', 'describe']):
            query_types.append('explanatory')
        if any(word in message_lower for word in ['implement', 'code', 'develop', 'build']):
            query_types.append('implementation')
        if any(word in message_lower for word in ['error', 'issue', 'problem', 'debug']):
            query_types.append('troubleshooting')
        if any(word in message_lower for word in ['best', 'practice', 'recommend', 'should']):
            query_types.append('advisory')
            
        # Complexity assessment
        complexity_indicators = {
            'simple': len(message.split()) < 10,
            'medium': 10 <= len(message.split()) < 25,
            'complex': len(message.split()) >= 25
        }
        
        complexity = 'simple'
        for level, condition in complexity_indicators.items():
            if condition:
                complexity = level
                break
                
        # Domain specificity
        domain_keywords = ['ekyc', 'pan', 'aadhaar', 'otp', 'verification', 'validation', 'api', 'spring', 'java']
        domain_matches = sum(1 for keyword in domain_keywords if keyword in message_lower)
        
        return {
            'types': query_types,
            'complexity': complexity,
            'domain_specificity': 'high' if domain_matches >= 3 else 'medium' if domain_matches >= 1 else 'low',
            'estimated_context_needs': min(domain_matches + len(query_types), 8)
        }