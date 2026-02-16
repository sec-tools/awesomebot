"""Document processing utilities"""
import os
from typing import Optional
import PyPDF2
from docx import Document as DocxDocument


class DocumentProcessor:
    """Process various document types"""
    
    @staticmethod
    async def extract_text(file_path: str, file_type: str) -> Optional[str]:
        """Extract text from document"""
        
        try:
            if file_type == "pdf":
                return await DocumentProcessor._extract_pdf(file_path)
            elif file_type in ["txt", "md"]:
                return await DocumentProcessor._extract_text_file(file_path)
            elif file_type in ["docx", "doc"]:
                return await DocumentProcessor._extract_docx(file_path)
            else:
                return None
        except Exception as e:
            print(f"Error extracting text: {e}")
            return None
    
    @staticmethod
    async def _extract_pdf(file_path: str) -> str:
        """Extract text from PDF"""
        text = []
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text.append(page.extract_text())
        
        return "\n\n".join(text)
    
    @staticmethod
    async def _extract_text_file(file_path: str) -> str:
        """Extract text from plain text file"""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    
    @staticmethod
    async def _extract_docx(file_path: str) -> str:
        """Extract text from DOCX"""
        doc = DocxDocument(file_path)
        text = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text.append(paragraph.text)
        
        return "\n\n".join(text)


