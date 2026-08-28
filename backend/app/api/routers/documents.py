from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
import traceback
from typing import Any

from app.services.document_service import (
    process_and_store_document,
    get_user_documents,
    delete_user_document
)

router = APIRouter()

@router.post("/upload")
async def upload_document(file: UploadFile = File(...), user_id: str = Form(...)) -> Any:
    try:
        contents = await file.read()
        await process_and_store_document(contents, file.filename, user_id)
        return {"status": "success", "message": "Upload complete!", "filename": file.filename}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@router.get("/api/documents/{user_id}")
async def get_documents_endpoint(user_id: str) -> Any:
    try:
        documents = get_user_documents(user_id)
        return {"documents": documents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/{user_id}/{filename}")
async def delete_document_endpoint(user_id: str, filename: str) -> Any:
    try:
        delete_user_document(user_id, filename)
        return {"status": "success", "message": f"Deleted {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
