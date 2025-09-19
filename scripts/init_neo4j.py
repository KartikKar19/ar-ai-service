"""
Script to initialize Neo4j with sample data for AR-Learn
"""
import asyncio
from neo4j import AsyncGraphDatabase
import os
from dotenv import load_dotenv

async def init_neo4j():
    load_dotenv(".env")
    
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    
    async with driver.session() as session:
        # Clear existing data
        await session.run("MATCH (n) DETACH DELETE n")
        
        # Create Jet Engine Components
        await session.run("""
        CREATE (compressor:Component {
            id: 'compressor',
            name: 'Compressor',
            type: 'compressor',
            description: 'Compresses incoming air to increase pressure',
            position: 'front',
            function: 'air_compression'
        })
        """)
        
        await session.run("""
        CREATE (combustion:Component {
            id: 'combustion_chamber',
            name: 'Combustion Chamber',
            type: 'combustion_chamber',
            description: 'Where fuel is mixed with compressed air and ignited',
            position: 'middle',
            function: 'fuel_burning'
        })
        """)
        
        await session.run("""
        CREATE (turbine:Component {
            id: 'turbine',
            name: 'Turbine',
            type: 'turbine',
            description: 'Extracts energy from hot gases to drive the compressor',
            position: 'rear',
            function: 'energy_extraction'
        })
        """)
        
        # Create relationships
        await session.run("""
        MATCH (c:Component {id: 'compressor'}), (cc:Component {id: 'combustion_chamber'})
        CREATE (c)-[:CONNECTS_TO {flow: 'compressed_air'}]->(cc)
        """)
        
        await session.run("""
        MATCH (cc:Component {id: 'combustion_chamber'}), (t:Component {id: 'turbine'})
        CREATE (cc)-[:CONNECTS_TO {flow: 'hot_gases'}]->(t)
        """)
        
        await session.run("""
        MATCH (t:Component {id: 'turbine'}), (c:Component {id: 'compressor'})
        CREATE (t)-[:DRIVES {mechanism: 'shaft'}]->(c)
        """)
        
        # Create Procedures
        await session.run("""
        CREATE (proc:Procedure {
            id: 'jet_engine_basics',
            name: 'Jet Engine Component Identification',
            subject: 'Engineering',
            difficulty: 'Beginner'
        })
        """)
        
        # Create Steps
        await session.run("""
        MATCH (proc:Procedure {id: 'jet_engine_basics'})
        CREATE (step1:Step {
            id: 'step_1',
            title: 'Identify the Compressor',
            description: 'Locate and select the compressor stage',
            instruction: 'Look for the fan-like component at the front',
            expected_action: 'select_compressor',
            order: 1,
            validation_rules: 'component_type:compressor'
        })
        CREATE (step2:Step {
            id: 'step_2',
            title: 'Identify the Combustion Chamber',
            description: 'Locate the combustion chamber',
            instruction: 'Find where fuel is burned',
            expected_action: 'select_combustion_chamber',
            order: 2,
            validation_rules: 'component_type:combustion_chamber'
        })
        CREATE (step3:Step {
            id: 'step_3',
            title: 'Identify the Turbine',
            description: 'Locate the turbine',
            instruction: 'Find the energy extraction component',
            expected_action: 'select_turbine',
            order: 3,
            validation_rules: 'component_type:turbine'
        })
        CREATE (proc)-[:HAS_STEP]->(step1)
        CREATE (proc)-[:HAS_STEP]->(step2)
        CREATE (proc)-[:HAS_STEP]->(step3)
        """)
        
        print("Neo4j initialized with sample data!")
    
    await driver.close()

if __name__ == "__main__":
    asyncio.run(init_neo4j())