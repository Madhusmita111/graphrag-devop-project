import os
import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def generate_answer(prompt: str):
    """Generate answer using Groq API (fixed version)"""

    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set")

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
        "temperature": 0.3
    }

    response = requests.post(url, headers=headers, json=payload)

    print(" ASK STATUS:", response.status_code)
    print(" ASK RESPONSE:", response.text)

    if response.status_code != 200:
        raise RuntimeError(f"Groq API error: {response.status_code} - {response.text}")

    result = response.json()

    return result["choices"][0]["message"]["content"]