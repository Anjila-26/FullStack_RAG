# Multi-Agent FullStack RAG Pipeline

This is a comprehensive multi-agent RAG-based chatbot system with advanced features including agent communication, website crawling, performance evaluation, and real-time monitoring.

## Key Features

- 🤖 **Multi-Agent Communication**: Simple message passing system between specialized agents
- 🕷️ **Advanced Website Crawling**: Single URL processing with async HTTP requests
- 📊 **RAG Performance Evaluation**: Comprehensive evaluation system with multiple metrics
- 📈 **Real-time Monitoring**: Agent activity tracking and performance monitoring
- 🔍 **Enhanced Content Extraction**: Advanced text processing with multiple extraction methods
- ⚡ **FastAPI REST API**: Complete API for integration and automation
- 🎯 **Evaluation Metrics**: Correctness, relevance, groundedness, and retrieval quality assessment

---

## Screenshots

Step 1: User uploads the PDF / URL  
<img src="screenshots/landing_page.png" />

Step 2: Landing page for the chat  
<img src="screenshots/chat_page.png" />

Step 3: User asks a question related to the PDF / URL
1. When PDF:  
<img src="screenshots/pdf_answers.png" />
2. When Url:
<img src="screenshots/url_answers.png" />

### Evaluation System in Action
Real-time evaluation on 4 key metrics: Relevance, Groundedness, Retrieval, and Correctness
<img src="screenshots/eval.png" />
<img src="screenshots/evaluation.png" />

---

## Multi-Agent Architecture with Communication

The system implements a **simple message passing architecture** where specialized agents communicate through a central message bus:

### **Agent Communication System**
- **Simple Message Bus**: Central communication hub for all agents
- **Shared Memory**: Agents can share data through a centralized memory system
- **Activity Logging**: System coordinator tracks all agent activities
- **Status Updates**: Real-time agent status monitoring (idle, processing, error)
- **Message History**: Complete audit trail of inter-agent communication

### **Document Processing Agent**
- **Capabilities**: PDF processing, text extraction, document chunking
- **Communication**: Notifies system when processing starts/completes
- **Shared Memory**: Stores processing results for other agents to access
- Uses PyMuPDFLoader for content extraction  
- Advanced document chunking for optimal context
- Metadata preservation and source tracking

### **Web Scraping Agent**
- **Capabilities**: URL scraping, content extraction, HTML parsing
- **Communication**: Reports scraping progress and completion status
- **Shared Memory**: Stores scraped content with metadata
- Uses aiohttp for async HTTP requests
- BeautifulSoup for HTML parsing and cleaning
- Error handling and retry mechanisms

### **RAG Evaluation Agent**
- **Comprehensive Evaluation Metrics:**
  - **Correctness**: Compares answers against ground truth
  - **Relevance**: Measures answer relevance to the question (1-5 scale)
  - **Groundedness**: Checks if answers are supported by retrieved context
  - **Retrieval Relevance**: Evaluates quality of retrieved documents
- **Complete RAG Assessment**: Combined evaluation with overall scoring
- **Batch Evaluation**: Process multiple evaluations simultaneously
- **Real-time Evaluation**: Integrated evaluation with query processing
- **Health Monitoring**: Evaluator status and availability checks

### **System Coordinator Agent**
- **Activity Monitoring**: Logs all agent activities and status changes
- **Message Coordination**: Handles system-wide notifications
- **Health Tracking**: Monitors agent performance and availability
- **Error Handling**: Manages system-wide error reporting and recovery

### **RAG Orchestrator**
- Coordinates between all agents using the message bus
- Manages the vector database (ChromaDB)
- Handles embeddings and LLM interactions
- Provides unified API endpoints

---

## Agent Communication Flow

### **Message Passing**
```
Document Agent → System Coordinator: "Started processing PDF"
Document Agent → Shared Memory: Store processing results
Document Agent → System Coordinator: "PDF processing completed"
```

### **Shared Memory Usage**
```
Agent A: set_shared_data("processed_pdf_example.pdf", result_data)
Agent B: get_shared_data("processed_pdf_example.pdf") → retrieves result_data
```

### **Activity Tracking**
All agent activities are logged by the system coordinator:
- PDF processing started/completed
- URL scraping started/completed
- Content processing activities
- Error events and recovery

---

## Backend API Endpoints

### **Core Functionality**
- `POST /upload` — Upload and process a PDF file (uses Document Agent)
- `POST /url` — Process content from a webpage (uses Scraping Agent)
- `POST /query` — Query the processed documents
- `POST /query_with_evaluation` — Query with automatic evaluation
- `DELETE /clear` — Clear all documents from the database

### **Evaluation Endpoints**
- `POST /evaluate/correctness` — Evaluate answer correctness
- `POST /evaluate/relevance` — Evaluate answer relevance
- `POST /evaluate/groundedness` — Evaluate answer groundedness
- `POST /evaluate/retrieval_relevance` — Evaluate retrieval quality
- `POST /evaluate/complete` — Complete RAG evaluation
- `POST /evaluate/batch` — Batch evaluation processing
- `GET /evaluator/health` — Check evaluator status

### **Agent Communication Endpoints**
- `GET /agents/status` — Get all agent statuses and message counts
- `GET /agents/shared_data` — View all shared data between agents
- `GET /agents/activities` — Get recent agent activity logs

### **Technologies**
- FastAPI (REST API)
- Langchain (document processing, embeddings, LLM)
- ChromaDB (vector database)
- Ollama (local LLM and embedding models)
- PyMuPDFLoader (PDF parsing)
- BeautifulSoup4 (web scraping)
- aiohttp (async HTTP client)
- Loguru (logging)
- **Custom Agent Communication System**: Simple message bus with shared memory

---

## Frontend Features

### **Chat Interface**
- **Clean, Modern Design**: Responsive chatbot interface with gradient backgrounds
- **Real-time Messaging**: Instant message sending and receiving
- **Markdown Support**: Rich text rendering for responses
- **Loading Indicators**: Visual feedback during processing

### **Evaluation Interface**
- **Evaluation Toggle**: Easy on/off switch for evaluation mode
- **Evaluation Panel**: Dedicated settings panel with configuration options
- **Ground Truth Input**: Optional field for providing expected answers
- **Real-time Evaluation Display**: Immediate evaluation results with each response

### **Evaluation Results Display**
- **Overall Score**: Combined evaluation score (x/5)
- **Metric Breakdown**: Individual scores for each evaluation metric:
  - **Correctness**: Green/Red badges with explanations
  - **Relevance**: Blue badges with 1-5 scoring
  - **Groundedness**: Green/Red badges for context support
  - **Retrieval Relevance**: Purple badges with 1-5 scoring
- **Detailed Explanations**: Full explanations for each metric result

---

## How the Multi-Agent System Works

### **1. Document Processing Flow**
```
User uploads PDF → Document Agent receives task
Document Agent → System: "Starting PDF processing"
Document Agent → Shared Memory: Store processing results
Document Agent → System: "PDF processing completed with X chunks"
RAG Orchestrator → ChromaDB: Store processed chunks
```

### **2. URL Processing Flow**
```
User submits URL → Scraping Agent receives task
Scraping Agent → System: "Starting URL scraping"
Scraping Agent → Shared Memory: Store scraped content
Scraping Agent → System: "URL scraping completed"
RAG Orchestrator → Text Splitter → ChromaDB: Process and store chunks
```

### **3. Query Processing with Evaluation**
```
User asks question → RAG Orchestrator retrieves relevant chunks
RAG Orchestrator → LLM: Generate response
RAG Orchestrator → Evaluation Agent: Evaluate response quality
Evaluation Agent → User: Return answer with evaluation metrics
```

### **4. Agent Coordination Benefits**
- **Parallel Processing**: Multiple agents can work simultaneously
- **Status Transparency**: Real-time visibility into system operations
- **Error Isolation**: Agent failures don't crash the entire system
- **Scalability**: Easy to add new agents with specific capabilities
- **Monitoring**: Complete audit trail of all system activities

---

## Installation and Setup

### **Running the Backend**

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the FastAPI backend:
   ```bash
   python rag.py
   ```

3. Make sure Ollama is running with required models:
   - `mxbai-embed-large` for embeddings
   - `llama3` for LLM and evaluation

4. **Monitor Agent Communication:**
   - Visit `http://localhost:8000/agents/status` to see agent statuses
   - Visit `http://localhost:8000/agents/activities` to view recent activities
   - Visit `http://localhost:8000/agents/shared_data` to see shared memory

### **Running the Frontend**

1. Navigate to the chatbot directory:
   ```bash
   cd chatbot
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. **Access the application:**
   - Open `http://localhost:3000`
   - Upload PDFs or process URLs
   - Enable evaluation mode for quality assessment
   - Monitor agent activities through the backend endpoints

---

## Advanced Features

### **Agent Communication Monitoring**
- Real-time agent status tracking
- Message history between agents
- Shared memory inspection
- Activity logging and audit trails

### **Evaluation System**
- **Correctness**: Binary evaluation against ground truth
- **Relevance**: 1-5 scale rating of answer quality
- **Groundedness**: Checks for hallucinations and context support
- **Retrieval Relevance**: Quality of document retrieval

### **User Experience**
- Drag & drop PDF uploads
- URL processing for web content
- Real-time evaluation feedback
- Detailed metric explanations
- Responsive design for all devices

---

## System Benefits

✅ **Modularity**: Each agent has specific responsibilities  
✅ **Scalability**: Easy to add new agents and capabilities  
✅ **Transparency**: Complete visibility into system operations  
✅ **Reliability**: Agent isolation prevents cascading failures  
✅ **Monitoring**: Real-time status and activity tracking  
✅ **Quality Assurance**: Comprehensive evaluation system  
✅ **User Experience**: Modern, responsive interface with rich feedback  

This multi-agent architecture provides a robust, scalable, and transparent RAG system with advanced evaluation capabilities.
  - **Correctness**: Green/Red badges with explanations
  - **Relevance**: Blue badges with 1-5 scoring
  - **Groundedness**: Green/Red badges for context support
  - **Retrieval Relevance**: Purple badges with 1-5 scoring
- **Detailed Explanations**: Full explanations for each metric result

### **User Experience Features**
- **Drag & Drop**: Easy PDF file uploading
- **URL Processing**: Direct webpage content processing
- **Auto-scroll**: Automatic scrolling to latest messages
- **Error Handling**: Graceful error messages and recovery
- **Responsive Design**: Works on desktop and mobile devices

---

#### Running the Backend

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the FastAPI backend:
   ```bash
   python rag.py
   ```

3. Make sure Ollama is running and the required models are installed.

4. **Optional: Run Evaluation Tests**
   ```bash
   python test_evaluation.py
   ```
   This will run a simple evaluation test to verify the evaluation system is working.

---

#### Running the Frontend

1. Go to the `chatbot` directory:
   ```bash
   cd chatbot
   ```

2. Install dependencies:
   ```bash
   npm install
   # or
   yarn install
   ```

3. Start the Next.js development server:
   ```bash
   npx next dev
   # or
   yarn dev
   ```

4. **Access the application:**
   - Open your browser and go to `http://localhost:3000`
   - Upload PDFs or process URLs on the landing page
   - Use the chat interface with optional evaluation features:
     - Click the "Evaluation" button to access settings
     - Toggle "Evaluation ON/OFF" to enable/disable evaluation
     - Provide ground truth for correctness evaluation (optional)
     - View detailed evaluation results with each response

---

#### Notes

- The backend expects Ollama to be running locally with the required models (`mxbai-embed-large` for embeddings, `llama3` for LLM).
- The evaluation system uses the same `llama3` model for assessment.
- You can clear all uploaded documents using the `/clear` endpoint.
- The backend is CORS-enabled for local development.
- Use `/query` for regular queries or `/query_with_evaluation` for automatic evaluation.
- The evaluation system provides detailed explanations for each metric.
- **Frontend Features:**
  - Toggle evaluation mode on/off with the evaluation button
  - Provide ground truth in the evaluation panel for correctness assessment
  - View real-time evaluation results with color-coded metrics
  - All evaluation results include detailed explanations
  - The interface automatically switches between regular and evaluation modes

---



