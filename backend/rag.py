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
from agent_communication import simple_bus, coordinator

# Langchain and database imports
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter

from evaluator import RAGEvaluator
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import json

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

class EvaluationRequest(BaseModel):
    question: str
    answer: str
    context: List[str]
    ground_truth: Optional[str] = None

class CorrectnessEvaluationRequest(BaseModel):
    question: str
    answer: str
    ground_truth: str

class RelevanceEvaluationRequest(BaseModel):
    question: str
    answer: str

class GroundednessEvaluationRequest(BaseModel):
    answer: str
    context: List[str]

class RetrievalRelevanceEvaluationRequest(BaseModel):
    question: str
    retrieved_docs: List[str]

class EvaluationResponse(BaseModel):
    success: bool
    results: Dict[str, Any]
    message: Optional[str] = None

# Add these global variables to your existing globals
evaluator = None

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
    """Initialize embeddings, Chroma client, LLM, and evaluator"""
    global embeddings, client, collection, embedding_dim, llm, evaluator
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
        
        # Initialize evaluator
        evaluator = RAGEvaluator(model_name="llama3", temperature=0)
        
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
    """Query documents without evaluation"""
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
                answer="No relevant documents found. Please upload some documents first.",
                sources=[],
                success=True,
                message="No documents found"
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
        logger.error(f"Error in query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced query endpoint that includes evaluation
@app.post("/query_with_evaluation", response_model=Dict[str, Any])
async def query_documents_with_evaluation(request: QueryRequest, ground_truth: Optional[str] = None):
    """Query documents and automatically evaluate the response"""
    if not all([embeddings, collection, llm, evaluator]):
        raise HTTPException(status_code=503, detail="Components not initialized")
    
    try:
        # Query the collection
        query_embedding = embeddings.embed_query(request.question)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=request.n_results
        )
        
        if not results['documents'][0]:
            return {
                "query_response": {
                    "answer": "No relevant documents found.",
                    "sources": [],
                    "success": True
                },
                "evaluation": None,
                "message": "No documents found for evaluation"
            }
        
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
        
        # Prepare query response
        query_response = {
            "answer": response,
            "sources": results['documents'][0][:3],
            "success": True
        }
        
        # Perform evaluation
        evaluation_results = evaluator.evaluate_complete_rag(
            question=request.question,
            answer=response,
            context=results['documents'][0],
            ground_truth=ground_truth
        )
        
        return {
            "query_response": query_response,
            "evaluation": evaluation_results,
            "message": f"Query processed and evaluated. Overall score: {evaluation_results['overall_score']:.2f}/5"
        }
        
    except Exception as e:
        logger.error(f"Error in query with evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
# Individual evaluation endpoints
@app.post("/evaluate/correctness", response_model=EvaluationResponse)
async def evaluate_correctness(request: CorrectnessEvaluationRequest):
    """Evaluate answer correctness against ground truth"""
    if not evaluator:
        raise HTTPException(status_code=503, detail="Evaluator not initialized")
    
    try:
        result = evaluator.evaluate_correctness(
            question=request.question,
            student_answer=request.answer,
            ground_truth=request.ground_truth
        )
        
        return EvaluationResponse(
            success=True,
            results=result,
            message=f"Correctness evaluation completed: {'Correct' if result['correct'] else 'Incorrect'}"
        )
    except Exception as e:
        logger.error(f"Error in correctness evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/evaluate/relevance", response_model=EvaluationResponse)
async def evaluate_relevance(request: RelevanceEvaluationRequest):
    """Evaluate answer relevance to the question"""
    if not evaluator:
        raise HTTPException(status_code=503, detail="Evaluator not initialized")
    
    try:
        result = evaluator.evaluate_relevance(
            question=request.question,
            answer=request.answer
        )
        
        return EvaluationResponse(
            success=True,
            results=result,
            message=f"Relevance evaluation completed: {result['score']}/5"
        )
    except Exception as e:
        logger.error(f"Error in relevance evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/evaluate/groundedness", response_model=EvaluationResponse)
async def evaluate_groundedness(request: GroundednessEvaluationRequest):
    """Evaluate answer groundedness in the context"""
    if not evaluator:
        raise HTTPException(status_code=503, detail="Evaluator not initialized")
    
    try:
        result = evaluator.evaluate_groundedness(
            answer=request.answer,
            context=request.context
        )
        
        return EvaluationResponse(
            success=True,
            results=result,
            message=f"Groundedness evaluation completed: {'Grounded' if result['grounded'] else 'Not grounded'}"
        )
    except Exception as e:
        logger.error(f"Error in groundedness evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/evaluate/retrieval_relevance", response_model=EvaluationResponse)
async def evaluate_retrieval_relevance(request: RetrievalRelevanceEvaluationRequest):
    """Evaluate retrieval relevance of documents to question"""
    if not evaluator:
        raise HTTPException(status_code=503, detail="Evaluator not initialized")
    
    try:
        result = evaluator.evaluate_retrieval_relevance(
            question=request.question,
            retrieved_docs=request.retrieved_docs
        )
        
        return EvaluationResponse(
            success=True,
            results=result,
            message=f"Retrieval relevance evaluation completed: {result['score']}/5"
        )
    except Exception as e:
        logger.error(f"Error in retrieval relevance evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/evaluate/complete", response_model=EvaluationResponse)
async def evaluate_complete_rag(request: EvaluationRequest):
    """Perform complete RAG evaluation with all metrics"""
    if not evaluator:
        raise HTTPException(status_code=503, detail="Evaluator not initialized")
    
    try:
        result = evaluator.evaluate_complete_rag(
            question=request.question,
            answer=request.answer,
            context=request.context,
            ground_truth=request.ground_truth
        )
        
        return EvaluationResponse(
            success=True,
            results=result,
            message=f"Complete RAG evaluation finished. Overall score: {result['overall_score']:.2f}/5"
        )
    except Exception as e:
        logger.error(f"Error in complete RAG evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Batch evaluation endpoint
@app.post("/evaluate/batch")
async def batch_evaluate(requests: List[EvaluationRequest]):
    """Perform batch evaluation on multiple requests"""
    if not evaluator:
        raise HTTPException(status_code=503, detail="Evaluator not initialized")
    
    try:
        results = []
        for i, request in enumerate(requests):
            logger.info(f"Processing batch evaluation {i+1}/{len(requests)}")
            
            evaluation_result = evaluator.evaluate_complete_rag(
                question=request.question,
                answer=request.answer,
                context=request.context,
                ground_truth=request.ground_truth
            )
            
            results.append({
                "request_id": i,
                "question": request.question,
                "evaluation": evaluation_result
            })
        
        # Calculate batch statistics
        overall_scores = [r["evaluation"]["overall_score"] for r in results]
        batch_stats = {
            "total_evaluations": len(results),
            "average_score": sum(overall_scores) / len(overall_scores),
            "min_score": min(overall_scores),
            "max_score": max(overall_scores),
            "scores": overall_scores
        }
        
        return {
            "success": True,
            "batch_results": results,
            "batch_statistics": batch_stats,
            "message": f"Batch evaluation completed for {len(requests)} requests"
        }
        
    except Exception as e:
        logger.error(f"Error in batch evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check for evaluator
@app.get("/evaluator/health")
async def evaluator_health():
    """Check if evaluator is properly initialized"""
    if evaluator:
        return {
            "status": "healthy",
            "evaluator_initialized": True,
            "model": "llama3",
            "available_evaluations": [
                "correctness", "relevance", "groundedness", "retrieval_relevance", "complete"
            ]
        }
    else:
        return {
            "status": "unhealthy",
            "evaluator_initialized": False,
            "message": "Evaluator not initialized"
        }

@app.get("/agents/status")
async def get_simple_agent_status():
    """Get simple agent status"""
    try:
        status = {}
        for name, info in simple_bus.agents.items():
            status[name] = {
                "status": info["status"],
                "message_count": len(info["messages"])
            }
        
        return {
            "agents": status,
            "shared_data_keys": list(simple_bus.shared_data.keys())
        }
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents/shared_data")
async def get_shared_data():
    """Get all shared data"""
    try:
        data = {}
        for key, info in simple_bus.shared_data.items():
            data[key] = {
                "value": info["value"],
                "updated_by": info["updated_by"],
                "timestamp": info["timestamp"].isoformat()
            }
        return {"shared_data": data}
    except Exception as e:
        logger.error(f"Error getting shared data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents/activities")
async def get_recent_activities(limit: int = 20):
    """Get recent agent activities"""
    try:
        activities = coordinator.get_recent_activities(limit)
        return {
            "activities": [
                {
                    "agent": activity["agent"],
                    "activity": activity["activity"],
                    "timestamp": activity["timestamp"].isoformat(),
                    "details": activity["details"]
                }
                for activity in activities
            ],
            "total_activities": len(activities)
        }
    except Exception as e:
        logger.error(f"Error getting activities: {e}")
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