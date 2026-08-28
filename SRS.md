# Software Requirements Specification (SRS) - CollegeBuddy RAG Chatbot

## 1. Overview
The CollegeBuddy RAG Chatbot is an AI-powered college study ecosystem. It allows students to upload their PDF documents, process them into chunks and embeddings, and then query an AI assistant that answers questions *strictly* based on the uploaded context.

## 2. Technology Stack
- **Frontend**: (Out of Scope for Backend Rewrite - Remains Unchanged)
- **Backend Framework**: Python FastAPI
- **Database**: Supabase PostgreSQL with `pgvector` extension
- **AI / Embeddings**: Google Gemini (`text-embedding-004` or `gemini-embedding-001` for embeddings, and `gemini-3.7-flash` or similar models for generation).
- **PDF Processing**: `pypdf`, `langchain-text-splitters`

## 3. Database Schema (Source of Truth)
The verified Supabase PostgreSQL schema to be used:

```sql
-- Ensure the vector extension is enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- DOCUMENTS TABLE (Stores PDFs and Vector Embeddings)
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL, 
    filename TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(768), 
    file_size TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- PROFILES TABLE (User Management)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY, 
    email TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- CHAT SESSIONS TABLE (Sidebar History)
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- CHAT MESSAGES TABLE (Memory for the AI)
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL, 
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);
```

## 4. RPC Function for Vector Search
The active, optimized pgvector similarity search function:

```sql
-- Explicitly drop old overloaded versions to prevent RPC signature errors
DROP FUNCTION IF EXISTS match_documents(vector(768), float, int, uuid);
DROP FUNCTION IF EXISTS match_documents(vector(768), float, int, text);

-- The active, optimized pgvector similarity search function
CREATE OR REPLACE FUNCTION match_documents (
  query_embedding vector(768), 
  match_threshold float,
  match_count int,
  p_user_id text 
)
RETURNS TABLE (
  id uuid,
  filename text,
  content text,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    documents.id,
    documents.filename,
    documents.content,
    1 - (documents.embedding <=> query_embedding) AS similarity
  FROM documents
  WHERE documents.user_id::text = p_user_id
  AND 1 - (documents.embedding <=> query_embedding) > match_threshold
  ORDER BY documents.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
```

## 5. API Endpoints Required
The backend must implement the following endpoints exactly to ensure frontend compatibility:

### 5.1 Document Management
- `POST /upload`
  - Accepts: `file` (UploadFile), `user_id` (Form Data)
  - Action: Extracts text, chunks text, generates embeddings, stores in Supabase `documents`.
- `GET /api/documents/{user_id}`
  - Action: Retrieves a list of unique filenames uploaded by the user.
- `DELETE /documents/{user_id}/{filename}`
  - Action: Deletes all document chunks matching the user_id and filename.

### 5.2 Chat and Sessions
- `GET /sessions/{user_id}`
  - Action: Retrieves chat sessions for the user, ordered by creation date descending.
- `GET /sessions/{session_id}/messages`
  - Action: Retrieves chat messages for a specific session.
- `POST /chat`
  - Accepts JSON: `{ "message": "...", "user_id": "...", "user_name": "Student", "session_id": "..." }`
  - Action: Runs vector similarity search via RPC. Calls Gemini to answer based on context. Saves user query and AI response to `chat_messages`. Returns answer, sources, and session_id.
