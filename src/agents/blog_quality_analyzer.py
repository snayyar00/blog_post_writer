"""
Blog quality analyzer focused on accessibility content, empathetic writing,
and long-tail keyword optimization.
"""
from typing import Dict, List, Any, Optional
import re
from pathlib import Path
import json
from collections import Counter
from textblob import TextBlob
from datetime import datetime
from ..utils.long_tail_keyword_analyzer import analyze_blog_for_long_tail_keywords

def analyze_blog_structure(content: str) -> Dict[str, Any]:
    """Analyze blog structure and organization."""
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    sentences = [s.strip() for s in re.split(r'[.!?]+', content) if s.strip()]
    
    return {
        "paragraph_stats": {
            "count": len(paragraphs),
            "avg_length": sum(len(p.split()) for p in paragraphs) / len(paragraphs) if paragraphs else 0,
            "length_distribution": {
                "short": sum(1 for p in paragraphs if len(p.split()) < 50),
                "medium": sum(1 for p in paragraphs if 50 <= len(p.split()) <= 100),
                "long": sum(1 for p in paragraphs if len(p.split()) > 100)
            }
        },
        "sentence_stats": {
            "count": len(sentences),
            "avg_length": sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        }
    }

def analyze_accessibility_coverage(content: str) -> Dict[str, Any]:
    """Analyze coverage of accessibility-related topics."""
    accessibility_terms = {
        "wcag": "Web Content Accessibility Guidelines",
        "ada": "Americans with Disabilities Act",
        "section 508": "Section 508",
        "aria": "Accessible Rich Internet Applications",
        "screen reader": "Screen reader compatibility",
        "keyboard navigation": "Keyboard accessibility",
        "color contrast": "Color contrast requirements",
        "alt text": "Alternative text",
        "focus indicators": "Focus visibility",
        "semantic markup": "Semantic HTML"
    }
    
    content_lower = content.lower()
    covered_terms = {}
    
    for term, description in accessibility_terms.items():
        if term in content_lower:
            context = re.search(f".{{0,100}}{term}.{{0,100}}", content_lower)
            covered_terms[term] = {
                "description": description,
                "context": context.group(0) if context else None
            }
    
    return {
        "terms_covered": len(covered_terms),
        "coverage_score": (len(covered_terms) / len(accessibility_terms)) * 10,
        "covered_terms": covered_terms,
        "missing_terms": [term for term in accessibility_terms if term not in covered_terms]
    }

def analyze_empathy_and_tone(content: str) -> Dict[str, Any]:
    """Analyze empathetic language and tone."""
    empathy_patterns = {
        "understanding": r"\b(?:understand|appreciate|recognize)\b.*\b(?:needs|challenges|difficulties)\b",
        "support": r"\b(?:help|support|assist|enable)\b.*\b(?:you|users|people)\b",
        "inclusive": r"\b(?:everyone|all users|inclusive|accessible)\b",
        "commitment": r"\b(?:committed|dedicated|ensure)\b.*\b(?:accessibility|inclusion)\b"
    }
    
    blob = TextBlob(content)
    sentiment_scores = [sentence.sentiment.polarity for sentence in blob.sentences]
    
    empathy_matches = {}
    for category, pattern in empathy_patterns.items():
        matches = re.finditer(pattern, content, re.IGNORECASE)
        empathy_matches[category] = [m.group(0) for m in matches]
    
    return {
        "empathy_score": sum(len(matches) for matches in empathy_matches.values()),
        "empathy_examples": empathy_matches,
        "tone_analysis": {
            "overall_sentiment": sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0,
            "sentiment_consistency": max(sentiment_scores) - min(sentiment_scores) if sentiment_scores else 0
        }
    }

def analyze_technical_accuracy(content: str) -> Dict[str, Any]:
    """Analyze technical accuracy of accessibility content."""
    required_standards = ["WCAG", "ADA", "Section 508"]
    version_patterns = {
        "wcag": r"WCAG\s*2\.[0-9]+",
        "section_508": r"Section\s+508"
    }
    
    standards_mentioned = [std for std in required_standards if std in content]
    versions_found = {
        name: re.search(pattern, content) is not None
        for name, pattern in version_patterns.items()
    }
    
    return {
        "standards_coverage": {
            "mentioned": standards_mentioned,
            "missing": [std for std in required_standards if std not in standards_mentioned],
            "coverage_score": (len(standards_mentioned) / len(required_standards)) * 10
        },
        "versions_mentioned": versions_found
    }

def analyze_content_flow(content: str) -> Dict[str, Any]:
    """Analyze content flow and transitions."""
    transition_words = {
        "addition": ["additionally", "furthermore", "moreover", "also"],
        "contrast": ["however", "nevertheless", "on the other hand"],
        "example": ["for example", "for instance", "specifically"],
        "result": ["therefore", "consequently", "as a result"],
        "emphasis": ["importantly", "notably", "significantly"]
    }
    
    transition_counts = {category: 0 for category in transition_words}
    for category, words in transition_words.items():
        for word in words:
            transition_counts[category] += len(re.findall(r'\b' + word + r'\b', content, re.IGNORECASE))
    
    return {
        "transition_usage": transition_counts,
        "total_transitions": sum(transition_counts.values()),
        "flow_score": min(10, sum(transition_counts.values()) / 2)
    }

def generate_improvement_suggestions(analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate specific improvement suggestions based on analysis."""
    suggestions = []
    
    # Structure suggestions
    if analysis["structure"]["paragraph_stats"]["avg_length"] > 100:
        suggestions.append({
            "category": "Structure",
            "issue": "Paragraphs are too long",
            "suggestion": "Break down paragraphs longer than 100 words for better readability"
        })
    
    # Accessibility coverage suggestions
    if analysis["accessibility"]["coverage_score"] < 7:
        missing_terms = ", ".join(analysis["accessibility"]["missing_terms"][:3])
        suggestions.append({
            "category": "Accessibility Coverage",
            "issue": "Limited coverage of accessibility terms",
            "suggestion": f"Add coverage of key terms: {missing_terms}"
        })
    
    # Empathy suggestions
    if analysis["empathy"]["empathy_score"] < 5:
        suggestions.append({
            "category": "Empathy",
            "issue": "Low empathy score",
            "suggestion": "Add more empathetic language acknowledging user challenges and needs"
        })
    
    # Technical accuracy suggestions
    if analysis["technical"]["standards_coverage"]["coverage_score"] < 7:
        missing_standards = ", ".join(analysis["technical"]["standards_coverage"]["missing"])
        suggestions.append({
            "category": "Technical Accuracy",
            "issue": "Missing key accessibility standards",
            "suggestion": f"Include references to: {missing_standards}"
        })
    
    # Flow suggestions
    if analysis["flow"]["flow_score"] < 6:
        suggestions.append({
            "category": "Content Flow",
            "issue": "Limited use of transition words",
            "suggestion": "Add more transition words to improve content flow between paragraphs"
        })
    
    return suggestions

def analyze_blog_post(content: str) -> Dict[str, Any]:
    """
    Perform comprehensive blog post analysis including long-tail keyword optimization.
    
    Args:
        content: Blog post content
        
    Returns:
        Dictionary containing analysis results and suggestions
    """
    # Perform all analyses
    structure_analysis = analyze_blog_structure(content)
    accessibility_analysis = analyze_accessibility_coverage(content)
    empathy_analysis = analyze_empathy_and_tone(content)
    technical_analysis = analyze_technical_accuracy(content)
    flow_analysis = analyze_content_flow(content)
    
    # Perform long-tail keyword analysis
    long_tail_analysis = analyze_blog_for_long_tail_keywords(content)
    
    # Combine results
    analysis = {
        "structure": structure_analysis,
        "accessibility": accessibility_analysis,
        "empathy": empathy_analysis,
        "technical": technical_analysis,
        "flow": flow_analysis,
        "long_tail_keywords": long_tail_analysis["analysis"]
    }
    
    # Generate improvement suggestions
    suggestions = generate_improvement_suggestions(analysis)
    
    # Add long-tail keyword suggestions
    suggestions.extend(long_tail_analysis["suggestions"])
    
    # Calculate overall quality score
    quality_scores = {
        "accessibility_score": accessibility_analysis["coverage_score"],
        "empathy_score": min(10, empathy_analysis["empathy_score"]),
        "technical_score": technical_analysis["standards_coverage"]["coverage_score"],
        "flow_score": flow_analysis["flow_score"],
        "long_tail_score": long_tail_analysis["analysis"]["long_tail_usage"]["score"]
    }
    
    overall_score = sum(quality_scores.values()) / len(quality_scores)
    
    return {
        "analysis": analysis,
        "quality_scores": quality_scores,
        "overall_score": overall_score,
        "suggestions": suggestions,
        "timestamp": datetime.now().isoformat()
    }

def generate_report(analysis_results: Dict[str, Any]) -> str:
    """Generate a human-readable report from analysis results."""
    report = []
    
    # Overall score
    report.append("# Blog Post Analysis Report\n")
    report.append(f"## Overall Quality Score: {analysis_results['overall_score']:.1f}/10\n")
    
    # Quality scores breakdown
    report.append("## Quality Scores")
    for category, score in analysis_results["quality_scores"].items():
        report.append(f"- {category.replace('_', ' ').title()}: {score:.1f}/10")
    report.append("")
    
    # Structure analysis
    structure = analysis_results["analysis"]["structure"]
    report.append("## Structure Analysis")
    report.append(f"- Paragraphs: {structure['paragraph_stats']['count']}")
    report.append(f"- Average paragraph length: {structure['paragraph_stats']['avg_length']:.1f} words")
    report.append(f"- Sentences: {structure['sentence_stats']['count']}")
    report.append("")
    
    # Accessibility coverage
    accessibility = analysis_results["analysis"]["accessibility"]
    report.append("## Accessibility Coverage")
    report.append(f"- Terms covered: {accessibility['terms_covered']}")
    report.append(f"- Coverage score: {accessibility['coverage_score']:.1f}/10")
    if accessibility["missing_terms"]:
        report.append("- Missing terms: " + ", ".join(accessibility["missing_terms"]))
    report.append("")
    
    # Improvement suggestions
    report.append("## Suggested Improvements")
    for suggestion in analysis_results["suggestions"]:
        report.append(f"### {suggestion['category']}")
        report.append(f"**Issue**: {suggestion['issue']}")
        report.append(f"**Suggestion**: {suggestion['suggestion']}\n")
    
    return "\n".join(report)

def save_analysis(content: str, output_dir: str = "analysis") -> str:
    """
    Analyze blog post and save results.
    
    Args:
        content: Blog post content
        output_dir: Directory to save analysis results
        
    Returns:
        Path to the analysis report
    """
    # Analyze content
    analysis_results = analyze_blog_post(content)
    
    # Generate report
    report = generate_report(analysis_results)
    
    # Save results
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Save detailed analysis
    analysis_file = output_path / "blog_analysis.json"
    with open(analysis_file, "w") as f:
        json.dump(analysis_results, f, indent=2)
    
    # Save human-readable report
    report_file = output_path / "blog_analysis_report.md"
    with open(report_file, "w") as f:
        f.write(report)
    
    return str(report_file)

if __name__ == "__main__":
    # Example usage
    blog_content = """
    # Example Blog Post
    This is an example blog post about web accessibility...
    """
    
    report_path = save_analysis(blog_content)
    print(f"Analysis report saved to: {report_path}")
