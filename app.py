"""
Streamlit app for blog post generation with visualization of the process.
"""

import os
import json
import streamlit as st
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import time

# Import our modules
from src.agents.keyword_functions import generate_keywords
from src.agents.research_agent import ResearchAgent
from src.agents.content_functions import humanize_content
from src.agents.memoripy_manager import ResearchMemoryManager
from src.utils.web_scraper import load_context_files, scrape_website_to_context

# Load environment variables
load_dotenv()

# We're now using the enhanced load_context_files from web_scraper.py

def process_topic(topic: str, context_data: Dict[str, str], api_key: Optional[str] = None) -> Dict[str, Any]:
    """Process a topic through the agent pipeline with visualization."""
    results = {
        "keywords": [],
        "research": [],
        "context_used": [],
        "webability_context": [],
        "brand_context": {},
        "content": "",
        "errors": []
    }
    
    # Extract and categorize context
    webability_context = []
    brand_voice = "professional yet conversational"  # Default
    target_audience = "business professionals"  # Default
    company_info = "WebAbility.io is a leading web accessibility consultancy"  # Default
    
    # Process context data
    for key, value in context_data.items():
        # Track which context files are used
        results["context_used"].append(key)
        
        # Categorize context
        if key.startswith("web_"):
            webability_context.append(value)
            results["webability_context"].append(key)
        elif "brand" in key.lower() or "voice" in key.lower():
            brand_voice = value
            results["brand_context"]["brand_voice"] = key
        elif "audience" in key.lower() or "target" in key.lower():
            target_audience = value
            results["brand_context"]["target_audience"] = key
        elif "company" in key.lower() or "business" in key.lower():
            company_info = value
            results["brand_context"]["company_info"] = key
    
    # Combine WebAbility.io context
    webability_content = "\n\n---\n\n".join(webability_context)
    
    # Step 1: Generate keywords
    with st.spinner("Generating keywords..."):
        try:
            # Add company info to context for better keyword generation
            keyword_context = context_data.copy()
            keyword_context["company_info"] = company_info
            keyword_context["webability_content"] = webability_content[:5000]  # Limit size
            
            results["keywords"] = generate_keywords(topic, keyword_context)
            st.success(f"Generated {len(results['keywords'])} keywords")
        except Exception as e:
            error_msg = f"Error generating keywords: {str(e)}"
            st.error(error_msg)
            results["errors"].append(error_msg)
            # Use fallback keywords
            results["keywords"] = [topic, f"{topic} best practices", f"{topic} guide", "web accessibility"]
    
    # Step 2: Research the topic
    with st.spinner("Researching topic..."):
        try:
            research_agent = ResearchAgent(api_key=api_key)
            # Include WebAbility.io in the research query
            research_query = f"WebAbility.io {topic}: {', '.join(results['keywords'][:5])}"
            research_results = research_agent.research_topic(research_query)
            results["research"] = research_results
            st.success(f"Research completed with {len(research_results)} findings")
        except Exception as e:
            error_msg = f"Error during research: {str(e)}"
            st.error(error_msg)
            results["errors"].append(error_msg)
            # Use mock research data
            results["research"] = [{
                "content": f"Error researching {topic}. Using placeholder content.",
                "sources": [],
                "confidence": 0
            }]
    
    # Step 3: Store research results in memory
    with st.spinner("Storing research in memory..."):
        try:
            memory_manager = ResearchMemoryManager(api_key)
            research_data = {
                "topic": topic,
                "keywords": results["keywords"],
                "research": results["research"],
                "context_used": results["context_used"],
                "webability_context": results["webability_context"],
                "timestamp": time.time()
            }
            
            # Save research results to a file for reference
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            memory_dir = Path("./memory")
            memory_dir.mkdir(exist_ok=True)
            research_file = memory_dir / f"research_{timestamp}.json"
            with open(research_file, "w") as f:
                json.dump(research_data, f, indent=2)
            
            # Store in memory system
            store_success = memory_manager.store_research_results(research_data, topic)
            if store_success:
                st.success(f"Research stored in memory and saved to {research_file}")
            else:
                st.warning(f"Memory storage failed, but research saved to {research_file}")
                
        except Exception as e:
            error_msg = f"Error storing research: {str(e)}"
            st.error(error_msg)
            results["errors"].append(error_msg)
            
            # Try to save research results to a file even if memory storage failed
            try:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                memory_dir = Path("./memory")
                memory_dir.mkdir(exist_ok=True)
                research_file = memory_dir / f"research_error_{timestamp}.json"
                with open(research_file, "w") as f:
                    json.dump({
                        "topic": topic,
                        "keywords": results["keywords"],
                        "research": results["research"],
                        "error": str(e),
                        "timestamp": time.time()
                    }, f, indent=2)
                st.info(f"Research saved to {research_file} despite memory error")
            except Exception as file_error:
                st.error(f"Could not save research to file: {str(file_error)}")
    
    # Step 4: Humanize the content
    with st.spinner("Generating human-friendly content..."):
        try:
            # Prepare context for humanization
            humanization_context = {
                "brand_voice": brand_voice,
                "target_audience": target_audience,
                "company": "WebAbility.io",
                "company_info": company_info,
                "website": "https://www.webability.io",
                "topic": topic,
                "keywords": ", ".join(results["keywords"][:10])
            }
            
            # Extract research content
            research_content = "\n\n".join([item.get("content", "") for item in results["research"]])
            
            # Add WebAbility.io specific context
            if webability_content:
                research_content += "\n\nWebAbility.io Context:\n" + webability_content[:2000]
            
            # Humanize content
            results["content"] = humanize_content(
                research_content, 
                humanization_context.get("brand_voice", brand_voice),
                humanization_context.get("target_audience", target_audience)
            )
            st.success("Content humanized successfully")
        except Exception as e:
            error_msg = f"Error humanizing content: {str(e)}"
            st.error(error_msg)
            results["errors"].append(error_msg)
            results["content"] = research_content  # Use raw research as fallback
    
    return results

def main():
    st.set_page_config(
        page_title="WebAbility.io Blog Post Generator",
        page_icon="📝",
        layout="wide"
    )
    
    st.title("📝 WebAbility.io Blog Post Generator")
    st.subheader("Generate engaging accessibility-focused blog posts with AI")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # Topic input
        topic = st.text_input("Blog Topic", value="web accessibility best practices")
        
        # API key handling - don't show the actual key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.warning("⚠️ No API key found in environment variables")
            st.info("API key will be loaded from .env file if available")
        else:
            st.success("✅ API key loaded from environment")
        
        # Website scraping section
        st.header("WebAbility.io Content")
        sitemap_url = "https://www.webability.io/sitemap.xml"
        
        # Check if we already have scraped content
        context_data = load_context_files()
        web_context_count = sum(1 for filename in context_data.keys() if filename.startswith("web_"))
        
        if web_context_count > 0:
            st.success(f"✅ {web_context_count} WebAbility.io pages loaded")
        else:
            st.warning("No WebAbility.io content loaded")
        
        # Scrape button
        col1, col2 = st.columns(2)
        with col1:
            max_urls = st.number_input("Max URLs", min_value=1, max_value=20, value=5)
        with col2:
            scrape_button = st.button("Scrape Website")
        
        if scrape_button:
            with st.spinner(f"Scraping {sitemap_url}..."):
                saved_files = scrape_website_to_context(sitemap_url, max_urls=max_urls)
                st.success(f"Scraped {len(saved_files)} pages from WebAbility.io")
                # Reload context data
                context_data = load_context_files()
        
        # Process button
        process_button = st.button("Generate Blog Post", type="primary")
        
        # Show context files
        st.header("Available Context")
        if context_data:
            st.success(f"Loaded {len(context_data)} context files")
            
            # Group context files by type
            web_files = [f for f in context_data.keys() if f.startswith("web_")]
            brand_files = [f for f in context_data.keys() if "brand" in f.lower() or "voice" in f.lower()]
            audience_files = [f for f in context_data.keys() if "audience" in f.lower() or "target" in f.lower()]
            other_files = [f for f in context_data.keys() if f not in web_files + brand_files + audience_files]
            
            # Show files by category
            if web_files:
                with st.expander(f"WebAbility.io Content ({len(web_files)})", expanded=False):
                    for filename in web_files:
                        st.text(f"🌐 {filename}")
            
            if brand_files:
                with st.expander(f"Brand Voice ({len(brand_files)})", expanded=True):
                    for filename in brand_files:
                        st.text(f"🎯 {filename}")
            
            if audience_files:
                with st.expander(f"Target Audience ({len(audience_files)})", expanded=True):
                    for filename in audience_files:
                        st.text(f"👥 {filename}")
            
            if other_files:
                with st.expander(f"Other Context ({len(other_files)})", expanded=False):
                    for filename in other_files:
                        st.text(f"📄 {filename}")
        else:
            st.warning("No context files found")
    
    # Main content area
    if process_button:
        # Create tabs for different stages
        tab1, tab2, tab3, tab4 = st.tabs(["Keywords", "Research", "Context Integration", "Final Content"])
        
        # Process the topic
        results = process_topic(topic, context_data, api_key)
        
        # Tab 1: Keywords
        with tab1:
            st.header("Generated Keywords")
            st.write("These keywords were generated based on your topic and context:")
            
            # Display keywords in columns
            cols = st.columns(3)
            for i, keyword in enumerate(results["keywords"]):
                cols[i % 3].markdown(f"- **{keyword}**")
        
        # Tab 2: Research
        with tab2:
            st.header("Research Findings")
            st.write("Research conducted based on the generated keywords:")
            
            for i, finding in enumerate(results["research"]):
                with st.expander(f"Finding {i+1}", expanded=i==0):
                    st.markdown(finding.get("content", "No content"))
                    
                    if finding.get("sources"):
                        st.subheader("Sources")
                        for source in finding.get("sources", []):
                            st.markdown(f"- {source}")
                    
                    st.progress(finding.get("confidence", 0), text=f"Confidence: {finding.get('confidence', 0):.2f}")
        
        # Tab 3: Context Integration
        with tab3:
            st.header("Context Integration")
            st.write("How context files were used in the generation process:")
            
            # Display context files used
            for context_file in results["context_used"]:
                with st.expander(f"Context: {context_file}"):
                    st.code(context_data.get(context_file, "")[:500] + "...", language="markdown")
                    
                    # Show what was extracted from this context
                    if "brand" in context_file.lower() or "voice" in context_file.lower():
                        st.info("Used for brand voice guidance")
                    elif "audience" in context_file.lower() or "target" in context_file.lower():
                        st.info("Used for target audience information")
                    elif "competitor" in context_file.lower() or "business" in context_file.lower():
                        st.info("Used for competitive analysis and market positioning")
                    else:
                        st.info("Used for general context and domain knowledge")
        
        # Tab 4: Final Content
        with tab4:
            st.header("Final Blog Post Content")
            st.write("The final humanized content ready for publishing:")
            
            st.markdown(results["content"])
            
            # Download button for the content
            st.download_button(
                label="Download Blog Post",
                data=results["content"],
                file_name=f"blog_post_{topic.replace(' ', '_')}.md",
                mime="text/markdown"
            )

if __name__ == "__main__":
    main()
