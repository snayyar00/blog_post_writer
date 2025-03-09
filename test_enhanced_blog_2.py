"""
Test the enhanced blog post generation using the updated agent orchestrator.
"""

import os
import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Set a dummy API key for testing if not present in environment
if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"

async def test_enhanced_blog_generation():
    try:
        print("Starting enhanced blog post generation test")
        
        # Import the agent orchestrator
        from src.agents.agent_orchestrator import generate_blog_post
        
        # Generate a blog post with healthcare industry-specific content
        print("Generating a blog post about ADA compliance for healthcare")
        blog_post = await generate_blog_post(
            topic="ADA Compliance for Websites",
            industry="healthcare",
            content_type="technical",
            add_case_studies=True,
            add_expert_quotes=True,
            add_real_data=True,
            enhanced_formatting=True,
            use_premium_model=True
        )
        
        # Create output directory if it doesn't exist
        output_dir = Path("generated_posts/enhanced_test")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save the blog post to a file
        output_path = output_dir / "enhanced_ada_compliance_healthcare.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(blog_post.content)
        
        print(f"Blog post saved to {output_path}")
        
        # Save the blog post metadata to a file
        metadata_path = output_dir / "enhanced_ada_compliance_healthcare_metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            # Convert BlogPost object to dictionary, skipping content to avoid duplication
            metadata = {
                "title": blog_post.title,
                "keywords": blog_post.keywords,
                "outline": blog_post.outline,
                "metrics": {
                    "readability_score": blog_post.metrics.readability_score,
                    "seo_score": blog_post.metrics.seo_score,
                    "engagement_score": blog_post.metrics.engagement_score
                }
            }
            json.dump(metadata, f, indent=2)
        
        print(f"Blog post metadata saved to {metadata_path}")
        
    except ImportError as e:
        print(f"Failed to import required modules: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(test_enhanced_blog_generation())