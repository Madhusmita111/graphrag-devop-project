"""Graph-enhanced retrieval — finds relevant context from the knowledge graph for a query."""

import re
from app.graph_store import GraphStore


class GraphRetriever:
    """Retrieves relevant subgraph context for a natural language query."""

    def __init__(self, graph_store: GraphStore):
        self.graph_store = graph_store

    def extract_query_terms(self, query: str) -> list[str]:
        """Extract meaningful search terms from a natural language query.
        
        Uses simple keyword extraction (stop-word removal).
        For a production system, you'd use NER or embedding-based search.
        """
        stop_words = {
            "what", "who", "where", "when", "why", "how", "is", "are", "was",
            "were", "do", "does", "did", "the", "a", "an", "in", "on", "at",
            "to", "for", "of", "with", "by", "from", "as", "and", "or", "but",
            "not", "this", "that", "it", "its", "be", "been", "being", "have",
            "has", "had", "will", "would", "could", "should", "may", "might",
            "shall", "can", "about", "between", "through", "during", "before",
            "after", "above", "below", "up", "down", "out", "off", "over",
            "under", "again", "further", "then", "once", "tell", "me", "all",
            "which", "there", "their", "them", "they", "these", "those",
        }

        # Tokenize and filter
        words = re.findall(r'\b[a-zA-Z]{2,}\b', query)
        terms = [w for w in words if w.lower() not in stop_words]

        # Also try multi-word phrases (bigrams)
        bigrams = []
        for i in range(len(words) - 1):
            if words[i].lower() not in stop_words or words[i + 1].lower() not in stop_words:
                bigrams.append(f"{words[i]} {words[i+1]}")

        # Return individual terms + bigrams for broader matching
        return terms + bigrams

    def retrieve(self, query: str) -> dict:
        """Main retrieval function: extract terms → search graph → return context.
        
        Returns a dict with 'nodes' and 'edges' representing the relevant subgraph.
        """
        terms = self.extract_query_terms(query)

        if not terms:
            return {"nodes": [], "edges": []}

        context = self.graph_store.get_relevant_context(terms, limit=15)
        return context
