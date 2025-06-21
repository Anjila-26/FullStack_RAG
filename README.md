### FullStack RAG

This is a multi-agent RAG-based chatbot system made using Langchain, ChromaDB, and OLLAMA (you can easily use OpenAI or Gemini instead of OLLAMA).

---

#### Multi-Agent Architecture

The system uses a specialized multi-agent architecture:

- **Document Processing Agent:**
  - Handles PDF document processing and parsing
  - Uses PyMuPDFLoader for content extraction
  - Manages document chunking for optimal context

- **Web Scraping Agent:**
  - Handles webpage content extraction
  - Uses aiohttp for async HTTP requests
  - BeautifulSoup for HTML parsing and cleaning
  - Converts web content to processable text

- **RAG Orchestrator:**
  - Coordinates between agents
  - Manages the vector database (ChromaDB)
  - Handles embeddings and LLM interactions
  - Provides unified API endpoints

---

#### Features

- **Document Processing:**
  - PDF Upload and parsing
  - Web page content extraction
  - Intelligent text chunking
- **Vector Database:** ChromaDB stores chunk embeddings and handles indexing
- **Query Processing:** Semantic search and context-aware responses
- **Multi-Source Support:** Process both PDFs and web URLs

---

#### Backend (FastAPI)

- **Endpoints:**
  - `POST /upload` — Upload and process a PDF file
  - `POST /url` — Process content from a webpage
  - `POST /query` — Query the processed documents
  - `DELETE /clear` — Clear all documents from the database
  - `GET /documents/count` — Get the number of documents
  - `GET /health` — Health check for backend components
  - `GET /` — Basic status endpoint

- **Technologies:**
  - FastAPI (REST API)
  - Langchain (document processing, embeddings, LLM)
  - ChromaDB (vector database)
  - Ollama (local LLM and embedding models)
  - PyMuPDFLoader (PDF parsing)
  - BeautifulSoup4 (web scraping)
  - aiohttp (async HTTP client)
  - Loguru (logging)

- **How it works:**
  1. **Startup:** Initializes all agents and components
  2. **Input Processing:** 
     - Document Agent processes PDFs
     - Scraping Agent processes URLs
  3. **Storage:** Content is chunked and stored in ChromaDB
  4. **Query:** Orchestrator manages retrieval and response generation

---

#### Steps

1. **PDF Upload:** Upload a PDF, which is parsed and chunked using PyMuPDFLoader.
2. **Web URL Processing:** Submit a web URL for content extraction and processing.
3. **Vector Database:** ChromaDB stores chunk embeddings and handles indexing.
4. **Query:** User asks any question about the PDF or web content.
5. **Retrieval:** ChromaDB retrieves top-N relevant chunks using semantic search.
6. **LLM Process:** Retrieved chunks are passed to the LLM to generate an answer.

---

#### Agent Interaction Flow

1. **Document Input:**
   - PDF files → Document Processing Agent
   - Web URLs → Web Scraping Agent

2. **Content Processing:**
   - **Document Agent:**
     - Extracts text from PDFs
     - Splits content into optimal chunks
     - Maintains document structure
   
   - **Scraping Agent:**
     - Fetches webpage content asynchronously
     - Cleans HTML and extracts text
     - Handles different webpage structures

3. **RAG Orchestrator:**
   - Receives processed content from both agents
   - Generates embeddings using Ollama
   - Stores in ChromaDB with metadata
   - Handles user queries:
     1. Embeds the question
     2. Retrieves relevant chunks
     3. Generates contextual response using LLM

This multi-agent architecture allows for:
- Parallel processing of different content types
- Specialized handling for each source
- Unified query interface for users
- Scalable and maintainable codebase

---

#### Screenshots

Step 1: User uploads the PDF / URL  
<img src="screenshots/landing_page.png" />

Step 2: Landing page for the chat  
<img src="screenshots/chat_page.png" />

Step 3: User asks a question related to the PDF / URL
1. When PDF:  
<img src="screenshots/pdf_answers.png" />
2. When Url:
<img src="screenshots/url_answers.png" />

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
   npm run dev
   # or
   yarn dev
   ```

---

#### Notes

- The backend expects Ollama to be running locally with the required models (`mxbai-embed-large` for embeddings, `llama3` for LLM).
- You can clear all uploaded documents using the `/clear` endpoint.
- The backend is CORS-enabled for local development.

---



