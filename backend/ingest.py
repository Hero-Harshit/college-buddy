import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from supabase.client import Client, create_client

# Load environment variables from .env file
# Looks in the current directory (backend/) or root
env_path = Path(__file__).resolve().parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


def get_required_env_var(name: str) -> str:
    """Retrieve an environment variable or raise an error if missing."""
    value = os.getenv(name)
    if not value or value.startswith("your_"):
        raise ValueError(
            f"Missing required environment variable: '{name}'. "
            f"Please configure it in backend/.env or your environment."
        )
    return value


def ingest_pdf(file_path: str = "sample_college_data.pdf"):
    """
    Ingests a PDF document into Supabase pgvector using Google Gemini embeddings.

    Steps:
    1. Validate environment credentials.
    2. Load PDF using PyPDFLoader.
    3. Split text into chunks using RecursiveCharacterTextSplitter.
    4. Generate embeddings via Google Gemini text-embedding-004.
    5. Store embeddings and documents in Supabase vector store ('documents' table).
    """
    # 1. Validate environment variables
    supabase_url = get_required_env_var("SUPABASE_URL")
    supabase_key = get_required_env_var("SUPABASE_SERVICE_ROLE_KEY")
    gemini_api_key = get_required_env_var("GEMINI_API_KEY")

    # 2. Check if the PDF file exists
    pdf_path = Path(file_path)
    if not pdf_path.is_absolute():
        pdf_path = Path(__file__).resolve().parent / file_path

    if not pdf_path.exists():
        print(f"Error: PDF file not found at '{pdf_path}'.")
        print("Please place your college data PDF in the backend directory or pass the file path as an argument.")
        sys.exit(1)

    print(f"Loading PDF document from: {pdf_path}")
    loader = PyPDFLoader(str(pdf_path))
    raw_documents = loader.load()
    print(f"Loaded {len(raw_documents)} page(s) from document.")

    # 3. Chunk text
    print("Splitting document into chunks (chunk_size=800, chunk_overlap=100)...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        length_function=len,
        is_separator_regex=False,
    )
    chunks = text_splitter.split_documents(raw_documents)
    print(f"Created {len(chunks)} chunk(s).")

    # 4. Initialize Google Gemini Embeddings
    print("Initializing Google Gemini Embeddings (models/text-embedding-004)...")
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=gemini_api_key,
    )

    # 5. Initialize Supabase Client & Vector Store
    print("Connecting to Supabase and uploading embeddings to 'documents' table...")
    supabase_client: Client = create_client(supabase_url, supabase_key)

    SupabaseVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        client=supabase_client,
        table_name="documents",
        query_name="match_documents",
    )

    print("Document ingestion completed successfully!")


if __name__ == "__main__":
    target_pdf = sys.argv[1] if len(sys.argv) > 1 else "sample_college_data.pdf"
    try:
        ingest_pdf(target_pdf)
    except Exception as e:
        print(f"Ingestion failed: {e}", file=sys.stderr)
        sys.exit(1)
