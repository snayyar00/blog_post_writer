"""
Pydantic models for blog analysis structured outputs.

These models define the structure for blog post analysis results, including
scores, insights, and validation rules. They ensure consistent data formats
and provide proper type checking.

Example:
    ```python
    # Create an analysis section
    section = AnalysisSection(
        score=8.5,
        strengths=["Clear writing", "Good examples"],
        weaknesses=["Could use more data"],
        suggestions=["Add statistics", "Include case studies"]
    )

    # Create a complete blog analysis
    analysis = BlogAnalysis(
        overall_score=8.0,
        structure=section,
        accessibility=section,
        empathy=section
    )
    ```
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from typing_extensions import Literal

class AnalysisSection(BaseModel):
    """Analysis section with score and insights.
    
    Attributes:
        score (float): Score from 0-10 for this section
        strengths (List[str]): List of identified strengths
        weaknesses (List[str]): List of areas needing improvement
        suggestions (List[str]): List of actionable suggestions
        metadata (Optional[Dict[str, Any]]): Additional analysis metadata
    """
    score: float = Field(
        ge=0, le=10,
        description="Score from 0-10",
        examples=[7.5, 8.0, 9.2]
    )
    strengths: List[str] = Field(
        default_factory=list,
        description="List of strengths",
        min_items=1,
        max_items=5
    )
    weaknesses: List[str] = Field(
        default_factory=list,
        description="List of areas for improvement",
        min_items=1,
        max_items=5
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="List of actionable suggestions",
        min_items=1,
        max_items=5
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional analysis metadata"
    )

    @field_validator("score")
    def validate_score(cls, v: float) -> float:
        """Ensure score is between 0 and 10."""
        return round(max(0, min(10, v)), 1)

class BlogAnalysis(BaseModel):
    """Complete blog post analysis.
    
    Attributes:
        overall_score (float): Overall analysis score from 0-10
        structure (AnalysisSection): Analysis of content structure
        accessibility (AnalysisSection): Analysis of accessibility features
        empathy (AnalysisSection): Analysis of empathetic writing
        metadata (Optional[Dict[str, Any]]): Additional analysis metadata
    """
    overall_score: float = Field(
        ge=0, le=10,
        description="Overall analysis score",
        examples=[8.0, 9.5]
    )
    structure: AnalysisSection = Field(
        description="Structure analysis",
        examples=[{
            "score": 8.5,
            "strengths": ["Clear organization"],
            "weaknesses": ["Long paragraphs"],
            "suggestions": ["Break up text"]
        }]
    )
    accessibility: AnalysisSection = Field(
        description="Accessibility analysis"
    )
    empathy: AnalysisSection = Field(
        description="Empathy analysis"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional analysis metadata"
    )

    @field_validator("overall_score")
    def validate_overall_score(cls, v: float) -> float:
        """Ensure overall score is between 0 and 10."""
        return round(max(0, min(10, v)), 1)

class AnalysisRequest(BaseModel):
    """Request model for blog analysis.
    
    Attributes:
        content (str): Blog post content to analyze
        analysis_type (str): Type of analysis to perform
        evaluation_points (List[str]): Specific points to evaluate
        metadata (Optional[Dict[str, Any]]): Additional request metadata
    """
    content: str = Field(
        min_length=1,
        description="Blog post content to analyze",
        examples=["This is a blog post about..."]
    )
    analysis_type: Literal["structure", "accessibility", "empathy"] = Field(
        description="Type of analysis to perform",
        examples=["structure", "accessibility", "empathy"]
    )
    evaluation_points: List[str] = Field(
        default_factory=list,
        description="Specific points to evaluate",
        min_items=1,
        max_items=10,
        examples=[["readability", "organization", "flow"]]
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional request metadata"
    )

    @field_validator("content")
    def validate_content_not_empty(cls, v: str) -> str:
        """Ensure content is not just whitespace."""
        if not v.strip():
            raise ValueError("Content cannot be empty or just whitespace")
        return v.strip()

    @field_validator("evaluation_points")
    def validate_evaluation_points(cls, v: List[str]) -> List[str]:
        """Ensure evaluation points are not empty strings."""
        return [point.strip() for point in v if point.strip()]
