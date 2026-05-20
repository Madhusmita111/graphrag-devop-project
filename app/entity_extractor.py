import os
import json
import re
import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def call_groq(prompt: str):
    """Call Groq API using requests (correct implementation)"""

    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set")

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0
    }

    response = requests.post(url, headers=headers, json=payload)

    print("🔥 STATUS:", response.status_code)
    print("🔥 RESPONSE:", response.text)

    if response.status_code != 200:
        raise RuntimeError(f"Groq API error: {response.status_code} - {response.text}")

    result = response.json()

    return result["choices"][0]["message"]["content"]


def parse_json_response(response: str):
    """Safely parse LLM output into JSON"""

    try:
        return json.loads(response)
    except:
        # Try extracting JSON from messy LLM output
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass

    return {"entities": [], "relationships": []}


def normalize_relation(rel: str):
    """Normalize relation names (e.g., 'works at' → 'WORKS_AT')"""
    return rel.upper().replace(" ", "_")


def extract_entities(text: str):
    """Main function: text → entities + relationships"""

    if not text.strip():
        return [], []

    prompt = f"""
You are an information extraction system.

Extract entities and relationships from the text.

STRICT RULES:
- Use meaningful relationship types ONLY from below:
  FOUNDED, WORKS_AT, PLACED_AT, STUDIES, HAS_ROLE, BUILDS

- Do NOT use generic terms like RELATED_TO

- Identify entity types correctly:
  Person, Organization, Role, Education

Return ONLY valid JSON:

{{
  "entities": [
    {{"name": "Entity", "entity_type": "TYPE"}}
  ],
  "relationships": [
    {{"source": "A", "target": "B", "relation_type": "RELATION"}}
  ]
}}

TEXT:
{text}
"""

    response = call_groq(prompt)
    data = parse_json_response(response)

    entities = []
    relationships = []

    # Process entities
    for e in data.get("entities", []):
        if "name" in e:
            entities.append({
                "name": e["name"],
                "entity_type": e.get("entity_type", "UNKNOWN"),
                "description": e.get("description", "")
            })

    # Process relationships
    for r in data.get("relationships", []):
        if "source" in r and "target" in r:
            relationships.append({
                "source": r["source"],
                "target": r["target"],
                "relation_type": normalize_relation(r.get("relation_type", "RELATED_TO")),
                "description": r.get("description", "")
            })

    return entities, relationships