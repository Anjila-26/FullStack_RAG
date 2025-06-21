import tempfile
import os
from typing import Dict, Any
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

async def process_pdf(file_content: bytes, filename: str) -> Dict[Any, Any]:
    """
    Process a PDF file and return its chunks
    """
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        temp_file.write(file_content)
        temp_path = temp_file.name
    
    try:
        # Load PDF
        loader = PyMuPDFLoader(temp_path)
        docs = loader.load()
        
        if not docs:
            return {
                "success": False,
                "message": "No content found in the PDF file"
            }
        
        logger.info(f"Loaded {len(docs)} pages from PDF")
        
        # Use the same text splitter configuration as URL processing
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=400,
            separators=["\n\n", "\n", ".", "?", "!", " ", ""],
            length_function=len,
            is_separator_regex=False
        )
        
        # Split all documents
        all_splits = []
        for doc in docs:
            splits = text_splitter.split_text(doc.page_content)
            for split in splits:
                all_splits.append(type(doc)(page_content=split, metadata=doc.metadata))
        
        return {
            "success": True,
            "chunks": all_splits,
            "metadata": {"source": filename}
        }
        
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
    
    finally:
        # Clean up temporary file
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        except Exception as e:
            logger.warning(f"Could not delete temporary file: {e}")