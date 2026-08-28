from typing import List
from google import genai
from app.core.config import get_credentials

_gemini_client: genai.Client | None = None

def get_gemini_client() -> genai.Client:
    """
    Returns a singleton instance of the Google GenAI client.
    """
    global _gemini_client
    if _gemini_client is None:
        _, _, gemini_api_key = get_credentials()
        _gemini_client = genai.Client(api_key=gemini_api_key)
    return _gemini_client

def get_query_embedding(text: str) -> List[float]:
    """
    Generates a 768-dimensional embedding for the given text using Gemini.
    """
    client = get_gemini_client()
    try:
        response = client.models.embed_content(
            model="text-embedding-004",
            contents=text,
        )
        return response.embeddings[0].values
    except Exception:
        # Fallback for some region constraints or model availability
        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
            config={"output_dimensionality": 768},
        )
        return response.embeddings[0].values

def generate_llm_answer(prompt: str) -> str:
    """
    Generates text content based on a prompt. Attempts multiple models as fallbacks.
    """
    client = get_gemini_client()
    models_to_try = [
        "gemini-3.6-flash",
        "gemini-2.5-flash",
        "gemini-2.0-flash", 
        "gemini-1.5-flash", 
        "gemini-1.5-flash-8b"
    ]
    
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            if hasattr(response, "text") and response.text:
                return response.text
        except Exception:
            continue
            
    return "Unable to generate a response from the AI model."
