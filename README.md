

<h1 align="center">College Buddy RAG Chatbot</h1>

<p align="center">
  An intelligent, aesthetically designed <strong>Retrieval-Augmented Generation (RAG)</strong> study ecosystem. 
  <br />
  Built with a modern Forest-Themed glassmorphism UI, Supabase pgvector, and Google's Gemini API.
</p>

---

## -> Features

- **Context-Aware AI:** Answers questions strictly based on the documents you upload, eliminating hallucinations.
- **Smart Source Deduplication:** The AI clearly and cleanly cites the exact PDF documents it pulled information from.
- **Beautiful Forest UI:** Ultra-premium glassmorphism UI with subtle notebook-doodle backgrounds, custom emerald scrollbars, and gorgeous markdown tables.
- **Conversational Memory:** Remembers your chat history within a session so you can ask follow-up questions naturally.
- **Document Management:** Seamlessly upload, view, and delete college PDFs (pyqs, syllabus, policies) directly from your profile.

---

## 🛠️ Technology Stack

| Component | Technology |
|---|---|
| **Frontend** | React, Vite, Tailwind CSS v4, Lucide Icons |
| **Backend** | Python, FastAPI |
| **Database** | Supabase PostgreSQL, `pgvector` extension |
| **AI Models** | Google Gemini (`text-embedding-004` & `gemini-3.7-flash`) |
| **Processing** | `pypdf`, `langchain-text-splitters` |

---

## 🚀 Quick Setup Guide

### 1. Environment Configuration
Clone the repository and set up your backend environment variables:
```bash
cp backend/.env.example backend/.env
```
Fill in your `backend/.env`:
- `SUPABASE_URL`: Your Supabase Project URL.
- `SUPABASE_SERVICE_ROLE_KEY`: Your Supabase Service Role Secret Key.
- `GEMINI_API_KEY`: Your Google AI Studio API Key.

### 2. Database Setup (Supabase)
Run the following SQL in your Supabase SQL Editor to enable vectors and create the required matching function:
```sql
CREATE EXTENSION IF NOT EXISTS vector;

-- Ensure the match_documents RPC is installed for similarity search
CREATE OR REPLACE FUNCTION match_documents (
  query_embedding vector(768), match_threshold float, match_count int, p_user_id text 
) RETURNS TABLE (id uuid, filename text, content text, similarity float)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY SELECT documents.id, documents.filename, documents.content, 1 - (documents.embedding <=> query_embedding) AS similarity
  FROM documents WHERE documents.user_id::text = p_user_id AND 1 - (documents.embedding <=> query_embedding) > match_threshold
  ORDER BY documents.embedding <=> query_embedding LIMIT match_count;
END;
$$;
```
*(Note: Full table schemas are automatically handled by the application, but `match_documents` must be created manually).*

### 3. Start the Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Or .\.venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

### 4. Start the Frontend
```bash
cd frontend
npm install
npm run dev
```

Visit **[http://localhost:5173](http://localhost:5173)** to start chatting with College Buddy!

---

## 📚 Documentation
For a complete overview of the system architecture, database schema, and API endpoints, please refer to the [Software Requirements Specification (SRS.md)](./SRS.md).
