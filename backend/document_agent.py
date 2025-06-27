import tempfile
import os
from typing import Dict, Any
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger
from agent_communication import SimpleAgent

class DocumentAgent(SimpleAgent):
    """Simple document processing agent"""
    
    def __init__(self):
        super().__init__("document_agent")
    
    async def handle_message(self, message):
        """Handle incoming messages"""
        if message["type"] == "process_pdf":
            data = message["data"]
            result = await self.process_pdf(data["content"], data["filename"])
            
            # Store result in shared memory
            self.set_shared_data(f"pdf_result_{data['filename']}", result)
            
            # Notify sender
            await self.send_message(
                message["from"], 
                "pdf_processed", 
                {"filename": data["filename"], "success": result["success"]}
            )
    
    async def process_pdf(self, file_content: bytes, filename: str) -> Dict[Any, Any]:
        """Process a PDF file and return its chunks"""
        self.set_status("processing")
        
        # Simple status notification
        await self.send_message("system", "status_update", {
            "agent": self.name,
            "activity": "processing_pdf",
            "filename": filename
        })
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name
        
        try:
            # Load PDF
            loader = PyMuPDFLoader(temp_path)
            docs = loader.load()
            
            if not docs:
                result = {
                    "success": False,
                    "message": "No content found in the PDF file"
                }
                self.set_status("idle")
                return result
            
            logger.info(f"Loaded {len(docs)} pages from PDF")
            
            # Split documents
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=2000,
                chunk_overlap=400,
                separators=["\n\n", "\n", ".", "?", "!", " ", ""],
                length_function=len,
                is_separator_regex=False
            )
            
            all_splits = []
            for doc in docs:
                splits = text_splitter.split_text(doc.page_content)
                for split in splits:
                    all_splits.append(type(doc)(page_content=split, metadata=doc.metadata))
            
            result = {
                "success": True,
                "chunks": all_splits,
                "metadata": {"source": filename}
            }
            
            # Log completion
            await self.send_message("system", "status_update", {
                "agent": self.name,
                "activity": "pdf_completed",
                "filename": filename,
                "chunks": len(all_splits)
            })
            
            self.set_status("idle")
            return result
            
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            result = {
                "success": False,
                "error": str(e)
            }
            self.set_status("idle")
            
            # Log error
            await self.send_message("system", "status_update", {
                "agent": self.name,
                "activity": "pdf_error",
                "filename": filename,
                "error": str(e)
            })
            
            return result
        
        finally:
            # Clean up
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Could not delete temporary file: {e}")

# Global instance
document_agent = DocumentAgent()

# Legacy function for compatibility
async def process_pdf(file_content: bytes, filename: str) -> Dict[Any, Any]:
    """Process PDF using the document agent"""
    return await document_agent.process_pdf(file_content, filename)