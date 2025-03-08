"""Memory manager using Memoripy for storing and retrieving research results."""

import os
from typing import Dict, List, Any, Optional
import json
from pathlib import Path
from datetime import datetime
import numpy as np
import faiss

from memoripy import MemoryManager, JSONStorage
from memoripy.implemented_models import OpenAIChatModel, OpenAIEmbeddingModel

class ResearchMemoryManager:
    """Memory manager for storing and retrieving research results using Memoripy."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the memory manager with Memoripy.
        
        Args:
            api_key: OpenAI API key (defaults to environment variable)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
            
        # Create memory directory if it doesn't exist
        self.memory_dir = Path("./memory")
        self.memory_dir.mkdir(exist_ok=True)
        
        # Initialize Memoripy components
        storage = JSONStorage(str(self.memory_dir / "research_memory.json"))
        chat_model = OpenAIChatModel(self.api_key, "gpt-4")
        embedding_model = OpenAIEmbeddingModel(self.api_key)
        
        self.memory_manager = MemoryManager(
            chat_model=chat_model,
            embedding_model=embedding_model,
            storage=storage
        )
        
        # Initialize Faiss index
        self.index = faiss.IndexFlatL2(768)  # Assuming 768 is the dimensionality of the embeddings

        # Load Faiss index if it exists
        index_file = self.memory_dir / 'index.faiss'
        if index_file.exists():
            self.index = faiss.read_index(str(index_file))

    def add_to_index(self, embedding: np.ndarray, topic: str):
        """
        Add an embedding to the Faiss index.
        
        Args:
            embedding: The embedding vector to add
            topic: The topic associated with the embedding
        """
        self.index.add(embedding)
        print(f"Added embedding for topic '{topic}' to Faiss index.")

    def save_index(self):
        """
        Save the Faiss index to a file.
        """
        faiss.write_index(self.index, str(self.memory_dir / 'index.faiss'))
        print("Faiss index saved.")

    def store_research_results(self, research_results: Dict[str, Any], topic: str) -> bool:
        """
        Store research results in memory using Memoripy.
        
        Args:
            research_results: Dictionary containing research findings
            topic: The topic being researched
            
        Returns:
            Boolean indicating success or failure
        """
        try:
            # Convert research results to string format for embedding
            if isinstance(research_results, dict):
                content_str = json.dumps(research_results)
            else:
                content_str = str(research_results)
                
            # Extract concepts from the research content
            concepts = self.memory_manager.extract_concepts(content_str)
            
            # Generate embedding for the content
            embedding = self.memory_manager.get_embedding(content_str)
            
            # Add embedding to Faiss index
            self.add_to_index(embedding, topic)
            
            # Store as an interaction (using topic as prompt and research as response)
            # Memoripy expects positional arguments, not keyword arguments
            self.memory_manager.add_interaction(
                f"Research on: {topic}",  # prompt
                content_str,              # response
                embedding,                # embedding
                concepts                  # concepts
            )
            
            print(f"Research results for '{topic}' stored in memory")
            return True
            
        except Exception as e:
            print(f"Error storing research results: {str(e)}")
            return False
            
    def retrieve_relevant_research(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant research based on a query.
        
        Args:
            query: The query to search for relevant research
            limit: Maximum number of results to return
            
        Returns:
            List of relevant research results
        """
        try:
            # Retrieve relevant interactions
            relevant_interactions = self.memory_manager.retrieve_relevant_interactions(
                query, 
                limit=limit
            )
            
            # Format the results
            results = []
            for interaction in relevant_interactions:
                try:
                    # Try to parse the response as JSON
                    content = json.loads(interaction.response)
                except:
                    # If not valid JSON, use as string
                    content = interaction.response
                    
                results.append({
                    "topic": interaction.prompt.replace("Research on: ", ""),
                    "content": content,
                    "timestamp": interaction.timestamp,
                    "relevance_score": interaction.relevance_score
                })
                
            return results
            
        except Exception as e:
            print(f"Error retrieving research: {str(e)}")
            return []
