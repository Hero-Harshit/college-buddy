import os
from pathlib import Path
from typing import Any, Dict, List
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_core.prompts import PromptTemplate
from supabase.client import Client, create_client

# Load environment variables
env_path = Path(__file__).resolve().parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

app = FastAPI(
    title="College RAG Chatbot API",
    description="FastAPI backend with LangChain RAG pipeline powered by Google Gemini and Supabase pgvector.",
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
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")

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
            detail=f"Missing or placeholder configuration for: {', '.join(missing)}. "
                   f"Please set valid credentials in your environment or backend/.env file."
        )

    return supabase_url, supabase_key, gemini_api_key


@app.get("/health")
def health_check():
    """Health check endpoint to verify backend service status."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest):
    """
    RAG-powered chat endpoint:
    1. Embeds user query with Google Gemini text-embedding-004.
    2. Searches top 4 relevant chunks in Supabase vector store ('documents' table).
    3. Prompts Gemini 1.5 Flash with the retrieved context to answer strictly.
    4. Returns answer and source metadata.
    """
    supabase_url, supabase_key, gemini_api_key = get_credentials()

    try:
        # 1. Initialize Google Gemini Embeddings
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=gemini_api_key,
        )

        # 2. Initialize Supabase Vector Store
        supabase_client: Client = create_client(supabase_url, supabase_key)
        vector_store = SupabaseVectorStore(
            client=supabase_client,
            embedding=embeddings,
            table_name="documents",
            query_name="match_documents",
        )

        # 3. Retrieve top 4 most relevant chunks
        relevant_docs = vector_store.similarity_search(payload.question, k=4)

        # 4. Prepare context and source metadata
        context_parts = []
        sources = []
        for i, doc in enumerate(relevant_docs, start=1):
            context_parts.append(f"[Document Chunk {i}]:\n{doc.page_content}")
            sources.append({
                "chunk_index": i,
                "metadata": doc.metadata,
                "content_preview": doc.page_content[:200] + ("..." if len(doc.page_content) > 200 else "")
            })

        context_text = "\n\n".join(context_parts) if context_parts else "No relevant context found."

        # 5. Build prompt template
        prompt_template = PromptTemplate(
            template="""You are a helpful, accurate, and professional college assistant.
Answer the user's question strictly based on the provided context below.
If the context does not contain enough information to answer the question, state politely and clearly that you do not have that information in the college documentation.
Do NOT make up or assume facts outside of the provided context.

Context:
{context}

Question:
{question}

Answer:""",
            input_variables=["context", "question"],
        )

        prompt_str = prompt_template.format(
            context=context_text,
            question=payload.question,
        )

        # 6. Initialize Gemini LLM and generate response
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=gemini_api_key,
            temperature=0.2,
        )

        response = await llm.ainvoke(prompt_str)
        answer_text = response.content if isinstance(response.content, str) else str(response.content)

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
