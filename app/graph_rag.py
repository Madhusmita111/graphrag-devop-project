"""
GraphRAG Engine — Hybrid (Graph + Semantic Embeddings)
"""

from app.graph_store import GraphStore
from app.retriever import GraphRetriever
from app.entity_extractor import extract_entities
from app.models import IngestResponse, QueryResponse
from app.llm import generate_answer
from app.embedding_store import EmbeddingStore


class GraphRAGEngine:

    def __init__(self, graph_store: GraphStore):
        self.graph_store = graph_store
        self.retriever = GraphRetriever(graph_store)

        #  NEW: semantic memory
        self.embedding_store = EmbeddingStore()

    # ============================
    # INGEST PIPELINE
    # ============================
    def ingest_document(self, text: str, source_name: str = "uploaded_document") -> IngestResponse:

        if not text.strip():
            return IngestResponse(
                message="Empty document",
                entities_created=0,
                relationships_created=0,
                source_name=source_name,
            )

        # 1. Extract entities + relationships
        entities, relationships = extract_entities(text)

        # 2. Store in graph
        entity_count, rel_count = self.graph_store.store_extraction(
            entities, relationships, source_name
        )

        #  3. Store raw text for semantic search
        self.embedding_store.add(text)

        return IngestResponse(
            message=f"Ingested '{source_name}'",
            entities_created=entity_count,
            relationships_created=rel_count,
            source_name=source_name,
        )

    # ============================
    # QUERY PIPELINE
    # ============================
    def ask(self, query: str) -> QueryResponse:

        if not query.strip():
            return QueryResponse(
                answer="Empty query.",
                sources=[],
                subgraph={"context": []}
            )

        # ----------------------------
        # 1. GRAPH RETRIEVAL
        # ----------------------------
        graph_results = self.retriever.retrieve(query)

        context_lines = []
        sources = []

        for record in graph_results:
            n = record["n"]
            m = record["m"]
            r = record["r"]

            line = f"{n['name']} -[{r['type']}]-> {m['name']}"
            context_lines.append(line)

            sources.append({
                "source": n["name"],
                "target": m["name"],
                "relationship": r["type"]
            })

        # ----------------------------
        # 2. SEMANTIC RETRIEVAL 🔥
        # ----------------------------
        semantic_context = self.embedding_store.search(query)

        # ----------------------------
        # 3. COMBINE CONTEXT
        # ----------------------------
        combined_context = context_lines + semantic_context

        if not combined_context:
            return QueryResponse(
                answer="I don't know.",
                sources=[],
                subgraph={"context": []}
            )

        context_text = "\n".join(combined_context[:20])

        # ----------------------------
        # 4. LLM PROMPT (FIXED)
        # ----------------------------
        prompt = f"""
You are an intelligent AI system using a knowledge graph.

Your job:
Answer the question using ONLY the provided context.

Rules:
- Do NOT guess
- Do NOT add external knowledge
- If answer not found, say "I don't know"
- Keep answer clear and short

CONTEXT:
{context_text}

QUESTION:
{query}
"""

        # ----------------------------
        # 5. GENERATE ANSWER
        # ----------------------------
        try:
            answer = generate_answer(prompt).strip()
        except Exception:
            answer = "Error generating answer."

        return QueryResponse(
            answer=answer,
            sources=sources,
            subgraph={"context": combined_context}
        )