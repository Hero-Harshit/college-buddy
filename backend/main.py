from fastapi import FastAPI

app = FastAPI(title="College RAG Chatbot API")


@app.get("/health")
def health_check():
    return {"status": "ok"}
