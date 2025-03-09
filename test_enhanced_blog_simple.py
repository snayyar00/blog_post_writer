"""
Simple test for the enhanced blog content generation.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set OpenAI API key
if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"

async def test_enhanced_generate_sections():
    """Test the enhanced generate_sections function directly."""
    
    from src.agents.content_functions import generate_sections
    
    # Create a simple outline
    outline = [
        "# WCAG Compliance Made Simple",
        "## In a Nutshell",
        "## What is WCAG Compliance?",
        "## Why WCAG Compliance Matters",
        "## 5 Steps to WCAG Compliance",
        "## Conclusion"
    ]
    
    # Generate content
    print("Generating enhanced content...")
    content = await generate_sections(
        outline=outline,
        research_results={"findings": [{"content": "WCAG compliance is important for accessibility"}]},
        keyword="WCAG Compliance",
        industry="healthcare",
        add_case_studies=True,
        add_expert_quotes=True,
        add_real_data=True,
        enhanced_formatting=True
    )
    
    # Save the content
    output_dir = Path("generated_posts/enhanced_test")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "simple_test_wcag_compliance.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"Content saved to {output_file}")

if __name__ == "__main__":
    asyncio.run(test_enhanced_generate_sections())