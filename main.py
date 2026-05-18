"""Enterprise GraphRAG Knowledge Engine — FastAPI Application."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app.models import (
    IngestRequest, IngestResponse,
    QueryRequest, QueryResponse,
    GraphStats,
)
from app.graph_store import GraphStore
from app.entity_extractor import EntityExtractor
from app.graph_rag import GraphRAGEngine


# ── Configuration ──────────────────────────────────────────────────

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


# ── App Lifecycle ──────────────────────────────────────────────────

graph_store: GraphStore | None = None
rag_engine: GraphRAGEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    global graph_store, rag_engine

    # Startup
    try:
        graph_store = GraphStore(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        if graph_store.verify_connection():
            print("✅ Connected to Neo4j")
        else:
            print("⚠️  Neo4j connection could not be verified")
    except Exception as e:
        print(f"❌ Failed to connect to Neo4j: {e}")
        graph_store = None

    if GROQ_API_KEY and graph_store:
        extractor = EntityExtractor(api_key=GROQ_API_KEY)
        rag_engine = GraphRAGEngine(graph_store=graph_store, extractor=extractor)
        print("✅ GraphRAG engine initialised with Groq")
    elif not GROQ_API_KEY:
        print("⚠️  GROQ_API_KEY not set — /ingest and /ask will not work")
    
    yield

    # Shutdown
    if graph_store:
        graph_store.close()
        print("🔌 Neo4j connection closed")


# ── FastAPI App ────────────────────────────────────────────────────

app = FastAPI(
    title="Enterprise GraphRAG Knowledge Engine",
    description=(
        "A production-grade GraphRAG system that ingests documents, "
        "builds a knowledge graph in Neo4j, and answers questions "
        "using graph-enhanced retrieval with Groq API (Llama 3)."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ─────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check():
    """Health check — reports Neo4j and Groq status."""
    neo4j_ok = graph_store.verify_connection() if graph_store else False
    return {
        "status": "healthy" if neo4j_ok else "degraded",
        "neo4j_connected": neo4j_ok,
        "groq_configured": bool(GROQ_API_KEY),
        "rag_engine_ready": rag_engine is not None,
    }


# ── Ingestion ──────────────────────────────────────────────────────

@app.post("/ingest", response_model=IngestResponse, tags=["GraphRAG"])
def ingest_document(request: IngestRequest):
    """Ingest a document: extract entities & relationships → store in Neo4j.
    
    The LLM analyses the text, identifies entities (people, orgs, technologies, etc.)
    and their relationships, then stores them as nodes and edges in the knowledge graph.
    """
    if not rag_engine:
        raise HTTPException(
            status_code=503,
            detail="GraphRAG engine not available. Check GROQ_API_KEY and Neo4j connection.",
        )

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    try:
        result = rag_engine.ingest_document(
            text=request.text,
            source_name=request.source_name,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")


# ── Question Answering ─────────────────────────────────────────────

@app.post("/ask", response_model=QueryResponse, tags=["GraphRAG"])
def ask_question(request: QueryRequest):
    """Ask a question — retrieves relevant graph context and generates an answer.
    
    The system:
    1. Extracts search terms from your question
    2. Finds relevant entities and relationships in the knowledge graph
    3. Uses the graph context to generate a grounded answer via LLM
    """
    if not rag_engine:
        raise HTTPException(
            status_code=503,
            detail="GraphRAG engine not available. Check GROQ_API_KEY and Neo4j connection.",
        )

    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        result = rag_engine.ask(query=request.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")


# ── Graph Exploration ──────────────────────────────────────────────

@app.get("/graph/stats", response_model=GraphStats, tags=["Knowledge Graph"])
def graph_stats():
    """Get statistics about the knowledge graph (entity/relationship counts by type)."""
    if not graph_store or not graph_store.verify_connection():
        raise HTTPException(status_code=503, detail="Neo4j not connected.")

    stats = graph_store.get_stats()
    return GraphStats(**stats)


@app.get("/graph/entities", tags=["Knowledge Graph"])
def list_entities(limit: int = 100):
    """List all entities in the knowledge graph."""
    if not graph_store or not graph_store.verify_connection():
        raise HTTPException(status_code=503, detail="Neo4j not connected.")

    return graph_store.get_all_entities(limit=limit)


@app.get("/graph/search/{term}", tags=["Knowledge Graph"])
def search_entities(term: str, limit: int = 20):
    """Search entities by name (case-insensitive partial match)."""
    if not graph_store or not graph_store.verify_connection():
        raise HTTPException(status_code=503, detail="Neo4j not connected.")

    return graph_store.search_entities(term=term, limit=limit)


@app.get("/graph/entity/{name}", tags=["Knowledge Graph"])
def get_entity_context(name: str):
    """Get an entity and its connected neighbourhood (subgraph)."""
    if not graph_store or not graph_store.verify_connection():
        raise HTTPException(status_code=503, detail="Neo4j not connected.")

    context = graph_store.get_entity_context(entity_name=name)
    if not context["nodes"]:
        raise HTTPException(status_code=404, detail=f"Entity '{name}' not found.")

    return context
