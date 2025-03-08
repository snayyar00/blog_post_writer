"""Standalone functions for content processing."""

import os
from typing import Dict, List, Any, Union
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

def generate_outline(keyword: str, research_results: Dict[str, Any], competitor_insights: Dict[str, Any], content_type: str = "standard") -> List[str]:
    """
    Generate a blog post outline based on keyword, research, and competitor insights.
    
    Args:
        keyword: Main keyword for the blog post
        research_results: Dictionary containing research findings
        competitor_insights: Dictionary containing competitor analysis results
        content_type: Type of content to generate (standard, journalistic, technical)
        
    Returns:
        List of outline sections as strings
    """
    # Initialize the LLM
    llm = ChatOpenAI(model="gpt-4")
    
    # Create the prompt for outline generation
    outline_prompt = PromptTemplate.from_template("""
    You are an expert content strategist tasked with creating an effective blog post outline.
    
    MAIN KEYWORD: {keyword}
    
    RESEARCH FINDINGS:
    {research_findings}
    
    COMPETITOR INSIGHTS:
    {competitor_insights}
    
    CONTENT TYPE: {content_type}
    
    Please create a comprehensive blog post outline that includes:
    
    1. An engaging title that includes the main keyword
    2. TLDR (Too Long; Didn't Read) section - a brief summary of the article
    3. Introduction section
    4. 4-6 main sections with descriptive headings
    5. A "Crazy Facts" section that includes surprising or interesting facts about the topic
    6. Conclusion section
    
    Each section should address key aspects of the topic and incorporate insights from the research.
    Format your response as a list of section headings only, one per line.
    """)
    
    # Create and execute the chain
    chain = outline_prompt | llm | StrOutputParser()
    
    try:
        # Convert research results to string format
        if 'findings' in research_results and isinstance(research_results['findings'], list):
            research_str = "\n".join([f"- {finding.get('content', '')}" for finding in research_results['findings']])
        elif isinstance(research_results, dict):
            research_str = "\n".join([f"- {k}: {v}" for k, v in research_results.items() if k != 'findings'])
        else:
            research_str = str(research_results)
        
        # Convert competitor insights to string format
        competitor_str = "\n".join([f"- {k}: {v}" for k, v in competitor_insights.items()]) if isinstance(competitor_insights, dict) else str(competitor_insights)
        
        # Generate outline
        result = chain.invoke({
            "keyword": keyword,
            "research_findings": research_str[:2000],  # Limit content length
            "competitor_insights": competitor_str[:2000],  # Limit content length
            "content_type": content_type
        })
        
        # Parse the result into a list of sections
        sections = [line.strip() for line in result.split('\n') if line.strip()]
        
        return sections
        
    except Exception as e:
        print(f"Error generating outline: {str(e)}")
        # Return a basic outline as fallback
        return [
            f"Title: Complete Guide to {keyword}",
            "Introduction",
            f"What is {keyword}?",
            f"Benefits of {keyword}",
            f"How to Implement {keyword}",
            f"Best Practices for {keyword}",
            "Conclusion"
        ]


def generate_sections(outline: List[str], research_results: Dict[str, Any], keyword: str, content_type: str = "standard") -> str:
    """
    Generate content for each section of the blog post outline.
    
    Args:
        outline: List of section headings
        research_results: Dictionary containing research findings
        keyword: Main keyword for the blog post
        content_type: Type of content to generate (standard, journalistic, technical)
        
    Returns:
        Complete blog post content as a string
    """
    # Initialize the LLM
    llm = ChatOpenAI(model="gpt-4")
    
    # Create the prompt for section content generation based on content type
    base_instructions = """
    1. Be comprehensive and informative
    2. Include the main keyword and related terms naturally
    3. Be engaging and reader-friendly
    4. Include examples and practical advice where appropriate
    5. ALWAYS include a TLDR section at the beginning that summarizes the key points in 2-3 sentences
    6. ALWAYS include a "Crazy Facts" section with 3-5 surprising or interesting facts about the topic
    """
    
    # Add content-type specific instructions
    if content_type == "journalistic":
        specific_instructions = """
    7. Include research-backed statistics and cite sources properly
    8. Present a balanced view with multiple perspectives
    9. Use a more formal, authoritative tone
    """
    elif content_type == "technical":
        specific_instructions = """
    7. Focus on technical details and implementation steps
    8. Include code examples or technical diagrams where relevant
    9. Use a precise, clear explanation style
    """
    else:  # standard
        specific_instructions = """
    7. Focus on practical applications and takeaways
    8. Use a conversational, approachable tone
    9. Emphasize benefits and solutions
    """
    
    section_prompt = PromptTemplate.from_template("""
    You are an expert content writer tasked with creating comprehensive blog post content.
    
    BLOG POST OUTLINE:
    {outline}
    
    MAIN KEYWORD: {keyword}
    
    RESEARCH FINDINGS:
    {research_findings}
    
    CONTENT TYPE: {content_type}
    
    Please write detailed content for each section in the outline. The content should:
    
    {instructions}
    
    Format your response as a complete blog post with proper headings (use # for the title, ## for main sections, ### for subsections).
    Make sure the TLDR section appears immediately after the title and before the introduction.
    """)
    
    # Create and execute the chain
    chain = section_prompt | llm | StrOutputParser()
    
    try:
        # Convert outline to string format
        outline_str = "\n".join(outline)
        
        # Convert research results to string format
        if 'findings' in research_results and isinstance(research_results['findings'], list):
            research_str = "\n".join([f"- {finding.get('content', '')}" for finding in research_results['findings']])
        elif isinstance(research_results, dict):
            research_str = "\n".join([f"- {k}: {v}" for k, v in research_results.items() if k != 'findings'])
        else:
            research_str = str(research_results)
        
        # Generate section content
        result = chain.invoke({
            "outline": outline_str,
            "keyword": keyword,
            "research_findings": research_str[:3000],  # Limit content length
            "content_type": content_type,
            "instructions": base_instructions + specific_instructions
        })
        
        return result
        
    except Exception as e:
        print(f"Error generating sections: {str(e)}")
        # Return a basic content as fallback
        return f"# Complete Guide to {keyword}\n\n" + "\n\n".join([f"## {section}\n\nContent for {section}..." for section in outline])


def humanize_content(content: Union[str, Dict, List], brand_voice: str, target_audience: str) -> str:
    """
    Transform research results into human-friendly content.
    
    Args:
        content: Research content as string, dictionary, or list
        brand_voice: Description of the brand voice to use
        target_audience: Description of the target audience
        
    Returns:
        Humanized content as a string
    """
    # Convert content to string if it's not already
    if isinstance(content, (dict, list)):
        try:
            import json
            content_str = json.dumps(content, indent=2)
        except:
            content_str = str(content)
    else:
        content_str = str(content)
    
    # Initialize the LLM
    llm = ChatOpenAI(model="gpt-4")
    
    # Create the prompt for humanization
    humanize_prompt = PromptTemplate.from_template("""
    You are an expert content writer tasked with transforming technical research into engaging, human-friendly content.
    
    BRAND VOICE GUIDELINES:
    {brand_voice}
    
    TARGET AUDIENCE:
    {target_audience}
    
    RESEARCH CONTENT TO TRANSFORM:
    {content}
    
    Please rewrite this research content into an engaging blog post that follows the brand voice guidelines 
    and appeals to the target audience. The content should:
    
    1. Have a compelling introduction that hooks the reader
    2. Maintain accuracy while being more conversational and accessible
    3. Include subheadings for better readability
    4. Add storytelling elements where appropriate
    5. End with a conclusion that includes a call to action
    6. Be well-structured with a logical flow
    7. Maintain SEO value by including important keywords naturally
    
    Your response should be the complete, humanized blog post content only.
    """)
    
    # Create and execute the chain
    chain = humanize_prompt | llm
    
    try:
        # Generate humanized content
        result = chain.invoke({
            "content": content_str[:4000],  # Limit content length to avoid token limits
            "brand_voice": brand_voice,
            "target_audience": target_audience
        })
        
        # Extract content from the response
        humanized_content = result.content if hasattr(result, 'content') else str(result)
        
        return humanized_content
        
    except Exception as e:
        print(f"Error humanizing content: {str(e)}")
        return f"Error humanizing content: {str(e)}\n\nOriginal content: {content_str[:500]}..."
