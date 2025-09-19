from neo4j import AsyncGraphDatabase
from typing import List, Dict, Any, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class Neo4jClient:
    def __init__(self):
        self.driver = None
    
    async def connect(self):
        self.driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        # Test connection
        async with self.driver.session() as session:
            await session.run("RETURN 1")
        logger.info("Connected to Neo4j")
    
    async def close(self):
        if self.driver:
            await self.driver.close()
    
    async def get_structured_facts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve structured facts from knowledge graph"""
        async with self.driver.session() as session:
            # Simple text search across nodes and relationships
            cypher = """
            MATCH (n)
            WHERE toLower(toString(n)) CONTAINS toLower($query)
            OPTIONAL MATCH (n)-[r]-(m)
            RETURN n, r, m
            LIMIT $limit
            """
            result = await session.run(cypher, query=query, limit=limit)
            
            facts = []
            async for record in result:
                node = record.get("n")
                rel = record.get("r")
                connected = record.get("m")
                
                fact = {
                    "node": dict(node) if node else None,
                    "relationship": {
                        "type": rel.type,
                        "properties": dict(rel)
                    } if rel else None,
                    "connected_node": dict(connected) if connected else None
                }
                facts.append(fact)
            
            return facts
    
    async def get_procedure_steps(self, procedure_name: str) -> List[Dict[str, Any]]:
        """Get procedural steps from knowledge graph"""
        async with self.driver.session() as session:
            cypher = """
            MATCH (p:Procedure {name: $procedure_name})-[:HAS_STEP]->(s:Step)
            RETURN s
            ORDER BY s.order
            """
            result = await session.run(cypher, procedure_name=procedure_name)
            
            steps = []
            async for record in result:
                step = dict(record["s"])
                steps.append(step)
            
            return steps
    
    async def validate_step_action(self, step_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user action against expected step behavior"""
        async with self.driver.session() as session:
            cypher = """
            MATCH (s:Step {id: $step_id})
            RETURN s.validation_rules as rules, s.expected_action as expected
            """
            result = await session.run(cypher, step_id=step_id)
            record = await result.single()
            
            if not record:
                return {"valid": False, "message": "Step not found"}
            
            # Simple validation logic - can be enhanced
            expected = record["expected"]
            rules = record["rules"]
            
            # Basic validation - check if action matches expected pattern
            is_valid = action.get("type") == expected.get("type")
            
            return {
                "valid": is_valid,
                "message": "Correct action!" if is_valid else "Try again. Look for the correct component.",
                "expected": expected,
                "rules": rules
            }

# Global client instance
neo4j_client = Neo4jClient()