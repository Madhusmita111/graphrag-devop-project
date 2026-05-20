import os
import json
import urllib.request
import numpy as np

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


class EmbeddingStore:

    def __init__(self):
        self.texts = []
        self.vectors = []

    def get_embedding(self, text: str):
        url = "https://api.groq.com/openai/v1/embeddings"

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        data = json.dumps({
            "model": "text-embedding-3-small",
            "input": text
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers)

        with urllib.request.urlopen(req) as res:
            result = json.loads(res.read().decode())

        return np.array(result["data"][0]["embedding"])

    def add(self, text):
        vec = self.get_embedding(text)
        self.texts.append(text)
        self.vectors.append(vec)

    def search(self, query, top_k=5):
        query_vec = self.get_embedding(query)

        scores = []
        for i, vec in enumerate(self.vectors):
            sim = np.dot(query_vec, vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(vec)
            )
            scores.append((sim, self.texts[i]))

        scores.sort(reverse=True)
        return [t for _, t in scores[:top_k]]