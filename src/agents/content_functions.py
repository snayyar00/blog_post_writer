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
    You are an elite SEO content strategist who specializes in creating outlines with headings that EXACTLY match what real humans type into search engines.
    
    MAIN KEYWORD: {keyword}
    
    RESEARCH FINDINGS:
    {research_findings}
    
    COMPETITOR INSIGHTS:
    {competitor_insights}
    
    CONTENT TYPE: {content_type}
    
    Create a blog post outline with headings that PRECISELY MATCH actual search queries. Your outline must include:
    
    1. A title that reads like a high-CTR Google search result (max 60 chars)
       - Must include the exact main keyword
       - Should promise clear value (guide, steps, benefits, etc.)
    
    2. "In a Nutshell" section (replaces TLDR)
    
    3. 4-6 main sections with headings that:
       - Are EXACTLY what people would type into Google (3-5 words max)
       - Include at least 2 question-based headings ("How to...", "Why Does...", "What Is...")
       - Use simple, everyday language (5th-7th grade reading level)
       - Contain high-volume search terms and phrases
    
    4. A "Quick Facts" section with surprising information
    
    5. A brief conclusion (max 4 words)
    
    CRITICAL HEADING GUIDELINES:
    - NEVER use academic or formal language
    - ALWAYS write as if speaking to a friend
    - Use numbers whenever possible (e.g., "5 Ways to..." not "Ways to...")
    - Include emotional triggers (best, easy, fast, free, proven, etc.)
    - Match search intent perfectly (informational, commercial, etc.)
    - Use "you" and "your" to make it personal
    
    STUDY THESE EXAMPLES OF PERFECT SEARCH-MATCHING HEADINGS:
    - "What Is Web Accessibility" (not "Understanding Web Accessibility Concepts")
    - "How to Fix Alt Text" (not "Methods for Improving Alternative Text")
    - "5 WCAG Compliance Tips" (not "Strategies for WCAG Compliance")
    - "Best Screen Readers 2025" (not "Top Screen Reading Technologies")
    - "Why ADA Matters for Websites" (not "The Importance of ADA for Digital Properties")
    
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
    1. Write in a conversational, human-like style that feels natural to read
    2. Use short paragraphs (3-4 sentences max) for better readability
    3. Include the main keyword and related terms naturally without keyword stuffing
    4. Be engaging and reader-friendly with a conversational tone
    5. Include practical examples and actionable advice
    6. ALWAYS include an "In a Nutshell" section at the beginning (instead of TLDR) that summarizes the key points in 2-3 sentences
    7. ALWAYS include a "Wild Facts" section with 3-5 surprising or interesting facts about the topic
    8. Use bullet points and numbered lists where appropriate
    9. Include questions in the content that readers might ask
    10. End with a clear conclusion that summarizes key points
    """
    
    # Add content-type specific instructions
    if content_type == "journalistic":
        specific_instructions = """
    11. Include research-backed statistics and cite sources properly
    12. Present a balanced view with multiple perspectives
    13. Use a more authoritative but still conversational tone
    14. Include expert quotes or insights where relevant
    """
    elif content_type == "technical":
        specific_instructions = """
    11. Explain technical concepts in simple, accessible language
    12. Include practical examples that illustrate technical points
    13. Use a clear, step-by-step approach for technical instructions
    14. Balance technical depth with readability for non-experts
    """
    else:  # standard
        specific_instructions = """
    11. Focus on practical applications and real-world benefits
    12. Use a friendly, approachable tone throughout
    13. Include personal touches like "you" and "we" to connect with readers
    14. Emphasize solutions to common problems
    """
    
    section_prompt = PromptTemplate.from_template("""
    You are an expert content writer tasked with creating engaging, human-friendly blog post content.
    
    BLOG POST OUTLINE:
    {outline}
    
    MAIN KEYWORD: {keyword}
    
    RESEARCH FINDINGS:
    {research_findings}
    
    CONTENT TYPE: {content_type}
    
    Please write detailed content for each section in the outline. The content should:
    
    {instructions}
    
    IMPORTANT WRITING GUIDELINES:
    - Write like a human talking to another human
    - Use contractions (don't, can't, we're) to sound natural
    - Vary sentence length - mix short and medium sentences
    - Use active voice instead of passive voice
    - Include rhetorical questions to engage readers
    - Use analogies and metaphors to explain complex concepts
    - Avoid jargon and overly formal language
    - Write at approximately an 8th-grade reading level
    
    Format your response as a complete blog post with proper headings (use # for the title, ## for main sections, ### for subsections).
    Make sure the "In a Nutshell" section appears immediately after the title and before the introduction.
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
    You are an expert content writer tasked with transforming technical content into engaging, human-friendly blog posts.
    
    BRAND VOICE GUIDELINES:
    {brand_voice}
    
    TARGET AUDIENCE:
    {target_audience}
    
    CONTENT TO TRANSFORM:
    {content}
    
    Please rewrite this content into a highly engaging blog post that sounds like it was written by a real human,
    not AI. The content should:
    
    1. Use a conversational, natural tone that feels like someone talking to a friend
    2. Have short, punchy paragraphs (3-4 sentences max)
    3. Include rhetorical questions that engage the reader
    4. Use contractions (don't, can't, we're) and casual language
    5. Include personal touches like "you" and "we" to connect with readers
    6. Vary sentence length - mix short and medium sentences for rhythm
    7. Use analogies and metaphors to explain complex concepts
    8. Include occasional humor or personality where appropriate
    9. Maintain all the original information but present it in a more engaging way
    10. Keep headings concise and conversational (max 5-7 words)
    11. End with a conclusion that includes a natural call to action
    
    IMPORTANT WRITING GUIDELINES:
    - Write at approximately an 8th-grade reading level
    - Use active voice instead of passive voice
    - Avoid jargon and overly formal language
    - Include transition words between paragraphs for flow
    - Break up text with bullet points where appropriate
    - Maintain all SEO value by keeping important keywords
    - Ensure headings match what real humans would search for
    
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
