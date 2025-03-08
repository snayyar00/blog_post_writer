"""
Content analysis utilities for blog posts with focus on accessibility.
"""
from typing import Dict, List, Any, Optional
from typing_extensions import TypedDict
from dataclasses import dataclass
from pathlib import Path
import re
import json

@dataclass
class ContentImprovement:
    """Represents a suggested improvement for the content."""
    category: str
    issue: str
    suggestion: str

def analyze_structure(content: str) -> Dict[str, Any]:
    """Analyze content structure and organization."""
    if not content:
        return {"error": "Empty content"}
        
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    sentences = [s.strip() for s in re.split(r'[.!?]+', content) if s.strip()]
    
    return {
        "paragraphs": {
            "count": len(paragraphs),
            "avg_length": sum(len(p.split()) for p in paragraphs) / len(paragraphs) if paragraphs else 0,
            "long_paragraphs": sum(1 for p in paragraphs if len(p.split()) > 100)
        },
        "sentences": {
            "count": len(sentences),
            "avg_length": sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        }
    }

def analyze_accessibility_terms(content: str) -> Dict[str, Any]:
    """Analyze coverage of accessibility-related terms."""
    accessibility_terms = {
        "wcag": "Web Content Accessibility Guidelines",
        "ada": "Americans with Disabilities Act",
        "section 508": "Section 508 compliance",
        "screen reader": "Screen reader compatibility",
        "keyboard navigation": "Keyboard accessibility",
        "color contrast": "Color contrast requirements",
        "alt text": "Alternative text",
        "aria": "Accessible Rich Internet Applications"
    }
    
    content_lower = content.lower()
    covered_terms = {
        term: description
        for term, description in accessibility_terms.items()
        if term in content_lower
    }
    
    return {
        "terms_covered": len(covered_terms),
        "coverage_score": (len(covered_terms) / len(accessibility_terms)) * 10,
        "covered_terms": covered_terms,
        "missing_terms": [
            term for term in accessibility_terms 
            if term not in covered_terms
        ]
    }

def analyze_empathy(content: str) -> Dict[str, Any]:
    """Analyze empathetic language usage."""
    empathy_patterns = [
        r"\b(?:understand|appreciate|recognize)\b.*\b(?:needs|challenges|difficulties)\b",
        r"\b(?:help|support|assist|enable)\b.*\b(?:you|users|people)\b",
        r"\b(?:everyone|all users|inclusive|accessible)\b",
        r"\b(?:committed|dedicated|ensure)\b.*\b(?:accessibility|inclusion)\b"
    ]
    
    matches = []
    for pattern in empathy_patterns:
        found = re.finditer(pattern, content, re.IGNORECASE)
        matches.extend([m.group(0) for m in found])
    
    return {
        "empathy_score": min(10, len(matches) * 2),
        "examples": matches[:3],
        "needs_improvement": len(matches) < 3
    }

def analyze_technical_accuracy(content: str) -> Dict[str, Any]:
    """Analyze technical accuracy of content."""
    requirements = {
        "wcag_version": r"WCAG\s*2\.[0-9]+",
        "ada_reference": r"ADA\s+compliance",
        "section_508": r"Section\s+508"
    }
    
    met_requirements = {
        name: bool(re.search(pattern, content, re.IGNORECASE))
        for name, pattern in requirements.items()
    }
    
    return {
        "requirements_met": met_requirements,
        "score": (sum(met_requirements.values()) / len(met_requirements)) * 10
    }

def analyze_content_flow(content: str) -> Dict[str, Any]:
    """Analyze content flow and transitions."""
    transition_words = [
        "additionally", "furthermore", "moreover",
        "however", "nevertheless", "conversely",
        "therefore", "consequently", "thus",
        "specifically", "for example", "notably"
    ]
    
    transition_count = sum(
        1 for word in transition_words 
        if re.search(r'\b' + word + r'\b', content, re.IGNORECASE)
    )
    
    return {
        "transition_count": transition_count,
        "flow_score": min(10, transition_count * 2),
        "needs_improvement": transition_count < 5
    }

def get_improvement_suggestions(analysis: Dict[str, Any]) -> List[ContentImprovement]:
    """Generate improvement suggestions based on analysis results."""
    suggestions = []
    
    # Structure suggestions
    if analysis["structure"]["paragraphs"]["long_paragraphs"] > 0:
        suggestions.append(ContentImprovement(
            category="Structure",
            issue="Long paragraphs detected",
            suggestion="Break down paragraphs longer than 100 words for better readability"
        ))
    
    # Accessibility suggestions
    if analysis["accessibility"]["coverage_score"] < 7:
        missing = ", ".join(analysis["accessibility"]["missing_terms"][:3])
        suggestions.append(ContentImprovement(
            category="Accessibility Coverage",
            issue="Missing key accessibility terms",
            suggestion=f"Add coverage of: {missing}"
        ))
    
    # Empathy suggestions
    if analysis["empathy"]["needs_improvement"]:
        suggestions.append(ContentImprovement(
            category="Empathy",
            issue="Limited empathetic language",
            suggestion="Add more phrases acknowledging user challenges and needs"
        ))
    
    # Technical suggestions
    if analysis["technical"]["score"] < 7:
        suggestions.append(ContentImprovement(
            category="Technical Accuracy",
            issue="Missing technical requirements",
            suggestion="Include specific versions of accessibility standards"
        ))
    
    # Flow suggestions
    if analysis["flow"]["needs_improvement"]:
        suggestions.append(ContentImprovement(
            category="Content Flow",
            issue="Limited transitions",
            suggestion="Add more transition words between paragraphs"
        ))
    
    return suggestions

def analyze_content(content: str) -> Dict[str, Any]:
    """
    Perform comprehensive content analysis.
    
    Args:
        content: Blog post content
        
    Returns:
        Dictionary containing analysis results
    """
    if not content:
        raise ValueError("Content cannot be empty")
    
    analysis = {
        "structure": analyze_structure(content),
        "accessibility": analyze_accessibility_terms(content),
        "empathy": analyze_empathy(content),
        "technical": analyze_technical_accuracy(content),
        "flow": analyze_content_flow(content)
    }
    
    # Calculate overall score
    scores = [
        analysis["accessibility"]["coverage_score"],
        analysis["empathy"]["empathy_score"],
        analysis["technical"]["score"],
        analysis["flow"]["flow_score"]
    ]
    analysis["overall_score"] = sum(scores) / len(scores)
    
    # Get improvement suggestions
    analysis["improvements"] = [
        {"category": imp.category, "issue": imp.issue, "suggestion": imp.suggestion}
        for imp in get_improvement_suggestions(analysis)
    ]
    
    return analysis

def generate_report(analysis: Dict[str, Any]) -> str:
    """Generate a markdown report from analysis results."""
    report = []
    
    # Overall score
    report.append("# Blog Post Analysis Report\n")
    report.append(f"## Overall Score: {analysis['overall_score']:.1f}/10\n")
    
    # Structure
    struct = analysis["structure"]
    report.append("## Structure Analysis")
    report.append(f"- Paragraphs: {struct['paragraphs']['count']}")
    report.append(f"- Average paragraph length: {struct['paragraphs']['avg_length']:.1f} words")
    report.append(f"- Long paragraphs: {struct['paragraphs']['long_paragraphs']}")
    report.append(f"- Sentences: {struct['sentences']['count']}\n")
    
    # Accessibility
    access = analysis["accessibility"]
    report.append("## Accessibility Coverage")
    report.append(f"- Coverage Score: {access['coverage_score']:.1f}/10")
    report.append("- Missing Terms:")
    for term in access["missing_terms"][:3]:
        report.append(f"  * {term}")
    report.append("")
    
    # Empathy
    empathy = analysis["empathy"]
    report.append("## Empathy Analysis")
    report.append(f"- Empathy Score: {empathy['empathy_score']}/10")
    if empathy["examples"]:
        report.append("- Examples of empathetic language:")
        for example in empathy["examples"]:
            report.append(f"  * {example}")
    report.append("")
    
    # Technical
    tech = analysis["technical"]
    report.append("## Technical Analysis")
    report.append(f"- Technical Score: {tech['score']:.1f}/10")
    report.append("- Requirements Met:")
    for req, met in tech["requirements_met"].items():
        report.append(f"  * {req}: {'✓' if met else '✗'}")
    report.append("")
    
    # Flow
    flow = analysis["flow"]
    report.append("## Content Flow")
    report.append(f"- Flow Score: {flow['flow_score']}/10")
    report.append(f"- Transition words used: {flow['transition_count']}\n")
    
    # Improvements
    report.append("## Suggested Improvements")
    for imp in analysis["improvements"]:
        report.append(f"### {imp['category']}")
        report.append(f"**Issue**: {imp['issue']}")
        report.append(f"**Suggestion**: {imp['suggestion']}\n")
    
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
        analysis_file = output_path / "content_analysis.json"
        with open(analysis_file, "w") as f:
            json.dump(analysis, f, indent=2)
        
        # Save report
        report_file = output_path / "content_analysis_report.md"
        with open(report_file, "w") as f:
            f.write(report)
        
        return str(report_file)
        
    except ValueError as e:
        raise ValueError(f"Invalid content: {str(e)}")
    except OSError as e:
        raise OSError(f"Error saving analysis: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error during analysis: {str(e)}")
