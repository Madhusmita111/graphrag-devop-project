"""Enterprise GraphRAG Knowledge Engine — FastAPI Application."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.models import (
    IngestRequest, IngestResponse,
    QueryRequest, QueryResponse,
)
from app.graph_store import GraphStore
from app.graph_rag import GraphRAGEngine


# =============================
# CONFIGURATION
# =============================

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")  # FIXED
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


graph_store: GraphStore | None = None
rag_engine: GraphRAGEngine | None = None


# =============================
# LIFECYCLE
# =============================

@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph_store, rag_engine

    try:
        graph_store = GraphStore(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        if graph_store.verify_connection():
            print("Connected to Neo4j")
        else:
            print("Neo4j connection failed")
    except Exception as e:
        print(f"Neo4j error: {e}")
        graph_store = None

    if not GROQ_API_KEY:
        print("WARNING: GROQ API KEY not set")

    if GROQ_API_KEY and graph_store:
        rag_engine = GraphRAGEngine(graph_store=graph_store)
        print("GraphRAG engine ready")
    else:
        rag_engine = None

    yield

    if graph_store:
        graph_store.close()
        print("Neo4j connection closed")


# =============================
# FASTAPI APP
# =============================

app = FastAPI(
    title="GraphRAG Knowledge Engine",
    version="2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================
# HEALTH
# =============================

@app.get("/health")
def health_check():
    neo4j_ok = graph_store.verify_connection() if graph_store else False
    return {
        "status": "healthy" if neo4j_ok else "degraded",
        "neo4j": neo4j_ok,
        "groq": bool(GROQ_API_KEY),
        "engine": rag_engine is not None,
    }


# =============================
# INGEST
# =============================

@app.post("/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest):

    if not rag_engine:
        raise HTTPException(status_code=503, detail="GraphRAG not ready")

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Empty text")

    try:
        return rag_engine.ingest_document(
            text=request.text,
            source_name=request.source_name
        )
    except Exception as e:
        print("error:", e)
        raise HTTPException(status_code=500, detail=str(e))


# =============================
# ASK
# =============================

@app.post("/ask", response_model=QueryResponse)
def ask(request: QueryRequest):

    if not rag_engine:
        raise HTTPException(status_code=503, detail="GraphRAG not ready")

    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Empty query")

    try:
        return rag_engine.ask(request.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================
# BASIC GRAPH STATS
# =============================

@app.get("/graph/stats")
def graph_stats():

    if not graph_store:
        raise HTTPException(status_code=503, detail="Neo4j not connected")

    return graph_store.get_stats()


# =============================
# ENTITY LIST
# =============================

@app.get("/graph/entities")
def list_entities(limit: int = 100):

    if not graph_store:
        raise HTTPException(status_code=503, detail="Neo4j not connected")

    return graph_store.get_all_entities(limit)