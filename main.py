from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from neo4j import GraphDatabase

app = FastAPI(
    title="Enterprise GraphRAG Knowledge Engine",
    description="A Cloud DevOps sample project using GraphRAG",
    version="1.0.0"
)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

driver = None

@app.on_event("startup")
def startup_db_client():
    global driver
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        print("Connected to Neo4j Database")
    except Exception as e:
        print(f"Failed to connect to Neo4j: {e}")
        driver = None

@app.on_event("shutdown")
def shutdown_db_client():
    if driver:
        driver.close()

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
    sources: list[str]

@app.get("/health")
def health_check():
    return {"status": "healthy", "neo4j_connected": driver is not None}

@app.post("/ask", response_model=QueryResponse)
def ask_question(request: QueryRequest):
    if not driver:
        raise HTTPException(status_code=503, detail="Database connection not available")
    
    # In a real GraphRAG application, we would:
    # 1. Use an LLM to convert the natural language query to Cypher.
    # 2. Query the Neo4j database using the Cypher query.
    # 3. Use the LLM to synthesize the results into a human-readable answer.
    
    # For this DevOps project, we return a mock answer to focus on deployment.
    return QueryResponse(
        answer=f"Simulated GraphRAG response for: {request.query}",
        sources=["Document A", "Graph Node B"]
    )
