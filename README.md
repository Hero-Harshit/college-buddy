# College RAG Chatbot

An intelligent, RAG-powered college assistant application built with **FastAPI**, **LangChain**, **Google Gemini** (`models/text-embedding-004` & `gemini-1.5-flash`), **Supabase pgvector**, and **React + Vite**.

---

## Setup

### 1. Environment Configuration
Copy the example environment file in `/backend`:
```bash
cp backend/.env.example backend/.env
```

Fill in your actual credentials in `backend/.env`:
- `SUPABASE_URL`: Your Supabase Project URL.
- `SUPABASE_SERVICE_ROLE_KEY`: Your Supabase Service Role Secret Key.
- `GEMINI_API_KEY`: Your Google AI Studio API Key.

### 2. Supabase pgvector Setup
Run the following SQL script in your Supabase SQL Editor:
```sql
-- Create profiles table
create table if not exists profiles (
  id uuid references auth.users not null primary key,
  display_name text,
  age integer,
  gender text,
  major text,
  updated_at timestamp with time zone
);

-- Enable vector extension
create extension if not exists vector;

-- Create documents table (768 dimensions for Google text-embedding-004)
create table if not exists documents (
  id bigserial primary key,
  user_id text,
  content text,
  metadata jsonb,
  embedding vector(768)
);

-- Create chat sessions table
create table if not exists chat_sessions (
  id uuid primary key,
  user_id uuid references auth.users not null,
  title text,
  created_at timestamp with time zone default now()
);

-- Create chat messages table
create table if not exists chat_messages (
  id bigserial primary key,
  session_id uuid references chat_sessions on delete cascade,
  role text,
  content text,
  sources jsonb,
  created_at timestamp with time zone default now()
);

-- Create matching function for similarity search
create or replace function match_documents (
  query_embedding vector(768),
  p_user_id text,
  match_count int default null,
  filter jsonb default '{}'
) returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
#variable_conflict use_column
begin
  return query
  select
    id,
    content,
    metadata,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  where documents.user_id = p_user_id
  and metadata @> filter
  order by documents.embedding <=> query_embedding
  limit match_count;
end;
$$;
```

---

## Backend

### Installation
```bash
cd backend
pip install -r requirements.txt
```

### Document Ingestion
Place your college handbook or data PDF (e.g. `sample_college_data.pdf`) in the `backend/` directory, then run:
```bash
python ingest.py sample_college_data.pdf
```

### Running the API
```bash
uvicorn main:app --reload --port 8001
```
- Health Check: `GET http://localhost:8001/health`
- Chat Query: `POST http://localhost:8001/chat` with body `{"question": "What are the college library timings?"}`

---

## Frontend

### Installation & Development
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.
