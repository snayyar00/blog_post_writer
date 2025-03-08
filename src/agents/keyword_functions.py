"""Standalone keyword generation functions."""

from typing import Dict, List, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

def generate_keywords(topic: str, context_data: Dict[str, str]) -> List[str]:
    """
    Generate keywords for a given topic using context data.
    
    Args:
        topic: The main topic to generate keywords for
        context_data: Dictionary of context data from files
        
    Returns:
        List of generated keywords
    """
    llm = ChatOpenAI(model="gpt-4")
    parser = JsonOutputParser()
    
    # Extract relevant context
    context_text = "\n\n".join(context_data.values())
    
    prompt = PromptTemplate.from_template("""
        Generate a list of SEO-optimized keywords related to this topic: {topic}
        
        Use the following context information to inform your keyword selection:
        {context}
        
        Generate 10-15 keywords that are:
        1. Highly relevant to the topic
        2. Have good search potential
        3. Range from short-tail to long-tail keywords
        4. Include question-based keywords where appropriate
        
        Format response as a JSON array of strings.
    """)
    
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({"topic": topic, "context": context_text[:2000]})
        return result if isinstance(result, list) else []
    except Exception as e:
        print(f"Error generating keywords: {str(e)}")
        # Fallback to basic keywords if parsing fails
        return [topic, f"{topic} best practices", f"{topic} guide", f"how to {topic}", f"what is {topic}"]
