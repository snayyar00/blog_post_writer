"""
OpenAI-powered blog post analyzer focused on accessibility and content quality.
"""
from typing import Dict, List, Any
from dataclasses import dataclass
import os
from pathlib import Path
import json
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

@dataclass
class AnalysisResult:
    """Container for analysis results."""
    category: str
    score: float
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[str]

def analyze_structure(content: str) -> AnalysisResult:
    """Analyze content structure using OpenAI."""
    prompt = f"""Analyze the structure of this blog post about web accessibility:

{content}

Evaluate:
1. Paragraph organization and length
2. Sentence structure and clarity
3. Headers and subheaders
4. Logical flow and transitions
5. Content hierarchy

Format:
- Score (0-10)
- Key strengths (bullet points)
- Areas for improvement (bullet points)
- Specific suggestions (bullet points)

Focus on accessibility best practices for content structure."""

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1000
    )
    
    result = response.choices[0].message.content
    
    # Parse the response with better error handling
    try:
        lines = result.split("\n")
        # Find score - default to 5 if not found
        score_lines = [l for l in lines if "Score" in l]
        score = 5.0 if not score_lines else float(score_lines[0].split(":")[-1].strip())
        
        # Extract insights with flexible matching
        strengths = []
        weaknesses = []
        suggestions = []
        
        for line in lines:
            line = line.strip("- *")
            if not line:
                continue
                
            # Categorize based on context
            if any(word in line.lower() for word in ["strength", "good", "effective", "well"]):
                strengths.append(line)
            elif any(word in line.lower() for word in ["improve", "weak", "missing", "lack"]):
                weaknesses.append(line)
            elif any(word in line.lower() for word in ["suggest", "recommend", "consider", "try"]):
                suggestions.append(line)
                
        # Ensure we have at least one item in each category
        if not strengths:
            strengths = ["Content provides basic information about accessibility"]
        if not weaknesses:
            weaknesses = ["Could be enhanced with more specific examples"]
        if not suggestions:
            suggestions = ["Consider adding more concrete implementation details"]
    
    except Exception as e:
        print(f"Error parsing response: {e}")
        return AnalysisResult(
            category="Structure",
            score=0,
            strengths=[],
            weaknesses=[],
            suggestions=[]
        )
    return AnalysisResult(
        category="Structure",
        score=score,
        strengths=strengths,
        weaknesses=weaknesses,
        suggestions=suggestions
    )

def analyze_accessibility(content: str) -> AnalysisResult:
    """Analyze accessibility coverage using OpenAI."""
    prompt = f"""Analyze the accessibility coverage in this blog post:

{content}

Evaluate:
1. Coverage of key accessibility standards (WCAG, ADA, Section 508)
2. Technical accuracy of accessibility terms
3. Explanation of accessibility features
4. Real-world applications and examples
5. Target audience understanding

Format:
- Score (0-10)
- Key strengths (bullet points)
- Missing coverage areas (bullet points)
- Improvement suggestions (bullet points)

Focus on comprehensive accessibility coverage."""

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1000
    )
    
    result = response.choices[0].message.content
    
    # Parse the response
    lines = result.split("\n")
    score = float([l for l in lines if "Score" in l][0].split(":")[-1].strip())
    strengths = [l.strip("- ") for l in lines if l.startswith("- ") and "strength" in l.lower()]
    weaknesses = [l.strip("- ") for l in lines if l.startswith("- ") and ("missing" in l.lower() or "lack" in l.lower())]
    suggestions = [l.strip("- ") for l in lines if l.startswith("- ") and "suggest" in l.lower()]
    
    return AnalysisResult(
        category="Accessibility",
        score=score,
        strengths=strengths,
        weaknesses=weaknesses,
        suggestions=suggestions
    )

def analyze_empathy(content: str) -> AnalysisResult:
    """Analyze empathetic language using OpenAI."""
    prompt = f"""Analyze the empathetic language in this blog post:

{content}

Evaluate:
1. Understanding of user challenges
2. Inclusive language
3. Emotional connection
4. User-centric perspective
5. Supportive tone

Format:
- Score (0-10)
- Effective empathy examples (bullet points)
- Areas lacking empathy (bullet points)
- Suggestions for improvement (bullet points)

Focus on creating emotional connection with users."""

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1000
    )
    
    result = response.choices[0].message.content
    
    # Parse the response
    lines = result.split("\n")
    score = float([l for l in lines if "Score" in l][0].split(":")[-1].strip())
    strengths = [l.strip("- ") for l in lines if l.startswith("- ") and "example" in l.lower()]
    weaknesses = [l.strip("- ") for l in lines if l.startswith("- ") and "lack" in l.lower()]
    suggestions = [l.strip("- ") for l in lines if l.startswith("- ") and "suggest" in l.lower()]
    
    return AnalysisResult(
        category="Empathy",
        score=score,
        strengths=strengths,
        weaknesses=weaknesses,
        suggestions=suggestions
    )

def analyze_content(content: str) -> Dict[str, Any]:
    """
    Perform comprehensive content analysis using OpenAI.
    
    Args:
        content: Blog post content
        
    Returns:
        Dictionary containing analysis results
    """
    if not content:
        raise ValueError("Content cannot be empty")
    
    # Perform all analyses
    structure = analyze_structure(content)
    accessibility = analyze_accessibility(content)
    empathy = analyze_empathy(content)
    
    # Calculate overall score
    overall_score = (structure.score + accessibility.score + empathy.score) / 3
    
    return {
        "overall_score": overall_score,
        "structure": {
            "score": structure.score,
            "strengths": structure.strengths,
            "weaknesses": structure.weaknesses,
            "suggestions": structure.suggestions
        },
        "accessibility": {
            "score": accessibility.score,
            "strengths": accessibility.strengths,
            "weaknesses": accessibility.weaknesses,
            "suggestions": accessibility.suggestions
        },
        "empathy": {
            "score": empathy.score,
            "strengths": empathy.strengths,
            "weaknesses": empathy.weaknesses,
            "suggestions": empathy.suggestions
        }
    }

def generate_report(analysis: Dict[str, Any]) -> str:
    """Generate a markdown report from analysis results."""
    report = []
    
    # Overall score
    report.append("# Blog Post Analysis Report\n")
    report.append(f"## Overall Score: {analysis['overall_score']:.1f}/10\n")
    
    # Structure
    report.append("## Structure Analysis")
    struct = analysis["structure"]
    report.append(f"Score: {struct['score']:.1f}/10\n")
    report.append("### Strengths")
    for strength in struct["strengths"]:
        report.append(f"- {strength}")
    report.append("\n### Areas for Improvement")
    for weakness in struct["weaknesses"]:
        report.append(f"- {weakness}")
    report.append("\n### Suggestions")
    for suggestion in struct["suggestions"]:
        report.append(f"- {suggestion}")
    report.append("")
    
    # Accessibility
    report.append("## Accessibility Coverage")
    access = analysis["accessibility"]
    report.append(f"Score: {access['score']:.1f}/10\n")
    report.append("### Strengths")
    for strength in access["strengths"]:
        report.append(f"- {strength}")
    report.append("\n### Missing Coverage")
    for weakness in access["weaknesses"]:
        report.append(f"- {weakness}")
    report.append("\n### Suggestions")
    for suggestion in access["suggestions"]:
        report.append(f"- {suggestion}")
    report.append("")
    
    # Empathy
    report.append("## Empathy Analysis")
    empathy = analysis["empathy"]
    report.append(f"Score: {empathy['score']:.1f}/10\n")
    report.append("### Effective Examples")
    for strength in empathy["strengths"]:
        report.append(f"- {strength}")
    report.append("\n### Areas Lacking Empathy")
    for weakness in empathy["weaknesses"]:
        report.append(f"- {weakness}")
    report.append("\n### Suggestions")
    for suggestion in empathy["suggestions"]:
        report.append(f"- {suggestion}")
    
    return "\n".join(report)

def analyze_and_save(content: str, output_dir: str = "analysis") -> str:
    """
    Analyze content and save results.
    
    Args:
        content: Blog post content
        output_dir: Directory to save analysis results
        
    Returns:
        Path to the analysis report file
    """
    try:
        # Analyze content
        analysis = analyze_content(content)
        
        # Generate report
        report = generate_report(analysis)
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Save analysis
        analysis_file = output_path / "openai_analysis.json"
        with open(analysis_file, "w") as f:
            json.dump(analysis, f, indent=2)
        
        # Save report
        report_file = output_path / "openai_analysis_report.md"
        with open(report_file, "w") as f:
            f.write(report)
        
        return str(report_file)
        
    except ValueError as e:
        raise ValueError(f"Invalid content: {str(e)}")
    except openai.OpenAIError as e:
        raise Exception(f"OpenAI API error: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error during analysis: {str(e)}")

if __name__ == "__main__":
    example = "This is an example blog post about web accessibility..."
    try:
        report_path = analyze_and_save(example)
        print(f"Analysis saved to: {report_path}")
    except Exception as e:
        print(f"Error: {str(e)}")
