import uuid
from typing import Dict, Any
from app.services.supabase_service import get_supabase_client
from app.services.gemini_service import get_query_embedding, generate_llm_answer
from app.schemas.chat import ChatRequest

def get_user_sessions(user_id: str):
    supabase_client = get_supabase_client()
    response = supabase_client.table('chat_sessions').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
    return response.data

def get_session_messages(session_id: str):
    supabase_client = get_supabase_client()
    response = supabase_client.table('chat_messages').select('*').eq('session_id', session_id).order('created_at').execute()
    return response.data

def process_chat_message(request: ChatRequest) -> Dict[str, Any]:
    supabase_client = get_supabase_client()

    # 1. Manage Session
    session_id = request.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        title = request.message[:30] + "..." if len(request.message) > 30 else request.message
        supabase_client.table('chat_sessions').insert({
            "id": session_id,
            "user_id": request.user_id,
            "title": title
        }).execute()

    # 2. Save User Message
    supabase_client.table('chat_messages').insert({
        "session_id": session_id,
        "role": "user",
        "content": request.message
    }).execute()

    sources_list = []
    
    # 3. Handle Chat Logic Based on Mode
    if not request.rag_mode:
        # PATH A: General Knowledge Mode
        system_prompt = (
            "You are CollegeBuddy, an AI chatbot integrated into the CollegeBuddy application. "
            "You are designed specifically for students to ask questions related to their college syllabus, "
            "previous year questions (PYQs), and complex study documents. "
            "You are currently in General Knowledge Mode. Answer the user's questions accurately, casually, and helpfully based on your general knowledge. "
            "You can answer anything, but always maintain your helpful student-assistant persona."
        )
        final_prompt = f"{system_prompt}\n\nUSER QUESTION:\n{request.message}"
        gemini_response = generate_llm_answer(final_prompt)
        
    else:
        # PATH B: RAG Mode
        # Check if user has docs
        user_docs_check = supabase_client.table('documents').select('id').eq('user_id', request.user_id).limit(1).execute()
        
        if not user_docs_check.data:
            # RAG Mode but no docs
            gemini_response = "I cannot answer this because you haven't uploaded any documents. Please upload a PDF in the Profile tab or switch to General Assistant mode."
        else:
            # RAG Mode with docs
            query_embedding = get_query_embedding(request.message)
            
            # Fetch all user documents to compute similarity locally (bypassing broken RPC)
            docs_resp = supabase_client.table('documents').select('content, metadata, embedding').eq('user_id', request.user_id).execute()
            all_docs = docs_resp.data or []
            
            import math
            import json
            
            def cosine_similarity(vec1, vec2):
                if not vec1 or not vec2:
                    return 0.0
                
                # If Supabase returned the vector as a string, parse it
                if isinstance(vec1, str):
                    try:
                        vec1 = json.loads(vec1)
                    except Exception:
                        pass
                if isinstance(vec2, str):
                    try:
                        vec2 = json.loads(vec2)
                    except Exception:
                        pass
                
                # Force conversion to float
                vec1 = [float(x) for x in vec1]
                vec2 = [float(x) for x in vec2]
                
                dot_product = sum(a * b for a, b in zip(vec1, vec2))
                mag1 = math.sqrt(sum(a * a for a in vec1))
                mag2 = math.sqrt(sum(b * b for b in vec2))
                if mag1 == 0 or mag2 == 0:
                    return 0.0
                return dot_product / (mag1 * mag2)
            
            scored_docs = []
            for doc in all_docs:
                emb = doc.get('embedding')
                if emb:
                    sim = cosine_similarity(emb, query_embedding)
                    if sim > 0.0:  # Threshold can be adjusted
                        scored_docs.append((sim, doc))
            
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            relevant_docs = [doc for sim, doc in scored_docs[:4]]
            
            context_parts = []
            
            for doc in relevant_docs:
                content = doc.get("content", "")
                metadata = doc.get("metadata") or {}
                filename = metadata.get("filename", "unknown_file")
                context_parts.append(f"[Document: {filename}]\nContent: {content}")
                sources_list.append({"document": filename, "page": 1})
                
            context_text = "\n\n".join(context_parts) if context_parts else "No relevant context found."
            
            system_prompt = (
                "You are CollegeBuddy, an AI assistant that ONLY answers questions based on the uploaded documents.\n"
                "RULES:\n"
                "1. You MUST answer the user's question USING ONLY the provided document context.\n"
                "2. If the answer is NOT explicitly stated in the document context, you MUST say exactly: "
                "'I cannot answer this based on the provided documents.'\n"
                "3. UNDER NO CIRCUMSTANCES are you allowed to use general knowledge, internet information, or facts outside of the provided text."
            )
            
            final_prompt = f"{system_prompt}\n\nCONTEXT:\n{context_text}\n\nUSER QUESTION:\n{request.message}"
            gemini_response = generate_llm_answer(final_prompt)

    # 4. Save AI Response
    supabase_client.table('chat_messages').insert({
        "session_id": session_id,
        "role": "assistant",
        "content": gemini_response
    }).execute()

    return {"answer": gemini_response, "sources": sources_list, "session_id": session_id}
