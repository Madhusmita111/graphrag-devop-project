"""LLM-based entity and relationship extraction using Groq API."""

import json
import re
import urllib.request
from app.models import Entity, Relationship, ExtractionResult


# ── Prompts ────────────────────────────────────────────────────────

EXTRACTION_PROMPT = """You are an expert knowledge graph engineer. Analyse the following text and extract:

1. **Entities** — people, organisations, technologies, concepts, locations, events
2. **Relationships** — how the entities relate to each other

Respond ONLY with valid JSON in this exact format (no markdown, no explanation):
{{
  "entities": [
    {{"name": "...", "entity_type": "Person|Organization|Technology|Concept|Location|Event", "description": "..."}}
  ],
  "relationships": [
    {{"source": "...", "target": "...", "relation_type": "WORKS_AT|USES|PART_OF|CREATED_BY|RELATED_TO|LOCATED_IN|...", "description": "..."}}
  ]
}}

Rules:
- Use UPPER_SNAKE_CASE for relation_type (e.g. WORKS_AT, FOUNDED_BY)
- Entity names should be capitalised properly
- Every relationship source and target MUST match an entity name exactly
- Extract ALL meaningful entities and relationships, not just obvious ones
- Be thorough but avoid duplicates

TEXT:
{text}
"""

QA_PROMPT = """You are a knowledgeable AI assistant. Answer the user's question using ONLY the provided knowledge graph context.

KNOWLEDGE GRAPH CONTEXT:
{context}

QUESTION: {question}

Instructions:
- Answer based on the graph context provided
- If the context doesn't contain enough information, say so honestly
- Reference specific entities and relationships from the context
- Be concise but thorough
"""


class EntityExtractor:
    """Uses Groq API (Llama 3) to extract entities and relationships from text."""

    def __init__(self, api_key: str, model_name: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model_name = model_name

    def _call_groq(self, prompt: str) -> str:
        """Call Groq API using standard urllib.request."""
        req_data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }
        # Request JSON mode if it's the extraction prompt
        if "JSON" in prompt:
            req_data["response_format"] = {"type": "json_object"}

        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps(req_data).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                res = json.loads(response.read().decode("utf-8"))
                return res["choices"][0]["message"]["content"]
        except Exception as e:
            if hasattr(e, 'read'):
                error_details = e.read().decode("utf-8")
                raise RuntimeError(f"Groq API call failed: {error_details}") from e
            raise RuntimeError(f"Groq API call failed: {e}") from e

    def _parse_json_response(self, text: str) -> dict:
        """Extract JSON from LLM response, handling markdown code blocks."""
        # Try to find JSON in code blocks first
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if json_match:
            text = json_match.group(1)

        # Clean up common issues
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Last resort: find first { and last }
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
            return {"entities": [], "relationships": []}

    def chunk_text(self, text: str, chunk_size: int = 2000, overlap: int = 200) -> list[str]:
        """Split text into overlapping chunks for processing."""
        chunks = []
        sentences = re.split(r'(?<=[.!?])\s+', text)
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Keep overlap
                words = current_chunk.split()
                overlap_text = " ".join(words[-overlap // 5:]) if len(words) > overlap // 5 else ""
                current_chunk = overlap_text + " " + sentence
            else:
                current_chunk += " " + sentence

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text]

    def extract_from_text(self, text: str) -> ExtractionResult:
        """Extract entities and relationships from a text chunk using Groq."""
        prompt = EXTRACTION_PROMPT.format(text=text)

        try:
            response_text = self._call_groq(prompt)
            parsed = self._parse_json_response(response_text)

            entities = [Entity(**e) for e in parsed.get("entities", [])]
            relationships = [Relationship(**r) for r in parsed.get("relationships", [])]

            # Validate that relationship endpoints exist in entities
            entity_names = {e.name for e in entities}
            valid_relationships = [
                r for r in relationships
                if r.source in entity_names and r.target in entity_names
            ]

            return ExtractionResult(entities=entities, relationships=valid_relationships)

        except Exception as e:
            print(f"Extraction error: {e}")
            return ExtractionResult(entities=[], relationships=[])

    def extract_from_document(self, text: str) -> ExtractionResult:
        """Extract from a full document by chunking and merging results."""
        chunks = self.chunk_text(text)
        all_entities: dict[str, Entity] = {}
        all_relationships: list[Relationship] = []

        for chunk in chunks:
            result = self.extract_from_text(chunk)

            # Merge entities (deduplicate by name, keep longest description)
            for entity in result.entities:
                if entity.name not in all_entities or len(entity.description) > len(all_entities[entity.name].description):
                    all_entities[entity.name] = entity

            all_relationships.extend(result.relationships)

        # Deduplicate relationships
        seen_rels = set()
        unique_rels = []
        for rel in all_relationships:
            key = (rel.source, rel.target, rel.relation_type)
            if key not in seen_rels:
                seen_rels.add(key)
                unique_rels.append(rel)

        return ExtractionResult(
            entities=list(all_entities.values()),
            relationships=unique_rels,
        )

    def generate_answer(self, question: str, context: dict) -> str:
        """Generate an answer to a question using graph context."""
        # Format the graph context into readable text
        context_parts = []

        if context.get("nodes"):
            context_parts.append("ENTITIES:")
            for node in context["nodes"]:
                desc = f" — {node.get('description', '')}" if node.get("description") else ""
                context_parts.append(f"  • {node['name']} ({node.get('entity_type', 'Unknown')}){desc}")

        if context.get("edges"):
            context_parts.append("\nRELATIONSHIPS:")
            for edge in context["edges"]:
                desc = f" ({edge.get('description', '')})" if edge.get("description") else ""
                context_parts.append(f"  • {edge['source']} --[{edge['relation_type']}]--> {edge['target']}{desc}")

        if not context_parts:
            return "I don't have enough information in the knowledge graph to answer this question. Try ingesting relevant documents first."

        context_text = "\n".join(context_parts)
        prompt = QA_PROMPT.format(context=context_text, question=question)

        try:
            response_text = self._call_groq(prompt)
            return response_text
        except Exception as e:
            return f"Error generating answer: {e}"
