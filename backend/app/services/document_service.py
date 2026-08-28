import io
import pypdf
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.services.supabase_service import get_supabase_client
from app.services.gemini_service import get_query_embedding

async def process_and_store_document(file_bytes: bytes, filename: str, user_id: str) -> None:
    """
    Extracts text from a PDF, chunks it, generates embeddings, 
    and stores them in the Supabase documents table, strictly adhering to the schema.
    """
    # 1. Extract text
    pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page_idx, page in enumerate(pdf_reader.pages, start=1):
        extracted = page.extract_text()
        if extracted and extracted.strip():
            pages.append({"page_number": page_idx, "text": extracted.strip()})

    if not pages:
        raise ValueError("Could not extract any text from the provided PDF.")

    # 2. Chunk text
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200, 
        separators=["\n\n", "\n", ".", " ", ""]
    )
    
    all_chunks = []
    for page in pages:
        page_chunks = text_splitter.split_text(page["text"])
        for idx, chunk in enumerate(page_chunks):
            all_chunks.append({
                "content": chunk,
            })

    # 3. Generate embeddings & Prepare Records
    for chunk_dict in all_chunks:
        chunk_dict["embedding"] = get_query_embedding(chunk_dict["content"])

    # 4. Insert into Supabase in batches
    supabase_client = get_supabase_client()
    records_to_insert = []
    batch_size = 20
    
    file_size = str(len(file_bytes))
    
    for i, chunk_dict in enumerate(all_chunks, start=1):
        record = {
            "user_id": user_id,
            "content": chunk_dict["content"],
            "embedding": chunk_dict["embedding"],
            "metadata": {"filename": filename, "file_size": file_size}
        }
        
        records_to_insert.append(record)
        
        if len(records_to_insert) >= batch_size or i == len(all_chunks):
            supabase_client.table("documents").insert(records_to_insert).execute()
            records_to_insert = []

def get_user_documents(user_id: str) -> List[Dict[str, str]]:
    """
    Retrieves a list of unique filenames uploaded by the user.
    """
    supabase_client = get_supabase_client()
    response = supabase_client.table("documents").select("metadata").eq("user_id", user_id).execute()
    
    docs_map = {}
    for row in response.data or []:
        metadata = row.get("metadata") or {}
        fname = metadata.get("filename")
        if fname and fname not in docs_map:
            docs_map[fname] = {"filename": fname}
            
    return list(docs_map.values())

def delete_user_document(user_id: str, filename: str) -> None:
    """
    Deletes all chunks of a specific document for a user.
    """
    supabase_client = get_supabase_client()
    # We must fetch the records first since we can't delete directly on a JSONB field easily via simple eq()
    response = supabase_client.table("documents").select("id, metadata").eq("user_id", user_id).execute()
    
    ids_to_delete = []
    for row in response.data or []:
        metadata = row.get("metadata") or {}
        if metadata.get("filename") == filename:
            ids_to_delete.append(row["id"])
            
    if ids_to_delete:
        # Delete in batches or use in_ to delete all at once
        supabase_client.table("documents").delete().in_("id", ids_to_delete).execute()
