import tempfile
import os
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Langchain dependencies
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
import chromadb
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from loguru import logger

# Pydantic models for request/response
class QueryRequest(BaseModel):
    question: str
    n_results: Optional[int] = 5

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    success: bool
    message: Optional[str] = None

class ProcessResponse(BaseModel):
    success: bool
    message: str
    document_count: Optional[int] = None

# Initialize FastAPI app
app = FastAPI(
    title="RAG Document Processing API",
    description="Upload PDFs and query them using RAG (Retrieval Augmented Generation)",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for components
embeddings = None
client = None
collection = None
embedding_dim = None
llm = None

# System prompt for the LLM
SYSTEM_PROMPT = """
You are an intelligent assistant that answers questions based on provided context from documents. Your role is to:

1. **Analyze the provided context carefully** and extract relevant information to answer the user's question
2. **Answer based ONLY on the information provided** in the context - do not use external knowledge
3. **Be accurate and precise** - if the context doesn't contain enough information to answer the question, clearly state this
4. **Quote directly from the context** when appropriate, using quotation marks
5. **Maintain the same tone and style** as the source material when possible

## Instructions:
- If the answer is clearly stated in the context, provide a direct answer
- If the context contains partial information, explain what you can determine and what is unclear
- If the context doesn't contain relevant information, respond with: "The provided context doesn't contain enough information to answer this question."
- Always be honest about the limitations of the provided context

## Context:
{context}

## Question:
{question}

## Answer:
"""

def initialize_components():
    """Initialize embeddings, Chroma client, and LLM"""
    global embeddings, client, collection, embedding_dim, llm
    
    try:
        # Initialize embeddings
        embeddings = OllamaEmbeddings(model="mxbai-embed-large")
        
        # Initialize Chroma client
        client = chromadb.PersistentClient(path="chroma_store")
        
        # Test embedding dimensions for consistency
        test_single = embeddings.embed_query("test")
        test_batch = embeddings.embed_documents(["test"])
        
        single_dim = len(test_single)
        batch_dim = len(test_batch[0]) if test_batch else 0
        
        if single_dim != batch_dim:
            logger.warning(f"⚠️ Embedding dimension inconsistency detected!")
            logger.warning(f"Single query: {single_dim}d, Batch: {batch_dim}d")
            logger.info("Using batch embedding dimension for consistency.")
            embedding_dim = batch_dim
        else:
            embedding_dim = single_dim
        
        # Create or get collection
        collection_name = f"docs_mxbai_{embedding_dim}d"
        collection = client.get_or_create_collection(name=collection_name)
        logger.info(f"Using collection: {collection_name} (embedding dimension: {embedding_dim})")
        
        # Initialize LLM
        llm = ChatOllama(model="llama3", temperature=0.7)
        
        logger.success("All components initialized successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize components: {str(e)}")
        logger.error("Make sure Ollama is running and the required models are installed.")
        return False

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    logger.info("Starting up RAG backend...")
    success = initialize_components()
    if not success:
        logger.error("Failed to initialize components. Some endpoints may not work.")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "RAG Document Processing API",
        "status": "running",
        "embeddings_initialized": embeddings is not None,
        "llm_initialized": llm is not None,
        "database_initialized": client and collection is not None
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "components": {
            "embeddings": embeddings is not None,
            "database": client is not None and collection is not None,
            "llm": llm is not None
        },
        "embedding_dimension": embedding_dim
    }

@app.post("/upload", response_model=ProcessResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process a PDF file"""
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    if not all([embeddings, client, collection]):
        raise HTTPException(status_code=503, detail="Backend components not initialized")
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name
    
    try:
        # Load and process PDF
        loader = PyMuPDFLoader(temp_path)
        docs = loader.load()
        
        if not docs:
            return ProcessResponse(
                success=False,
                message="No content found in the PDF file"
            )
        
        logger.info(f"Loaded {len(docs)} pages from PDF")
        
        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,  # Larger chunks for better context
            chunk_overlap=400,  # Larger overlap to maintain context
            separators=["\n\n", "\n", ".", "?", "!", " ", ""],
            length_function=len,
            is_separator_regex=False
        )
        
        # Process each page separately
        all_splits = []
        current_chunk = []
        current_length = 0
        
        for doc in docs:
            content = doc.page_content
            # Split by sections (looking for headers or major breaks)
            sections = content.split('\n\n')
            
            for section in sections:
                if len(section.strip()) > 0:  # Skip empty sections
                    # If adding this section would exceed chunk size, create a new chunk
                    if current_length + len(section) > 2000 and current_chunk:
                        # Join the current chunk and add it
                        chunk_text = '\n\n'.join(current_chunk)
                        chunk_doc = type(doc)(page_content=chunk_text, metadata=doc.metadata)
                        all_splits.append(chunk_doc)
                        # Start new chunk with the current section
                        current_chunk = [section]
                        current_length = len(section)
                    else:
                        # Add to current chunk
                        current_chunk.append(section)
                        current_length += len(section)
        
        # Add the last chunk if it exists
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunk_doc = type(docs[0])(page_content=chunk_text, metadata=docs[0].metadata)
            all_splits.append(chunk_doc)
            
        logger.info(f"Created {len(all_splits)} chunks from {len(docs)} pages")
        if all_splits:
            logger.info(f"First chunk sample: {all_splits[0].page_content[:200]}...")
            logger.info(f"Average chunk size: {sum(len(chunk.page_content) for chunk in all_splits) / len(all_splits):.0f} characters")
        
        # Add to vector database
        texts = [doc.page_content for doc in all_splits]
        embeddings_list = embeddings.embed_documents(texts)
        
        # Create unique IDs for each chunk
        file_base = os.path.splitext(file.filename)[0]
        for i, (text, emb) in enumerate(zip(texts, embeddings_list)):
            doc_id = f"{file_base}_{i}"
            collection.add(
                ids=[doc_id],
                documents=[text],
                embeddings=[emb]
            )
        
        logger.info(f"Successfully processed {len(all_splits)} chunks from {file.filename}")
        
        return ProcessResponse(
            success=True,
            message=f"Successfully processed PDF: {file.filename}",
            document_count=len(all_splits)
        )
        
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        return ProcessResponse(
            success=False,
            message=f"Error processing PDF: {str(e)}"
        )
    
    finally:
        # Clean up temporary file
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        except Exception as e:
            logger.warning(f"Could not delete temporary file: {e}")

@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Query the processed documents"""
    
    if not all([embeddings, collection, llm]):
        raise HTTPException(status_code=503, detail="Backend components not initialized")
    
    try:
        # Generate query embedding
        query_embedding = embeddings.embed_documents([request.question])[0]
        
        # Query the collection
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=request.n_results
        )
        
        if not results['documents'] or not results['documents'][0]:
            return QueryResponse(
                answer="No relevant documents found for your question.",
                sources=[],
                success=True,
                message="No matching documents"
            )
        
        # Combine retrieved documents as context
        context = "\n\n".join(results['documents'][0])
        
        # Generate response using LLM
        chat_prompt = ChatPromptTemplate.from_template(SYSTEM_PROMPT)
        output_parser = StrOutputParser()
        chain = chat_prompt | llm | output_parser
        
        response = chain.invoke({
            "context": context,
            "question": request.question
        })
        
        return QueryResponse(
            answer=response,
            sources=results['documents'][0][:3],  # Return top 3 source chunks
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error querying documents: {str(e)}")
        
        # Try fallback query method
        try:
            logger.info("Trying fallback query method...")
            query_embedding = embeddings.embed_query(request.question)
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=request.n_results
            )
            
            context = "\n\n".join(results['documents'][0])
            
            chat_prompt = ChatPromptTemplate.from_template(SYSTEM_PROMPT)
            output_parser = StrOutputParser()
            chain = chat_prompt | llm | output_parser
            
            response = chain.invoke({
                "context": context,
                "question": request.question
            })
            
            return QueryResponse(
                answer=response,
                sources=results['documents'][0][:3],
                success=True,
                message="Used fallback query method"
            )
            
        except Exception as e2:
            logger.error(f"Fallback also failed: {str(e2)}")
            raise HTTPException(status_code=500, detail=f"Error querying documents: {str(e2)}")

@app.delete("/clear")
async def clear_database():
    """Clear all documents from the database"""
    if not collection:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        # Get all document IDs and delete them
        all_docs = collection.get()
        if all_docs['ids']:
            collection.delete(ids=all_docs['ids'])
            logger.info(f"Cleared {len(all_docs['ids'])} documents from database")
            return {"message": f"Cleared {len(all_docs['ids'])} documents", "success": True}
        else:
            return {"message": "Database was already empty", "success": True}
    except Exception as e:
        logger.error(f"Error clearing database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error clearing database: {str(e)}")

@app.get("/documents/count")
async def get_document_count():
    """Get the number of documents in the database"""
    if not collection:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        count = collection.count()
        return {"count": count, "success": True}
    except Exception as e:
        logger.error(f"Error getting document count: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting document count: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "rag:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )