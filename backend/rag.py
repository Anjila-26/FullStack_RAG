import tempfile
import os
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from loguru import logger

from document_agent import process_pdf
from scrape_agent import scrape_url

# Langchain and database imports
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Pydantic models
class QueryRequest(BaseModel):
    question: str
    n_results: Optional[int] = 5

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    success: bool
    message: Optional[str] = None

class ProcessURL(BaseModel):
    url: str

# Initialize FastAPI app
app = FastAPI(
    title="RAG Document Processing API",
    description="Process PDFs and URLs using RAG",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
embeddings = None
client = None
collection = None
embedding_dim = None
llm = None

# Initialize components
def initialize_components():
    """Initialize embeddings, Chroma client, and LLM"""
    global embeddings, client, collection, embedding_dim, llm
    try:
        embeddings = OllamaEmbeddings(model="mxbai-embed-large")
        client = chromadb.PersistentClient(path="chroma_store")
        
        # Test embedding dimensions
        test_single = embeddings.embed_query("test")
        embedding_dim = len(test_single)
        
        # Create or get collection
        collection_name = f"docs_mxbai_{embedding_dim}d"
        collection = client.get_or_create_collection(name=collection_name)
        
        # Initialize LLM
        llm = ChatOllama(model="llama3", temperature=0.7)
        
        logger.success("All components initialized successfully!")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize components: {str(e)}")
        return False

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    logger.info("Starting up RAG backend...")
    success = initialize_components()
    if not success:
        logger.error("Failed to initialize components")

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a PDF file"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    content = await file.read()
    result = await process_pdf(content, file.filename)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Add chunks to vector database
    chunks = result["chunks"]
    texts = [chunk.page_content for chunk in chunks]
    embeddings_list = embeddings.embed_documents(texts)
    
    # Store in database
    for i, (text, emb) in enumerate(zip(texts, embeddings_list)):
        doc_id = f"{file.filename}_{i}"
        collection.add(
            ids=[doc_id],
            documents=[text],
            embeddings=[emb]
        )
    
    return {"success": True, "message": f"Processed {len(chunks)} chunks"}

@app.post("/url")
async def process_webpage(url_data: ProcessURL):
    """Process content from a URL"""
    if not all([embeddings, collection]):
        raise HTTPException(
            status_code=503,
            detail="Backend components not initialized"
        )
    
    # Validate URL
    if not url_data.url.startswith(('http://', 'https://')):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL. Must start with http:// or https://"
        )
    
    result = await scrape_url(url_data.url)
    
    if not result["success"]:
        raise HTTPException(
            status_code=400, 
            detail=result.get("error", "Failed to process URL")
        )
    
    # Process the content using text splitter
    content = result["content"]
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=400,
        separators=["\n\n", "\n", ".", "?", "!", " ", ""],
        length_function=len,
        is_separator_regex=False
    )
    
    text_chunks = text_splitter.split_text(content)
    
    if not text_chunks:
        raise HTTPException(
            status_code=400,
            detail="No content could be extracted from the URL"
        )
    
    # Create embeddings and store
    try:
        embeddings_list = embeddings.embed_documents(text_chunks)
        
        for i, (text, emb) in enumerate(zip(text_chunks, embeddings_list)):
            doc_id = f"url_{i}"
            collection.add(
                ids=[doc_id],
                documents=[text],
                embeddings=[emb]
            )
        
        return {
            "success": True,
            "message": f"Processed {len(text_chunks)} chunks from URL"
        }
    except Exception as e:
        logger.error(f"Error processing URL content: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing URL content: {str(e)}"
        )

@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Query the processed documents"""
    if not all([embeddings, collection, llm]):
        raise HTTPException(status_code=503, detail="Components not initialized")
    
    try:
        # Query the collection
        query_embedding = embeddings.embed_query(request.question)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=request.n_results
        )
        
        if not results['documents'][0]:
            return QueryResponse(
                answer="No relevant documents found.",
                sources=[],
                success=True
            )
        
        # Generate response
        context = "\n\n".join(results['documents'][0])
        prompt = ChatPromptTemplate.from_template(
            "Answer based on this context:\n{context}\nQuestion: {question}"
        )
        chain = prompt | llm | StrOutputParser()
        response = chain.invoke({
            "context": context,
            "question": request.question
        })
        
        return QueryResponse(
            answer=response,
            sources=results['documents'][0][:3],
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error querying documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/clear")
async def clear_database():
    """Clear all documents from the database"""
    if not collection:
        raise HTTPException(status_code=503, detail="Database not initialized")
    try:
        # Get all document IDs
        all_ids = collection.get()['ids']
        if all_ids:
            # Delete all documents from collection
            collection.delete(ids=all_ids)
            logger.info(f"Cleared {len(all_ids)} documents from database")
            return {"success": True, "message": f"Cleared {len(all_ids)} documents"}
        return {"success": True, "message": "Database was already empty"}
    except Exception as e:
        logger.error(f"Error clearing database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error clearing database: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("rag:app", host="0.0.0.0", port=8000, reload=True)