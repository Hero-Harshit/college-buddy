# Software Requirements Specification (SRS) - CollegeBuddy RAG Chatbot

## 1. Overview
The CollegeBuddy RAG Chatbot is an AI-powered college study ecosystem. It allows students to upload their PDF documents, process them into chunks and embeddings, and then query an AI assistant that answers questions *strictly* based on the uploaded context.

## 2. Technology Stack
- **Frontend**: React, Vite, Tailwind CSS
- **Backend Framework**: Python FastAPI
- **Database**: Supabase PostgreSQL with `pgvector` extension
- **AI / Embeddings**: Google Gemini (`text-embedding-004` or `gemini-embedding-001` for embeddings, and `gemini-3.7-flash` or similar models for generation).
- **PDF Processing**: `pypdf`, `langchain-text-splitters`

## 3. Database Schema Overview
The database uses Supabase PostgreSQL. The following tables exist to support the application:

- **`documents`**: Stores the uploaded PDFs, their raw text content, and their generated 768-dimensional vector embeddings.
- **`profiles`**: Manages user profiles (linked to Supabase Auth).
- **`chat_sessions`**: Tracks individual chat instances/threads for a user.
- **`chat_messages`**: Stores the message history (both user queries and AI responses) linked to a specific chat session to provide conversational memory.

## 4. RPC Functions
- **`match_documents`**: A PostgreSQL RPC (Remote Procedure Call) function leveraging `pgvector`. It takes a query embedding and performs a similarity search against the `documents` table to return the most relevant document chunks based on cosine similarity.

## 5. API Endpoints Required

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
