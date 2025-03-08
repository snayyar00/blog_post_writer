"""Memory manager for storing and retrieving company-related content."""

from typing import Dict, List, Optional
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
            except Exception as e:
                print(f"Error loading vector store: {str(e)}")
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
        
    def get_relevant_context(self, query: str, k: int = 5) -> List[Document]:
        """Retrieve relevant company context based on query."""
        return self.vector_store.similarity_search(query, k=k)
        
    def get_company_tone(self, company_name: str) -> Optional[str]:
        """Get company's tone of voice."""
        results = self.vector_store.similarity_search(
            f"tone of voice for {company_name}",
            k=1
        )
        
        if results:
            try:
                context = json.loads(results[0].page_content)
                return context.get("tone_of_voice")
            except:
                return None
        return None
        
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
        self.vector_store.add_documents([doc])
        self.vector_store.save_local(self.persist_directory)

class ConversationMemory(BaseMemory):
    def __init__(self, company_name: str, session_id: str):
        self.company_name = company_name
        self.session_id = session_id
        self.chat_history = RedisChatMessageHistory(
            session_id=session_id,
            url=os.getenv("REDIS_URL", "redis://localhost:6379")
        )
        
    def load_memory_variables(self, inputs: Dict) -> Dict[str, List]:
        """Load conversation history."""
        return {
            "chat_history": self.chat_history.messages
        }
        
    def save_context(self, inputs: Dict, outputs: Dict):
        """Save interactions to memory."""
        if inputs.get("human_input"):
            self.chat_history.add_message(
                HumanMessage(content=inputs["human_input"])
            )
        if outputs.get("ai_output"):
            self.chat_history.add_message(
                AIMessage(content=outputs["ai_output"])
            )
            
    def clear(self):
        """Clear conversation history."""
        self.chat_history.clear()

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
