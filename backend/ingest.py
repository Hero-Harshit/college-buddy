import os
import sys
from pathlib import Path
from typing import Any, Dict, List
from dotenv import load_dotenv

# Reconfigure stdout/stderr to utf-8 for Windows terminals
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from google import genai
from pypdf import PdfReader
from supabase import Client, create_client

# Load environment variables
env_path = Path(__file__).resolve().parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


def get_required_env_var(name: str) -> str:
    """Retrieve an environment variable or raise an error if missing."""
    value = os.environ.get(name)
    if not value or value.startswith("your_"):
        raise ValueError(
            f"Missing required environment variable: '{name}'. "
            f"Please check your backend/.env file."
        )
    return value


def extract_text_from_pdf(pdf_path: Path) -> List[Dict[str, Any]]:
    """Extract text from each page of a PDF using pypdf."""
    reader = PdfReader(str(pdf_path))
    pages = []
    for page_idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if text and text.strip():
            pages.append({
                "page_number": page_idx,
                "text": text.strip(),
            })
    return pages


def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> List[str]:
    """
    Pure Python text chunker that creates overlapping text segments.
    Splits with priority given to paragraphs or spaces to avoid cutting words.
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        if end >= text_length:
            chunk = text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break

        boundary = text.rfind("\n", start, end)
        if boundary == -1 or boundary < start + (chunk_size // 2):
            boundary = text.rfind(" ", start, end)

        if boundary != -1 and boundary > start:
            chunk = text[start:boundary].strip()
            start = max(start + 1, boundary - chunk_overlap)
        else:
            chunk = text[start:end].strip()
            start = end - chunk_overlap

        if chunk:
            chunks.append(chunk)

    return chunks


def get_embedding(client: genai.Client, text: str) -> List[float]:
    """
    Generates embedding for a chunk of text using the official google-genai SDK.
    Uses 'text-embedding-004' (with 'gemini-embedding-001' 768-dim fallback if needed).
    """
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


def ingest_pdf(file_path: str = "sample_college_data.pdf"):
    """
    Ingests a PDF document into Supabase pgvector using google-genai:
    1. Reads PDF via pypdf.
    2. Chunks text into ~800 char segments.
    3. Generates embeddings using text-embedding-004.
    4. Inserts records into Supabase 'documents' table.
    """
    supabase_url = get_required_env_var("SUPABASE_URL")
    supabase_key = get_required_env_var("SUPABASE_SERVICE_ROLE_KEY")
    gemini_api_key = get_required_env_var("GEMINI_API_KEY")

    # Locate PDF
    pdf_path = Path(file_path)
    if not pdf_path.is_absolute():
        pdf_path = Path(__file__).resolve().parent / file_path

    if not pdf_path.exists():
        print(f"Error: PDF file not found at '{pdf_path}'")
        sys.exit(1)

    print(f"Reading PDF: {pdf_path.name}")
    pages = extract_text_from_pdf(pdf_path)
    print(f"Extracted text from {len(pages)} non-empty page(s).")

    if not pages:
        print("Warning: No text could be extracted from the PDF.")
        return

    # Split text into chunks
    all_chunks = []
    for page in pages:
        page_chunks = chunk_text(page["text"], chunk_size=800, chunk_overlap=100)
        for idx, chunk in enumerate(page_chunks):
            all_chunks.append({
                "content": chunk,
                "metadata": {
                    "source": pdf_path.name,
                    "page": page["page_number"],
                    "chunk_index": idx,
                }
            })

    print(f"Total chunks created: {len(all_chunks)}")

    # Initialize google-genai Client
    print("Initializing Google GenAI client...")
    client = genai.Client(api_key=gemini_api_key)

    # Initialize Supabase client
    print("Connecting to Supabase...")
    supabase: Client = create_client(supabase_url, supabase_key)

    # Generate embeddings and upload in batches
    batch_size = 20
    records_to_insert = []
    print("Generating embeddings and uploading to Supabase 'documents' table...")

    for i, item in enumerate(all_chunks, start=1):
        embedding = get_embedding(client, item["content"])

        records_to_insert.append({
            "content": item["content"],
            "metadata": item["metadata"],
            "embedding": embedding,
        })

        # Insert when batch is full or at the end
        if len(records_to_insert) >= batch_size or i == len(all_chunks):
            supabase.table("documents").insert(records_to_insert).execute()
            print(f"  Processed and uploaded {i}/{len(all_chunks)} chunks...")
            records_to_insert = []

    print("Success: Document ingestion completed successfully!")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "sample_college_data.pdf"
    try:
        ingest_pdf(target)
    except Exception as err:
        print(f"Ingestion failed: {err}", file=sys.stderr)
        sys.exit(1)
