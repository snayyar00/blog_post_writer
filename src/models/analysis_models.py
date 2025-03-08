"""
Pydantic models for blog analysis structured outputs.
"""
from typing import List
from pydantic import BaseModel, Field, field_validator
from typing_extensions import Literal

class AnalysisSection(BaseModel):
    """Analysis section with score and insights."""
    score: float = Field(ge=0, le=10, description="Score from 0-10")
    strengths: List[str] = Field(default_factory=list, description="List of strengths")
    weaknesses: List[str] = Field(default_factory=list, description="List of areas for improvement")
    suggestions: List[str] = Field(default_factory=list, description="List of actionable suggestions")

    @field_validator("score")
    def validate_score(cls, v: float) -> float:
        """Ensure score is between 0 and 10."""
        return round(max(0, min(10, v)), 1)

class BlogAnalysis(BaseModel):
    """Complete blog post analysis."""
    overall_score: float = Field(ge=0, le=10, description="Overall analysis score")
    structure: AnalysisSection = Field(description="Structure analysis")
    accessibility: AnalysisSection = Field(description="Accessibility analysis")
    empathy: AnalysisSection = Field(description="Empathy analysis")

    @field_validator("overall_score")
    def validate_overall_score(cls, v: float) -> float:
        """Ensure overall score is between 0 and 10."""
        return round(max(0, min(10, v)), 1)

class AnalysisRequest(BaseModel):
    """Request model for blog analysis."""
    content: str = Field(min_length=1, description="Blog post content to analyze")
    analysis_type: Literal["structure", "accessibility", "empathy"] = Field(
        description="Type of analysis to perform"
    )
    evaluation_points: List[str] = Field(
        default_factory=list,
        description="Specific points to evaluate"
    )
