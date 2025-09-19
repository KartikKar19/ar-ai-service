import time
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import logging

from app.core.config import settings
from app.infra.db.chroma_client import chroma_client
from app.infra.db.neo4j_client import neo4j_client
from app.domain.dtos.query import QueryRequest, QueryResponse, QueryType

logger = logging.getLogger(__name__)

class RAGEngine:
    def __init__(self):
        self.llm = ChatOpenAI(
            openai_api_key=settings.OPENAI_API_KEY,
            model_name=settings.OPENAI_MODEL,
            temperature=0.1
        )
    
    async def query(self, request: QueryRequest, user_id: str) -> QueryResponse:
        """Main RAG query processing"""
        start_time = time.time()
        
        try:
            # Step 1: Retrieve from both sources
            vector_results = await self._retrieve_from_vector_store(
                request.question, 
                request.max_results,
                request.scene
            )
            
            graph_results = await self._retrieve_from_knowledge_graph(
                request.question,
                request.max_results
            )
            
            # Step 2: Combine and rank results
            combined_context = self._combine_contexts(vector_results, graph_results)
            
            # Step 3: Generate response using LLM
            answer = await self._generate_answer(
                request.question,
                combined_context,
                request.query_type
            )
            
            # Step 4: Calculate confidence and prepare sources
            confidence = self._calculate_confidence(vector_results, graph_results)
            sources = self._prepare_sources(vector_results, graph_results)
            
            processing_time = time.time() - start_time
            
            return QueryResponse(
                answer=answer,
                confidence=confidence,
                sources=sources,
                query_type=request.query_type,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error in RAG query: {e}")
            raise
    
    async def _retrieve_from_vector_store(
        self, 
        query: str, 
        max_results: int,
        scene: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieve relevant chunks from ChromaDB"""
        try:
            where_clause = None
            if scene:
                where_clause = {"subject": scene}
            
            results = await chroma_client.search_similar(
                query_text=query,
                n_results=max_results,
                where=where_clause
            )
            
            return {
                "type": "vector",
                "results": results,
                "count": len(results.get("documents", []))
            }
            
        except Exception as e:
            logger.error(f"Error retrieving from vector store: {e}")
            return {"type": "vector", "results": {}, "count": 0}
    
    async def _retrieve_from_knowledge_graph(
        self, 
        query: str, 
        max_results: int
    ) -> Dict[str, Any]:
        """Retrieve structured facts from Neo4j"""
        try:
            # Check if Neo4j driver is available
            if not neo4j_client.driver:
                logger.warning("Neo4j driver not available, skipping graph retrieval")
                return {"type": "graph", "results": [], "count": 0}
                
            facts = await neo4j_client.get_structured_facts(query, max_results)
            
            return {
                "type": "graph",
                "results": facts,
                "count": len(facts)
            }
            
        except Exception as e:
            logger.error(f"Error retrieving from knowledge graph: {e}")
            return {"type": "graph", "results": [], "count": 0}
    
    def _combine_contexts(
        self, 
        vector_results: Dict[str, Any], 
        graph_results: Dict[str, Any]
    ) -> str:
        """Combine contexts from both retrieval sources"""
        context_parts = []
        
        # Add vector store results
        if vector_results["count"] > 0:
            context_parts.append("=== DOCUMENT EXCERPTS ===")
            documents = vector_results["results"].get("documents", [])
            metadatas = vector_results["results"].get("metadatas", [])
            
            for i, doc in enumerate(documents[:3]):  # Top 3 results
                metadata = metadatas[i] if i < len(metadatas) else {}
                doc_id = metadata.get("document_id", "unknown")
                context_parts.append(f"[Document {doc_id}]: {doc}")
        
        # Add knowledge graph results
        if graph_results["count"] > 0:
            context_parts.append("\n=== STRUCTURED KNOWLEDGE ===")
            facts = graph_results["results"]
            
            for fact in facts[:3]:  # Top 3 facts
                if fact.get("node") and fact.get("relationship"):
                    node_info = str(fact["node"])
                    rel_info = fact["relationship"]["type"]
                    connected_info = str(fact.get("connected_node", ""))
                    context_parts.append(f"Fact: {node_info} {rel_info} {connected_info}")
        
        return "\n".join(context_parts)
    
    async def _generate_answer(
        self, 
        question: str, 
        context: str, 
        query_type: QueryType
    ) -> str:
        """Generate answer using LLM with retrieved context"""
        
        # Different system prompts based on query type
        if query_type == QueryType.PROCEDURAL:
            system_prompt = """You are an AI tutor specializing in step-by-step procedural guidance. 
            Use the provided context to give clear, sequential instructions. 
            If the context contains procedural steps, present them in order.
            Be encouraging and provide helpful hints when appropriate."""
        
        elif query_type == QueryType.ASSESSMENT:
            system_prompt = """You are an AI assessment assistant. 
            Use the provided context to create educational questions or evaluate understanding.
            Focus on key concepts and learning objectives from the context."""
        
        else:  # GENERAL
            system_prompt = """You are an AI tutor for AR-Learn, an educational platform. 
            Use the provided context to answer questions accurately and educationally.
            Explain concepts clearly and relate them to practical applications when possible.
            If you're not certain about something, say so rather than guessing."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""
Context Information:
{context}

Question: {question}

Please provide a comprehensive answer based on the context provided. If the context doesn't contain enough information to fully answer the question, acknowledge this and provide what information you can.
""")
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return "I apologize, but I'm having trouble generating a response right now. Please try again."
    
    def _calculate_confidence(
        self, 
        vector_results: Dict[str, Any], 
        graph_results: Dict[str, Any]
    ) -> float:
        """Calculate confidence score based on retrieval results"""
        vector_count = vector_results["count"]
        graph_count = graph_results["count"]
        
        # Simple confidence calculation
        base_confidence = 0.3
        
        if vector_count > 0:
            base_confidence += 0.4
        
        if graph_count > 0:
            base_confidence += 0.3
        
        # Adjust based on result quality (distances for vector results)
        if vector_results["results"].get("distances"):
            avg_distance = sum(vector_results["results"]["distances"]) / len(vector_results["results"]["distances"])
            # Lower distance = higher confidence
            distance_bonus = max(0, (1.0 - avg_distance) * 0.2)
            base_confidence += distance_bonus
        
        return min(1.0, base_confidence)
    
    def _prepare_sources(
        self, 
        vector_results: Dict[str, Any], 
        graph_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Prepare source information for response"""
        sources = []
        
        # Add vector sources
        if vector_results["count"] > 0:
            metadatas = vector_results["results"].get("metadatas", [])
            distances = vector_results["results"].get("distances", [])
            
            for i, metadata in enumerate(metadatas):
                source = {
                    "type": "document",
                    "document_id": metadata.get("document_id"),
                    "chunk_index": metadata.get("chunk_index"),
                    "relevance_score": 1.0 - distances[i] if i < len(distances) else 0.5
                }
                sources.append(source)
        
        # Add graph sources
        if graph_results["count"] > 0:
            for fact in graph_results["results"]:
                source = {
                    "type": "knowledge_graph",
                    "node_info": str(fact.get("node", {})),
                    "relationship": fact.get("relationship", {}).get("type", ""),
                    "relevance_score": 0.8  # Fixed score for graph results
                }
                sources.append(source)
        
        return sources

# Global RAG engine instance
rag_engine = RAGEngine()