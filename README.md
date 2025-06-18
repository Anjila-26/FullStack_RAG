### FullStack RAG
This is the RAG based chatbot made using Langchain, ChromaDB, and locally for using OLLAMA(WE can use OpenAI or Gemini key easily instead of OLLAMA).

Steps are :

1. PDF Upload : We upload the pdf and the parsing and chunking start, use of PyMuPDFLoader and then divide them into the chunks.
2. Vector Database :  Use of the ChromaDB for the vectorstore of the chunk embeddings and indexing.
3. Query Initialization : User sends their Query about the pdf in anyform they like.
4. Retrieval : ChromaDB has the retrival process using the semantic search and we retrive top_n results as much we wish.
5. LLM Process : So, we passes the results we get from retrival to LLM to get the answers.

Here are the Screenshots of the project :

Step 1 : User Uploads the PDF : 
<img src = 'screenshots/landing_page.png>'/>

Step 2:  Landing Page for the chat:
<img src = 'screenshots/chat_page.png>'/>

Step 3: User Ask the question related to the PDF:
<img src = 'screenshots/chats.png>'/>


