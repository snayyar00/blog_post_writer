"""
FastAPI routes for blog analysis with keyword research functionality.
Uses functional patterns and Pydantic models for validation.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path

from src.utils.blog_analysis import analyze_blog_post
from src.utils.keyword_research_manager import get_keyword_suggestions, KeywordResearch

router = APIRouter(prefix="/api/blog", tags=["blog"])

class BlogAnalysisRequest(BaseModel):
    """Request model for blog analysis."""
    content: str = Field(..., description="Blog post content to analyze")
    seed_keywords: Optional[List[str]] = Field(
        default=None,
        description="Optional seed keywords for research"
    )

class BlogAnalysisResponse(BaseModel):
    """Response model for blog analysis."""
    analysis_path: str = Field(..., description="Path to analysis results")
    report_path: str = Field(..., description="Path to markdown report")
    keyword_research: Optional[dict] = Field(
        default=None,
        description="Keyword research results if seed keywords provided"
    )

@router.post("/analyze", response_model=BlogAnalysisResponse)
async def analyze_blog(request: BlogAnalysisRequest) -> BlogAnalysisResponse:
    """
    Analyze blog post with optional keyword research.
    
    - Validates input content
    - Performs keyword research if seed keywords provided
    - Analyzes content structure, accessibility, and empathy
    - Generates detailed report with suggestions
    """
    try:
        # Validate request
        if not request.content.strip():
            raise HTTPException(
                status_code=400,
                detail="Blog content cannot be empty"
            )
            
        # Set up output directory
        output_dir = Path("analysis")
        output_dir.mkdir(exist_ok=True)
        
        # Analyze blog with keyword research
        results = analyze_blog_post(
            content=request.content,
            output_dir=str(output_dir),
            seed_keywords=request.seed_keywords
        )
        
        return BlogAnalysisResponse(
            analysis_path=results["analysis_path"],
            report_path=results["report_path"],
            keyword_research=results.get("keyword_research")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing blog post: {str(e)}"
        )

@router.get("/keywords/history", response_model=List[KeywordResearch])
async def get_keyword_history() -> List[KeywordResearch]:
    """Get history of keyword research for continuous learning."""
    try:
        research_dir = Path("analysis/keyword_research")
        if not research_dir.exists():
            return []
            
        # Load all research files
        research_files = sorted(
            research_dir.glob("research_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        # Read research data
        history = []
        for file in research_files:
            try:
                with open(file) as f:
                    history.append(KeywordResearch.model_validate_json(f.read()))
            except Exception as e:
                print(f"Error reading research file {file}: {e}")
                continue
                
        return history
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching keyword history: {str(e)}"
        )

@router.get("/keywords/trends")
async def get_keyword_trends():
    """Get analysis of keyword trends and patterns."""
    try:
        research_dir = Path("analysis/keyword_research")
        if not research_dir.exists():
            return {
                "popular_topics": [],
                "underexplored_areas": [],
                "successful_keywords": []
            }
            
        # Get keyword suggestions to analyze trends
        trends = get_keyword_suggestions(
            seed_keywords=[],  # Empty list to just get trends
            research_dir=research_dir
        ).get("trends", {})
        
        return trends
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing keyword trends: {str(e)}"
        )
