"""
Initialize the company memory with a basic FAISS index.
"""

import os
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

def initialize_memory():
    """Initialize the company memory with a basic FAISS index."""
    print("Initializing company memory...")
    
    # Create memory directory if it doesn't exist
    memory_dir = "./company_memory"
    os.makedirs(memory_dir, exist_ok=True)
    
    # Initialize embeddings
    embeddings = OpenAIEmbeddings()
    
    # Create a simple document to initialize the index
    docs = [Document(
        page_content="Initialize company memory",
        metadata={"type": "initialization", "timestamp": "2025-03-08"}
    )]
    
    # Create and save the vector store
    vector_store = FAISS.from_documents(docs, embeddings)
    vector_store.save_local(memory_dir)
    
    print(f"Company memory initialized at {memory_dir}")

if __name__ == "__main__":
    initialize_memory()