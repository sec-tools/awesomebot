"""File upload and management API"""
import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.models import Document as DocumentModel
from app.models.user import User
from app.services import RAGService
from app.services.document_processor import DocumentProcessor
from app.core.auth import get_current_user

router = APIRouter()

# Global services
rag_service = RAGService()
doc_processor = DocumentProcessor()

# Upload directory
UPLOAD_DIR = "./data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class DocumentResponse(BaseModel):
    """Document response model"""
    id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.post("/upload", response_model=DocumentResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload and index a document"""
    
    # Validate file type
    allowed_types = ["pdf", "txt", "md", "docx", "doc"]
    file_ext = file.filename.split(".")[-1].lower()
    
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Allowed: {', '.join(allowed_types)}"
        )
    
    # Generate unique ID and save file
    doc_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}.{file_ext}")
    
    # Save file
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    file_size = len(content)
    
    # Extract text
    text = await doc_processor.extract_text(file_path, file_ext)
    
    if not text:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="Could not extract text from file")
    
    # Add to RAG index
    chunk_count = await rag_service.add_document(
        doc_id=doc_id,
        text=text,
        metadata={"filename": file.filename, "file_type": file_ext}
    )
    
    # Save to database
    document = DocumentModel(
        id=doc_id,
        filename=file.filename,
        file_type=file_ext,
        file_size=file_size,
        chunk_count=chunk_count
    )
    db.add(document)
    await db.commit()
    
    return DocumentResponse.model_validate(document)


@router.get("/", response_model=List[DocumentResponse])
async def get_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all uploaded documents"""
    
    result = await db.execute(select(DocumentModel))
    documents = result.scalars().all()
    
    return [DocumentResponse.model_validate(doc) for doc in documents]


@router.get("/{document_id}/view")
async def view_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """View document contents"""
    
    result = await db.execute(
        select(DocumentModel).where(DocumentModel.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Read file and extract text
    file_path = os.path.join(UPLOAD_DIR, f"{document_id}.{document.file_type}")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    # Extract text from file
    text = await doc_processor.extract_text(file_path, document.file_type)
    
    if not text:
        raise HTTPException(status_code=500, detail="Could not extract text from file")
    
    return {
        "filename": document.filename,
        "file_type": document.file_type,
        "content": text,
        "chunk_count": document.chunk_count
    }


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a document"""
    
    result = await db.execute(
        select(DocumentModel).where(DocumentModel.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from RAG index
    await rag_service.delete_document(document_id)
    
    # Delete file
    file_path = os.path.join(UPLOAD_DIR, f"{document_id}.{document.file_type}")
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete from database
    await db.delete(document)
    await db.commit()
    
    return {"status": "deleted"}

