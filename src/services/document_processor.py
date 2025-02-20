# src/services/document_processor.py
from pathlib import Path
from typing import Dict
import logging
from PyPDF2 import PdfReader
from docx import Document
import markdown

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Service for processing different types of input documents."""
    
    SUPPORTED_FORMATS = {'.pdf', '.docx', '.md', '.txt'}
    
    async def process_document(self, doc_path: str) -> str:
        """Process input document and extract text content."""
        try:
            path = Path(doc_path)
            if not path.exists():
                raise FileNotFoundError(f"Document not found: {doc_path}")
                
            if path.suffix not in self.SUPPORTED_FORMATS:
                raise ValueError(f"Unsupported file format: {path.suffix}")
            
            content = self._extract_content(path)
            return self._preprocess_content(content)
            
        except Exception as e:
            logger.error(f"Error processing document {doc_path}: {str(e)}")
            raise
    
    def _extract_content(self, file_path: Path) -> str:
        """Extract text content from different file formats."""
        if file_path.suffix == '.pdf':
            return self._extract_pdf(file_path)
        elif file_path.suffix == '.docx':
            return self._extract_docx(file_path)
        elif file_path.suffix == '.md':
            return self._extract_markdown(file_path)
        else:  # .txt
            return self._extract_text(file_path)
    
    def _extract_pdf(self, file_path: Path) -> str:
        with open(file_path, 'rb') as file:
            reader = PdfReader(file)
            return ' '.join(page.extract_text() for page in reader.pages)
    
    def _extract_docx(self, file_path: Path) -> str:
        doc = Document(file_path)
        return ' '.join(paragraph.text for paragraph in doc.paragraphs)
    
    def _extract_markdown(self, file_path: Path) -> str:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            return markdown.markdown(content)
    
    def _extract_text(self, file_path: Path) -> str:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    
    def _preprocess_content(self, content: str) -> str:
        """Preprocess extracted content for better analysis."""
        # Remove extra whitespace and normalize line endings
        content = ' '.join(content.split())
        return content