import os
import sys
import math
from pathlib import Path
from typing import Any, Dict, List
from dotenv import load_dotenv

# Reconfigure stdout/stderr to utf-8 for Windows terminals
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from google import genai
from supabase import Client, create_client

# Load environment variables
env_path = Path(__file__).resolve().parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

app = FastAPI(
    title="College RAG Chatbot API",
    description="FastAPI backend powered by official google-genai SDK and Supabase pgvector.",
    version="1.0.0",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The user's question about the college.")


class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]


def get_credentials():
    """Validate and return the required API credentials."""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    gemini_api_key = os.environ.get("GEMINI_API_KEY")

    missing = []
    if not supabase_url or supabase_url.startswith("your_"):
        missing.append("SUPABASE_URL")
    if not supabase_key or supabase_key.startswith("your_"):
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if not gemini_api_key or gemini_api_key.startswith("your_"):
        missing.append("GEMINI_API_KEY")

    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Missing configuration for: {', '.join(missing)}. "
                   f"Please set valid credentials in your backend/.env file."
        )

    return supabase_url, supabase_key, gemini_api_key


def get_query_embedding(client: genai.Client, text: str) -> List[float]:
    """Generates embedding for search query using google-genai."""
    try:
        response = client.models.embed_content(
            model="text-embedding-004",
            contents=text,
        )
        return response.embeddings[0].values
    except Exception:
        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
            config={"output_dimensionality": 768},
        )
        return response.embeddings[0].values


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculates cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def retrieve_relevant_documents(supabase: Client, query_embedding: List[float], match_count: int = 4) -> List[Dict[str, Any]]:
    """Retrieves top matching documents via Supabase RPC with client fallback."""
    try:
        rpc_response = supabase.rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_count": match_count,
            }
        ).execute()
        if rpc_response.data:
            return rpc_response.data
    except Exception as rpc_err:
        print(f"Supabase RPC note: {rpc_err}. Falling back to table similarity calculation.")

    # Fallback to direct table scan & cosine similarity calculation
    try:
        docs_response = supabase.table("documents").select("id, content, metadata, embedding").execute()
        raw_docs = docs_response.data or []
        scored_docs = []
        for d in raw_docs:
            emb = d.get("embedding")
            if isinstance(emb, str):
                import json
                try:
                    emb = json.loads(emb)
                except Exception:
                    emb = [float(x.strip()) for x in emb.strip("[]").split(",") if x.strip()]
            if emb:
                sim = cosine_similarity(query_embedding, emb)
                scored_docs.append({
                    "id": d.get("id"),
                    "content": d.get("content"),
                    "metadata": d.get("metadata", {}),
                    "similarity": sim,
                })
        scored_docs.sort(key=lambda x: x["similarity"], reverse=True)
        return scored_docs[:match_count]
    except Exception as fallback_err:
        print(f"Fallback search error: {fallback_err}")
        return []


def generate_llm_answer(client: genai.Client, prompt: str) -> str:
    """Generates LLM response using available fast Gemini model."""
    for model_name in ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.7-flash", "gemini-flash-latest"]:
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


@app.get("/health")
def health_check():
    """Health check endpoint to verify backend service status."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest):
    """
    RAG-powered chat endpoint:
    1. Generates query embedding using google-genai (text-embedding-004).
    2. Retrieves top 4 relevant chunks from Supabase pgvector.
    3. Prompts Gemini 3.7 Flash with the retrieved context.
    4. Returns the generated answer along with chunk sources.
    """
    supabase_url, supabase_key, gemini_api_key = get_credentials()

    try:
        # 1. Initialize Google GenAI and Supabase clients
        client = genai.Client(api_key=gemini_api_key)
        supabase: Client = create_client(supabase_url, supabase_key)

        # 2. Generate embedding for user query
        query_embedding = get_query_embedding(client, payload.question)

        # 3. Retrieve relevant chunks from Supabase
        matched_docs = retrieve_relevant_documents(supabase, query_embedding, match_count=4)

        # 4. Prepare context and sources
        context_parts = []
        sources = []
        for i, doc in enumerate(matched_docs, start=1):
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            similarity = doc.get("similarity", 0.0)

            context_parts.append(f"[Document Chunk {i}]:\n{content}")
            sources.append({
                "chunk_index": i,
                "similarity": similarity,
                "metadata": metadata,
                "content_preview": content[:200] + ("..." if len(content) > 200 else "")
            })

        context_text = "\n\n".join(context_parts) if context_parts else "No relevant context found in documents."

        # 5. Construct the prompt
        user_question = payload.question
        prompt = f"""You are "CollegeBuddy", the friendly, intelligent, and official AI Student Assistant for ABC Engineering College.

YOUR CORE BEHAVIOR RULES:
1. IDENTITY & GREETINGS:
   - If the user greets you (e.g., "Hi", "Hello"), welcomes you, or asks who you are / what this chatbot is about, introduce yourself warmly as CollegeBuddy.
   - Explain that you are built to help students with admissions, fees, hostel rules, courses, and campus policies at ABC Engineering College.

2. COLLEGE-SPECIFIC QUESTIONS:
   - When answering specific questions regarding college policies, fees, dates, or programs, strictly rely on the provided CONTEXT below.
   - Ground your answer in the provided context and present the facts clearly using bullet points and bold highlights where appropriate.

3. UNKNOWN / OUT-OF-CONTEXT QUESTIONS:
   - If a college-related question cannot be answered using the provided CONTEXT, politely state: "I do not have that specific information in the college documentation." Suggest what topics you can help with instead.

---
CONTEXT FROM COLLEGE DOCUMENTS:
{context_text}
---

USER QUESTION:
{user_question}

ANSWER:
"""

        # 6. Generate answer using Gemini 3.7 Flash
        answer_text = generate_llm_answer(client, prompt)

        return ChatResponse(
            answer=answer_text,
            sources=sources,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing the request: {str(e)}"
        )
