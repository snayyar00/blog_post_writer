"""Memory manager for storing and retrieving company-related content."""

from typing import Dict, List, Optional, Any, Union
from src.utils.openai_blog_writer import BlogPost
from src.utils.logging_manager import log_info, log_error, log_debug
from dataclasses import dataclass
from datetime import datetime
import json
import os

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_core.memory import BaseMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

@dataclass
class CompanyContext:
    name: str
    description: str
    industry: str
    values: List[str]
    tone_of_voice: str
    target_audience: List[str]
    key_products: List[str]
    competitors: List[str]
    unique_selling_points: List[str]
    last_updated: datetime

class CompanyMemoryManager:
    def __init__(self, persist_directory: str = "./company_memory"):
        self.persist_directory = persist_directory
        self.embeddings = OpenAIEmbeddings()
        log_debug("Initializing company memory manager", "MEMORY")
        self._initialize_storage()
        
    def _initialize_storage(self):
        """Initialize or load the vector store."""
        if os.path.exists(self.persist_directory):
            try:
                # Set allow_dangerous_deserialization to True since we're loading our own files
                self.vector_store = FAISS.load_local(
                    self.persist_directory,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                log_info("Successfully loaded existing vector store", "MEMORY")
            except Exception as e:
                log_error(f"Error loading vector store: {str(e)}", "MEMORY")
                # Create a new vector store if loading fails
                self.vector_store = FAISS.from_texts(
                    ["Initialize company memory after load failure"],
                    self.embeddings
                )
        else:
            # Create empty vector store
            self.vector_store = FAISS.from_texts(
                ["Initialize company memory"],
                self.embeddings
            )
            os.makedirs(self.persist_directory, exist_ok=True)
            log_info("Created new vector store for company memory", "MEMORY")
            
    def add_company_context(self, context: CompanyContext):
        """Add or update company context in the memory."""
        # Convert context to document format
        doc_content = json.dumps(context.__dict__, default=str)
        doc = Document(
            page_content=doc_content,
            metadata={
                "type": "company_context",
                "company_name": context.name,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Add to vector store
        self.vector_store.add_documents([doc])
        self.vector_store.save_local(self.persist_directory)
        log_info(f"Added company context for {context.name}", "MEMORY")
        
    def add_company_documents(self, documents: List[str], metadata: Dict):
        """Add company-related documents to memory."""
        docs = [
            Document(
                page_content=doc,
                metadata={
                    **metadata,
                    "timestamp": datetime.now().isoformat()
                }
            )
            for doc in documents
        ]
        
        self.vector_store.add_documents(docs)
        self.vector_store.save_local(self.persist_directory)
        log_info(f"Added {len(documents)} company documents to memory", "MEMORY")
        
    def get_relevant_context(self, query: str, k: int = 5) -> List[Document]:
        """Retrieve relevant company context based on query."""
        log_debug(f"Searching for context matching query: {query}", "MEMORY")
        results = self.vector_store.similarity_search(query, k=k)
        log_debug(f"Found {len(results)} relevant documents", "MEMORY")
        return results
        
    def get_company_tone(self, company_name: str) -> Optional[str]:
        """Get company's tone of voice."""
        log_debug(f"Retrieving tone of voice for company: {company_name}", "MEMORY")
        results = self.vector_store.similarity_search(
            f"tone of voice for {company_name}",
            k=1
        )
        
        if results:
            try:
                context = json.loads(results[0].page_content)
                tone = context.get("tone_of_voice")
                if tone:
                    log_debug(f"Found tone of voice: {tone}", "MEMORY")
                    return tone
            except:
                log_error(f"Error parsing tone of voice for {company_name}", "MEMORY")
        log_debug(f"No tone of voice found for {company_name}", "MEMORY")
        return None
        
    async def store_blog_post(self, blog_post: Union[BlogPost, Any]) -> None:
        """Store a blog post in memory.
        
        Args:
            blog_post: The blog post object to store
        """
        try:
            # Validate blog post attributes
            if not hasattr(blog_post, 'content'):
                raise ValueError("Blog post must have 'content' attribute")
            if not hasattr(blog_post, 'title'):
                raise ValueError("Blog post must have 'title' attribute")
                
            # Convert blog post to string representation
            content = str(blog_post.content)
            
            # Build metadata with validation
            metadata = {
                "type": "blog_post",
                "title": str(blog_post.title),
                "keywords": list(getattr(blog_post, 'keywords', [])),
                "metrics": (blog_post.metrics.dict() if hasattr(blog_post.metrics, 'dict') 
                          else getattr(blog_post.metrics, '__dict__', {})
                          if hasattr(blog_post.metrics, '__dict__')
                          else getattr(blog_post, 'metrics', {})),
                "timestamp": datetime.now().isoformat()
            }
            
            log_debug(f"Storing blog post: {metadata['title']}", "MEMORY")
            
            # Store in vector store
            doc = Document(
                page_content=content,
                metadata=metadata
            )
            
            # Store in vector store with error handling
            try:
                self.vector_store.add_documents([doc])
                self.vector_store.save_local(self.persist_directory)
                log_info(f"Successfully stored blog post: {metadata['title']}", "MEMORY")
            except Exception as e:
                log_error(f"Failed to store blog post in vector store: {str(e)}", "MEMORY")
                raise
            
        except Exception as e:
            from src.utils.logging_manager import log_error
            log_error(f"Error storing blog post in memory: {str(e)}", "MEMORY")
            raise
            
    def store_memory(self, content: str, metadata: Dict, memory_type: str = None):
        """Store memory content with associated metadata.
        
        Args:
            content: The content to store
            metadata: Metadata associated with the content
            memory_type: Optional type of memory (research, blog, etc.)
        """
        # Add memory_type to metadata if provided
        if memory_type:
            metadata["memory_type"] = memory_type
            
        doc = Document(
            page_content=content,
            metadata={
                **metadata,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Add to vector store
        try:
            self.vector_store.add_documents([doc])
            self.vector_store.save_local(self.persist_directory)
            log_info(f"Stored memory content of type: {memory_type or 'general'}", "MEMORY")
        except Exception as e:
            log_error(f"Failed to store memory content: {str(e)}", "MEMORY")
            raise
            
    def store_research(self, research_data: Dict[str, Any], topic: str):
        """Store research data in memory.
        
        Args:
            research_data: Dictionary containing research findings
            topic: Topic of the research
        """
        try:
            # Convert research data to string if it's a dict
            if isinstance(research_data, dict):
                content = json.dumps(research_data)
            else:
                content = str(research_data)
                
            metadata = {
                "type": "research",
                "topic": topic,
                "timestamp": datetime.now().isoformat()
            }
            
            self.store_memory(content, metadata, memory_type="research")
            log_info(f"Stored research data for topic: {topic}", "MEMORY")
            return True
        except Exception as e:
            log_error(f"Failed to store research data: {str(e)}", "MEMORY")
            return False
            
    def get_research(self, topic: str = None, limit: int = 5):
        """Get research data from memory.
        
        Args:
            topic: Optional topic to filter by
            limit: Maximum number of results to return
            
        Returns:
            Research data as a list of results
        """
        query = "research"
        if topic:
            query += f" {topic}"
            
        log_debug(f"Retrieving research data for query: {query}", "MEMORY")
        results = self.vector_store.similarity_search(query, k=limit)
        
        research_data = []
        for doc in results:
            if "type" in doc.metadata and doc.metadata["type"] == "research":
                try:
                    # Try to parse as JSON first
                    content = json.loads(doc.page_content)
                except:
                    # If that fails, use raw content
                    content = doc.page_content
                    
                research_data.append({
                    "content": content,
                    "topic": doc.metadata.get("topic", "Unknown"),
                    "timestamp": doc.metadata.get("timestamp")
                })
                
        log_debug(f"Found {len(research_data)} research results", "MEMORY")
        return research_data

class ConversationMemory(BaseMemory):
    def __init__(self, company_name: str, session_id: str):
        self.company_name = company_name
        self.session_id = session_id
        self.chat_history = RedisChatMessageHistory(
            session_id=session_id,
            url=os.getenv("REDIS_URL", "redis://localhost:6379")
        )
        log_debug(f"Initialized conversation memory for company: {company_name}", "MEMORY")
        
    def load_memory_variables(self, inputs: Dict) -> Dict[str, List]:
        """Load conversation history."""
        log_debug("Loading conversation history", "MEMORY")
        return {
            "chat_history": self.chat_history.messages
        }
        
    def save_context(self, inputs: Dict, outputs: Dict):
        """Save interactions to memory."""
        if inputs.get("human_input"):
            self.chat_history.add_message(
                HumanMessage(content=inputs["human_input"])
            )
            log_debug("Saved human message to conversation history", "MEMORY")
        if outputs.get("ai_output"):
            self.chat_history.add_message(
                AIMessage(content=outputs["ai_output"])
            )
            log_debug("Saved AI message to conversation history", "MEMORY")
            
    def clear(self):
        """Clear conversation history."""
        self.chat_history.clear()
        log_info("Cleared conversation history", "MEMORY")

# Example usage:
"""
# Initialize memory manager
memory_manager = CompanyMemoryManager()

# Add company context
context = CompanyContext(
    name="TechCorp",
    description="Leading AI software company",
    industry="Technology",
    values=["Innovation", "Quality", "Customer-first"],
    tone_of_voice="Professional yet approachable",
    target_audience=["Enterprise businesses", "Tech professionals"],
    key_products=["AI Platform", "Data Analytics Suite"],
    competitors=["CompetitorA", "CompetitorB"],
    unique_selling_points=["Advanced AI capabilities", "Excellent support"],
    last_updated=datetime.now()
)
memory_manager.add_company_context(context)

# Add company documents
documents = [
    "Our mission is to transform businesses through AI...",
    "TechCorp's core values emphasize innovation..."
]
memory_manager.add_company_documents(
    documents,
    {"type": "company_docs", "category": "mission_values"}
)

# Retrieve context for content generation
relevant_docs = memory_manager.get_relevant_context(
    "What is the company's approach to innovation?"
)
"""
