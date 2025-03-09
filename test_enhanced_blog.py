"""Test script for enhanced blog post generation."""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any, List

# Import necessary components
from src.agents.content_functions import generate_outline, generate_sections, humanize_content
from src.utils.logging_manager import log_info, log_debug, log_error

# Create enhanced content retrieval functions
async def retrieve_case_studies_and_quotes(keyword: str) -> Dict[str, Any]:
    """
    Retrieve relevant case studies and expert quotes from memory.
    
    In a real implementation, this would query the memory database.
    For this test, we'll use simulated data.
    """
    # Simulated case studies for web accessibility
    if "accessibility" in keyword.lower() or "wcag" in keyword.lower():
        case_studies = [
            {
                "company": "Maryville University",
                "industry": "Education",
                "challenge": "Poor accessibility compliance affecting student engagement",
                "solution": "Implemented WCAG 2.0 guidelines across all university websites",
                "results": "15% traffic increase and 30% admissions increase after site became fully accessible"
            },
            {
                "company": "Bank of America",
                "industry": "Finance",
                "challenge": "Multiple accessibility issues leading to legal challenges",
                "solution": "Redesigned online banking platform with accessibility-first approach",
                "results": "Reduced customer service calls by 25% and increased mobile banking usage by 18%"
            }
        ]
        
        expert_quotes = [
            {
                "name": "Sheri Byrne-Haber",
                "title": "Accessibility Architect",
                "quote": "If you don't plan for accessibility from the beginning, you're excluding 15% of potential users"
            },
            {
                "name": "Tim Berners-Lee",
                "title": "Inventor of the World Wide Web",
                "quote": "The power of the Web is in its universality. Access by everyone, regardless of disability, is an essential aspect"
            }
        ]
        
        return {
            "case_studies": case_studies,
            "expert_quotes": expert_quotes
        }
    
    # Default empty response for other keywords
    return {
        "case_studies": [],
        "expert_quotes": []
    }

async def retrieve_industry_specific_content(keyword: str, industry: str) -> Dict[str, Any]:
    """
    Retrieve industry-specific content for a keyword.
    
    In a real implementation, this would query the memory database.
    For this test, we'll use simulated data.
    """
    # Simulated industry-specific content
    if industry == "healthcare" and ("accessibility" in keyword.lower() or "wcag" in keyword.lower()):
        return {
            "challenges": [
                "Patient portals must be accessible to all users, including those with disabilities",
                "Medical terminology can be complex and requires screen reader compatibility",
                "Telehealth interfaces need to work with assistive technologies"
            ],
            "regulations": [
                "Section 1557 of the Affordable Care Act requires healthcare websites to be accessible",
                "HIPAA compliance must be maintained alongside accessibility features"
            ],
            "implementation_tips": [
                "Ensure all medical form fields have proper labels for screen readers",
                "Provide alternatives to complex medical charts and diagrams",
                "Test telehealth interfaces with various assistive technologies"
            ]
        }
    
    # Default empty response for other combinations
    return {
        "challenges": [],
        "regulations": [],
        "implementation_tips": []
    }

async def retrieve_real_data_and_statistics(keyword: str) -> Dict[str, Any]:
    """
    Retrieve real data and statistics related to the keyword.
    
    In a real implementation, this would query an external API or database.
    For this test, we'll use simulated data.
    """
    # Simulated statistics for web accessibility
    if "accessibility" in keyword.lower() or "wcag" in keyword.lower():
        return {
            "statistics": [
                {
                    "value": "98.1%",
                    "description": "of top 1 million website homepages have at least one WCAG 2.0 failure (WebAIM 2020)"
                },
                {
                    "value": "61%",
                    "description": "of accessibility issues are related to images with missing or improper alt text"
                },
                {
                    "value": "15%",
                    "description": "of the world's population (over 1 billion people) have some form of disability (WHO)"
                },
                {
                    "value": "$25,000-$55,000",
                    "description": "typical settlement amount for a web accessibility lawsuit"
                }
            ]
        }
    
    # Default empty response for other keywords
    return {
        "statistics": []
    }

def format_case_studies_as_string(case_studies: List[Dict[str, Any]]) -> str:
    """Format case studies as a string for the content generation prompt."""
    if not case_studies:
        return "No case studies available"
    
    formatted = []
    for cs in case_studies:
        formatted.append(f"CASE STUDY: {cs.get('company', 'Unknown Company')}")
        formatted.append(f"Industry: {cs.get('industry', 'Various')}")
        formatted.append(f"Challenge: {cs.get('challenge', '')}")
        formatted.append(f"Solution: {cs.get('solution', '')}")
        formatted.append(f"Results: {cs.get('results', '')}")
        formatted.append("")
    
    return "\n".join(formatted)

def format_expert_quotes_as_string(quotes: List[Dict[str, Any]]) -> str:
    """Format expert quotes as a string for the content generation prompt."""
    if not quotes:
        return "No expert quotes available"
    
    formatted = []
    for q in quotes:
        formatted.append(f"EXPERT QUOTE: \"{q.get('quote', '')}\" - {q.get('name', 'Unknown')}, {q.get('title', '')}")
    
    return "\n".join(formatted)

def format_industry_content_as_string(content: Dict[str, Any], industry: str) -> str:
    """Format industry-specific content as a string."""
    if not content or all(len(v) == 0 for v in content.values()):
        return f"No specific {industry} industry content available"
    
    formatted = [f"INDUSTRY SPOTLIGHT: {industry.upper()}"]
    
    if "challenges" in content and content["challenges"]:
        formatted.append(f"\nIndustry Challenges:")
        for challenge in content["challenges"]:
            formatted.append(f"- {challenge}")
    
    if "regulations" in content and content["regulations"]:
        formatted.append(f"\nIndustry Regulations:")
        for reg in content["regulations"]:
            formatted.append(f"- {reg}")
    
    if "implementation_tips" in content and content["implementation_tips"]:
        formatted.append(f"\nImplementation Tips for {industry}:")
        for tip in content["implementation_tips"]:
            formatted.append(f"- {tip}")
    
    return "\n".join(formatted)

def format_statistics_as_string(statistics: List[Dict[str, Any]]) -> str:
    """Format statistics as a string for the content generation prompt."""
    if not statistics:
        return "No statistics available"
    
    formatted = ["REAL DATA AND STATISTICS:"]
    for stat in statistics:
        formatted.append(f"- {stat.get('value', '')}: {stat.get('description', '')}")
    
    return "\n".join(formatted)

# Enhanced version of generate_sections with additional parameters
async def enhanced_generate_sections(
    outline: List[str], 
    research_results: Dict[str, Any], 
    keyword: str, 
    industry: str = None,
    content_type: str = "standard", 
    model: str = "gpt-4",
    add_case_studies: bool = True, 
    add_expert_quotes: bool = True,
    add_real_data: bool = True,
    enhanced_formatting: bool = True
) -> str:
    """
    Generate enhanced blog post content with additional features.
    """
    try:
        log_debug(f"Starting enhanced section generation for {len(outline)} sections", "CONTENT")
        
        # Retrieve additional content
        case_studies_quotes = await retrieve_case_studies_and_quotes(keyword) if add_case_studies or add_expert_quotes else {}
        case_studies_str = format_case_studies_as_string(case_studies_quotes.get("case_studies", [])) if add_case_studies else ""
        expert_quotes_str = format_expert_quotes_as_string(case_studies_quotes.get("expert_quotes", [])) if add_expert_quotes else ""
        
        # Retrieve industry-specific content if requested
        industry_content_str = ""
        if industry:
            industry_data = await retrieve_industry_specific_content(keyword, industry)
            industry_content_str = format_industry_content_as_string(industry_data, industry)
        
        # Retrieve real data and statistics if requested
        statistics_str = ""
        if add_real_data:
            statistics_data = await retrieve_real_data_and_statistics(keyword)
            statistics_str = format_statistics_as_string(statistics_data.get("statistics", []))
        
        # Prepare enhanced formatting instructions
        enhanced_formatting_instructions = ""
        if enhanced_formatting:
            enhanced_formatting_instructions = """
FORMAT THE CONTENT WITH:
1. Clear heading hierarchy using Markdown (# for title, ## for main sections, ### for subsections)
2. Use **bold text** for key points and statistics
3. Create distinct callout sections using > blockquotes for important information
4. Use --- horizontal rules to separate major sections
5. Create tables for comparing data when applicable
6. Use properly formatted bullet and numbered lists
7. Include "ℹ️ QUICK TIP" callouts for actionable advice
8. Format statistics as "📊 STAT: [statistic]"
9. Format expert quotes as "> [quote] - [Expert Name], [Title]"
10. Include "📝 IMPLEMENTATION CHECKLIST" sections
11. Create "🔍 INDUSTRY SPOTLIGHT" sections for industry-specific content
"""
        
        # Create an enhanced research object that includes all our additional content
        enhanced_research = {
            "original_research": research_results,
            "case_studies": case_studies_str,
            "expert_quotes": expert_quotes_str,
            "industry_content": industry_content_str,
            "statistics": statistics_str
        }
        
        # Convert enhanced research to string format
        enhanced_research_str = json.dumps(enhanced_research, indent=2)
        
        # Create the outline string
        outline_str = "\n".join(outline)
        
        # Import the necessary components
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import PromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        
        # Initialize the LLM
        llm = ChatOpenAI(model=model)
        
        # Create our enhanced prompt template
        enhanced_prompt = PromptTemplate.from_template("""
You are an expert content writer tasked with creating engaging, human-friendly blog post content.

BLOG POST OUTLINE:
{outline}

MAIN KEYWORD: {keyword}

RESEARCH FINDINGS:
{research_findings}

CASE STUDIES:
{case_studies}

EXPERT QUOTES:
{expert_quotes}

REAL DATA AND STATISTICS:
{statistics}

INDUSTRY-SPECIFIC CONTENT:
{industry_content}

CONTENT TYPE: {content_type}

Please write detailed content for each section in the outline. The content should:

1. Write in a conversational, human-like style that feels natural to read
2. Use short paragraphs (3-4 sentences max) for better readability
3. Include the main keyword and related terms naturally without keyword stuffing
4. Be engaging and reader-friendly with a conversational tone
5. Include practical examples and actionable advice
6. ALWAYS include an "In a Nutshell" section at the beginning (instead of TLDR) that summarizes the key points in 2-3 sentences
7. Use bullet points and numbered lists where appropriate
8. Include questions in the content that readers might ask
9. End with a clear conclusion that summarizes key points
10. INCORPORATE ALL PROVIDED CASE STUDIES, QUOTES, STATISTICS, AND INDUSTRY CONTENT naturally throughout the post
11. Include technical implementation guidance where appropriate, with code examples if relevant

{formatting_instructions}

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
        chain = enhanced_prompt | llm | StrOutputParser()
        
        # Extract research string
        if "original_research" in enhanced_research and enhanced_research["original_research"]:
            if 'findings' in enhanced_research["original_research"] and isinstance(enhanced_research["original_research"]['findings'], list):
                research_str = "\n".join([f"- {finding.get('content', '')}" for finding in enhanced_research["original_research"]['findings']])
            else:
                research_str = str(enhanced_research["original_research"])
        else:
            research_str = "No research data available"
            
        # Generate the enhanced content
        result = await chain.ainvoke({
            "outline": outline_str,
            "keyword": keyword,
            "research_findings": research_str[:2000],
            "case_studies": enhanced_research["case_studies"][:1500],
            "expert_quotes": enhanced_research["expert_quotes"][:1000],
            "statistics": enhanced_research["statistics"][:1000],
            "industry_content": enhanced_research["industry_content"][:1500],
            "content_type": content_type,
            "formatting_instructions": enhanced_formatting_instructions
        })
        
        log_debug("Successfully generated enhanced content", "CONTENT")
        return result
    
    except Exception as e:
        log_error(f"Error generating enhanced sections: {str(e)}", "CONTENT")
        # Return a basic content as fallback
        return f"# Complete Guide to {keyword}\n\nError generating enhanced content: {str(e)}\n\n" + "\n\n".join([f"## {section}\n\nContent for {section}..." for section in outline])

async def generate_enhanced_blog_post(keyword: str, industry: str = None):
    """
    Generate a blog post with enhanced features like case studies, expert quotes, 
    industry-specific content, and better formatting.
    """
    log_info(f"Generating enhanced blog post for keyword: {keyword}")
    
    # Step 1: Generate a basic outline
    research_results = {"findings": [{"content": "Web accessibility is a critical consideration for modern websites"}]}
    outline = await generate_outline(keyword, research_results)
    log_debug(f"Generated outline: {outline}")
    
    # Step 2: Generate the enhanced content
    content = await enhanced_generate_sections(
        outline=outline,
        research_results=research_results,
        keyword=keyword,
        industry=industry,
        content_type="technical" if industry else "journalistic"
    )
    
    # Save the generated content for inspection
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = "generated_posts/enhanced_test"
    os.makedirs(output_dir, exist_ok=True)
    
    output_filename = f"{output_dir}/enhanced_{keyword.replace(' ', '_')}_{timestamp}.md"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(content)
    
    log_info(f"Enhanced blog post generated and saved to {output_filename}")
    return content

async def main():
    """Run the test to generate an enhanced blog post."""
    # Test with a keyword and industry
    await generate_enhanced_blog_post("WCAG Compliance", "healthcare")
    print("Test completed. Check the generated_posts/enhanced_test directory for results.")

if __name__ == "__main__":
    asyncio.run(main())