"""Graph-enhanced retrieval — REAL GraphRAG version"""

import re
from app.graph_store import GraphStore


class GraphRetriever:
    def __init__(self, graph_store: GraphStore):
        self.graph_store = graph_store

    def extract_query_terms(self, query: str):
        stop_words = {
            "what","who","where","when","why","how","is","are","was","were",
            "do","does","did","the","a","an","in","on","at","to","for","of",
            "with","by","from","as","and","or","but","not"
        }

        words = re.findall(r'\b[a-zA-Z]{2,}\b', query)

        terms = [w for w in words if w.lower() not in stop_words]

        bigrams = [
            f"{words[i]} {words[i+1]}"
            for i in range(len(words)-1)
            if words[i].lower() not in stop_words
            and words[i+1].lower() not in stop_words
        ]

        return list(set(terms + bigrams))

    def retrieve(self, query: str):
        terms = self.extract_query_terms(query)

        if not terms:
            return []

        results = []

        for term in terms:
            records = self.graph_store.query_graph(term)
            results.extend(records)

        # Remove duplicates
        unique = []
        seen = set()

        for r in results:
            key = (
                r["n"]["name"],
                r["m"]["name"] if r.get("m") else "",
                r["r"]["type"] if r.get("r") else ""
            )

            if key not in seen:
                seen.add(key)
                unique.append(r)

        return unique[:10]