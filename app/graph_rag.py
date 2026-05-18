"""Core GraphRAG orchestrator — ties together extraction, storage, retrieval, and generation."""

from app.entity_extractor import EntityExtractor
from app.graph_store import GraphStore
from app.retriever import GraphRetriever
from app.models import IngestResponse, QueryResponse


class GraphRAGEngine:
    """Main engine that orchestrates the full GraphRAG pipeline."""

    def __init__(self, graph_store: GraphStore, extractor: EntityExtractor):
        self.graph_store = graph_store
        self.extractor = extractor
        self.retriever = GraphRetriever(graph_store)

    def ingest_document(self, text: str, source_name: str = "uploaded_document") -> IngestResponse:
        """Full ingestion pipeline: text → extract → store in graph.
        
        1. Chunk the document
        2. Extract entities and relationships using LLM
        3. Store them in Neo4j
        """
        # Extract entities and relationships
        extraction = self.extractor.extract_from_document(text)

        # Store in Neo4j
        entity_count, rel_count = self.graph_store.store_extraction(
            entities=extraction.entities,
            relationships=extraction.relationships,
            source_name=source_name,
        )

        return IngestResponse(
            message=f"Successfully ingested '{source_name}'. Extracted {entity_count} entities and {rel_count} relationships.",
            entities_created=entity_count,
            relationships_created=rel_count,
            source_name=source_name,
        )

    def ask(self, query: str) -> QueryResponse:
        """Full QA pipeline: query → retrieve graph context → generate answer.
        
        1. Extract search terms from the query
        2. Find relevant entities and their neighbourhood in the graph
        3. Use LLM to generate an answer grounded in graph context
        """
        # Retrieve relevant subgraph
        context = self.retriever.retrieve(query)

        # Generate answer using LLM + graph context
        answer = self.extractor.generate_answer(query, context)

        # Format sources from the subgraph
        sources = []
        for node in context.get("nodes", []):
            sources.append({
                "entity": node["name"],
                "type": node.get("entity_type", "Unknown"),
                "description": node.get("description", ""),
            })

        return QueryResponse(
            answer=answer,
            sources=sources,
            subgraph=context,
        )
