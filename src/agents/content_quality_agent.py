"""
Content quality checker agent for ensuring blog posts meet high standards.
"""

import re
from typing import Dict, List, Any, Tuple
from collections import Counter
import spacy
from textblob import TextBlob
import json
from pathlib import Path

# Import custom readability analyzer instead of external module
from src.utils.readability_analyzer import Readability

class ContentQualityChecker:
    def __init__(self):
        """Initialize the content quality checker with NLP models."""
        self.nlp = spacy.load("en_core_web_sm")
        
        # Accessibility-specific terminology
        self.accessibility_terms = {
            "wcag": "Web Content Accessibility Guidelines",
            "ada": "Americans with Disabilities Act",
            "section 508": "Section 508 compliance requirements",
            "aria": "Accessible Rich Internet Applications",
            "screen reader": "software that enables visually impaired users to read content",
            "alt text": "alternative text descriptions for images",
            "keyboard navigation": "ability to navigate using only keyboard",
            "color contrast": "difference in brightness between colors",
            "accessibility overlay": "tool that adds accessibility features to websites",
            "digital inclusion": "ensuring digital content is accessible to all"
        }
        
        # Emotional and empathetic language patterns
        self.empathy_patterns = [
            r"\b(?:understand|appreciate|recognize|acknowledge)\b.*\b(?:needs|challenges|difficulties)\b",
            r"\b(?:help|support|assist|enable)\b.*\b(?:you|users|people|individuals)\b",
            r"\b(?:together|partnership|collaborate)\b",
            r"\b(?:committed|dedicated|passionate)\b.*\b(?:accessibility|inclusion)\b"
        ]
        
        # Technical accuracy checklist
        self.technical_requirements = {
            "wcag_version": r"WCAG\s*2\.[0-9]+",
            "ada_reference": r"ADA\s+compliance",
            "section_508": r"Section\s+508",
            "standards_mentioned": ["WCAG", "ADA", "Section 508", "EN 301 549"]
        }

    def analyze_content(self, content: str) -> Dict[str, Any]:
        """
        Perform comprehensive content analysis.
        
        Args:
            content: Blog post content
            
        Returns:
            Dictionary containing analysis results
        """
        doc = self.nlp(content)
        blob = TextBlob(content)
        
        # Basic metrics
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        sentences = [sent.text.strip() for sent in doc.sents]
        words = [token.text for token in doc if not token.is_punct and not token.is_space]
        
        analysis = {
            "structure": self._analyze_structure(paragraphs, sentences),
            "readability": self._analyze_readability(content),
            "technical_accuracy": self._check_technical_accuracy(content),
            "empathy_score": self._analyze_empathy(content),
            "seo_optimization": self._analyze_seo(content),
            "content_flow": self._analyze_flow(sentences),
            "emotional_impact": self._analyze_emotional_impact(content),
            "accessibility_coverage": self._analyze_accessibility_coverage(content),
            "improvements": []
        }
        
        # Generate improvement suggestions
        analysis["improvements"] = self._generate_improvements(analysis)
        
        return analysis

    def _analyze_structure(self, paragraphs: List[str], sentences: List[str]) -> Dict[str, Any]:
        """Analyze content structure."""
        return {
            "paragraph_count": len(paragraphs),
            "avg_paragraph_length": sum(len(p.split()) for p in paragraphs) / len(paragraphs) if paragraphs else 0,
            "sentence_count": len(sentences),
            "avg_sentence_length": sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0,
            "paragraph_length_distribution": {
                "short": sum(1 for p in paragraphs if len(p.split()) < 50),
                "medium": sum(1 for p in paragraphs if 50 <= len(p.split()) <= 100),
                "long": sum(1 for p in paragraphs if len(p.split()) > 100)
            }
        }

    def _analyze_readability(self, content: str) -> Dict[str, float]:
        """Analyze content readability."""
        r = Readability(content)
        flesch_score = r.flesch()
        return {
            "flesch_reading_ease": flesch_score,
            "flesch_kincaid_grade": r.flesch_kincaid(),
            "gunning_fog": r.gunning_fog(),
            "smog": r.smog(),
            "dale_chall": r.dale_chall(),
            "difficulty_level": self._calculate_difficulty_level(flesch_score)
        }

    def _check_technical_accuracy(self, content: str) -> Dict[str, Any]:
        """Check technical accuracy of accessibility-related content."""
        content_lower = content.lower()
        return {
            "standards_mentioned": [
                std for std in self.technical_requirements["standards_mentioned"]
                if std.lower() in content_lower
            ],
            "wcag_version_mentioned": bool(re.search(self.technical_requirements["wcag_version"], content)),
            "ada_mentioned": bool(re.search(self.technical_requirements["ada_reference"], content)),
            "section_508_mentioned": bool(re.search(self.technical_requirements["section_508"], content)),
            "technical_terms_used": self._find_technical_terms(content)
        }

    def _analyze_empathy(self, content: str) -> Dict[str, Any]:
        """Analyze empathetic language use."""
        empathy_matches = []
        for pattern in self.empathy_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            empathy_matches.extend([m.group(0) for m in matches])
        
        return {
            "empathy_pattern_count": len(empathy_matches),
            "empathy_examples": empathy_matches[:5],
            "empathy_score": min(10, len(empathy_matches) * 2)  # Score out of 10
        }

    def _analyze_seo(self, content: str) -> Dict[str, Any]:
        """Analyze SEO optimization."""
        doc = self.nlp(content)
        
        # Extract potential keywords (nouns and noun phrases)
        keywords = []
        for chunk in doc.noun_chunks:
            if 2 <= len(chunk.text.split()) <= 4:  # Focus on 2-4 word phrases
                keywords.append(chunk.text.lower())
        
        keyword_freq = Counter(keywords)
        
        return {
            "top_keywords": [{"keyword": k, "frequency": v} for k, v in keyword_freq.most_common(5)],
            "keyword_density": {k: v/len(content.split()) for k, v in keyword_freq.most_common(5)},
            "meta_description_length": len(content.split('\n')[0]) if content else 0,
            "has_meta_description": bool(content.split('\n')[0])
        }

    def _analyze_flow(self, sentences: List[str]) -> Dict[str, Any]:
        """Analyze content flow and transitions."""
        transition_words = set([
            "however", "therefore", "furthermore", "moreover", "additionally",
            "consequently", "meanwhile", "nevertheless", "similarly", "in contrast"
        ])
        
        transitions = []
        for sent in sentences:
            words = set(sent.lower().split())
            transitions.extend([word for word in words if word in transition_words])
        
        return {
            "transition_word_count": len(transitions),
            "transition_density": len(transitions) / len(sentences) if sentences else 0,
            "unique_transitions": list(set(transitions))
        }

    def _analyze_emotional_impact(self, content: str) -> Dict[str, Any]:
        """Analyze emotional impact of content."""
        blob = TextBlob(content)
        sentences = [str(sent) for sent in blob.sentences]
        
        sentiment_scores = [sent.sentiment.polarity for sent in blob.sentences]
        subjectivity_scores = [sent.sentiment.subjectivity for sent in blob.sentences]
        
        return {
            "overall_sentiment": sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0,
            "sentiment_consistency": self._calculate_consistency(sentiment_scores),
            "subjectivity": sum(subjectivity_scores) / len(subjectivity_scores) if subjectivity_scores else 0,
            "emotional_sentences": [
                sent for sent, score in zip(sentences, sentiment_scores)
                if abs(score) > 0.5
            ][:3]  # Top 3 emotional sentences
        }

    def _analyze_accessibility_coverage(self, content: str) -> Dict[str, Any]:
        """Analyze coverage of accessibility topics."""
        content_lower = content.lower()
        covered_terms = {}
        
        for term, description in self.accessibility_terms.items():
            if term in content_lower:
                covered_terms[term] = {
                    "mentioned": True,
                    "context": self._find_context(content, term),
                    "description": description
                }
        
        return {
            "terms_covered": len(covered_terms),
            "coverage_percentage": (len(covered_terms) / len(self.accessibility_terms)) * 100,
            "covered_terms": covered_terms
        }

    def _find_technical_terms(self, content: str) -> List[Dict[str, str]]:
        """Find technical terms and their context."""
        technical_terms = []
        for term, description in self.accessibility_terms.items():
            if term in content.lower():
                context = self._find_context(content, term)
                if context:
                    technical_terms.append({
                        "term": term,
                        "context": context,
                        "description": description
                    })
        return technical_terms

    def _find_context(self, content: str, term: str, window: int = 100) -> str:
        """Find context around a term in content."""
        match = re.search(f".{{0,{window}}}{term}.{{0,{window}}}", content, re.IGNORECASE)
        if match:
            return match.group(0).strip()
        return ""

    def _calculate_consistency(self, scores: List[float]) -> float:
        """Calculate consistency of scores."""
        if not scores:
            return 0
        return 1 - (max(scores) - min(scores))

    def _calculate_difficulty_level(self, flesch_score: float) -> str:
        """Convert Flesch reading ease score to difficulty level."""
        if flesch_score >= 80:
            return "Easy"
        elif flesch_score >= 60:
            return "Standard"
        elif flesch_score >= 50:
            return "Fairly Difficult"
        else:
            return "Difficult"

    def _generate_improvements(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate improvement suggestions based on analysis."""
        improvements = []
        
        # Structure improvements
        if analysis["structure"]["avg_paragraph_length"] > 100:
            improvements.append({
                "category": "Structure",
                "issue": "Paragraphs are too long",
                "suggestion": "Break down paragraphs longer than 100 words into smaller, more digestible chunks"
            })
        
        # Readability improvements
        if analysis["readability"]["flesch_reading_ease"] < 60:
            improvements.append({
                "category": "Readability",
                "issue": "Content might be too complex",
                "suggestion": "Simplify language and use shorter sentences to improve readability"
            })
        
        # Technical accuracy improvements
        if len(analysis["technical_accuracy"]["standards_mentioned"]) < 2:
            improvements.append({
                "category": "Technical Accuracy",
                "issue": "Limited mention of accessibility standards",
                "suggestion": "Include more references to key accessibility standards (WCAG, ADA, Section 508)"
            })
        
        # Empathy improvements
        if analysis["empathy_score"]["empathy_score"] < 5:
            improvements.append({
                "category": "Empathy",
                "issue": "Low empathy score",
                "suggestion": "Add more empathetic language and acknowledge user challenges"
            })
        
        # Flow improvements
        if analysis["content_flow"]["transition_density"] < 0.2:
            improvements.append({
                "category": "Flow",
                "issue": "Limited use of transition words",
                "suggestion": "Add more transition words to improve content flow"
            })
        
        # Emotional impact improvements
        if abs(analysis["emotional_impact"]["overall_sentiment"]) < 0.2:
            improvements.append({
                "category": "Emotional Impact",
                "issue": "Neutral emotional tone",
                "suggestion": "Add more emotionally engaging content while maintaining professionalism"
            })
        
        # Accessibility coverage improvements
        if analysis["accessibility_coverage"]["coverage_percentage"] < 70:
            improvements.append({
                "category": "Accessibility Coverage",
                "issue": "Limited coverage of accessibility terms",
                "suggestion": "Include more accessibility-specific terminology and explanations"
            })
        
        return improvements

    def generate_report(self, analysis: Dict[str, Any]) -> str:
        """Generate a human-readable report from analysis results."""
        report = []
        
        # Overall scores
        report.append("# Content Quality Analysis Report\n")
        report.append("## Overall Scores")
        report.append(f"- Readability Score: {analysis['readability']['flesch_reading_ease']:.1f}/100")
        report.append(f"- Empathy Score: {analysis['empathy_score']['empathy_score']}/10")
        report.append(f"- Technical Accuracy: {len(analysis['technical_accuracy']['standards_mentioned'])}/4 standards covered")
        report.append(f"- Accessibility Coverage: {analysis['accessibility_coverage']['coverage_percentage']:.1f}%\n")
        
        # Structure analysis
        report.append("## Structure")
        report.append(f"- Paragraphs: {analysis['structure']['paragraph_count']}")
        report.append(f"- Average paragraph length: {analysis['structure']['avg_paragraph_length']:.1f} words")
        report.append(f"- Sentence count: {analysis['structure']['sentence_count']}\n")
        
        # Technical content
        report.append("## Technical Content")
        report.append("Standards mentioned:")
        for standard in analysis['technical_accuracy']['standards_mentioned']:
            report.append(f"- {standard}")
        report.append("")
        
        # Improvements
        report.append("## Suggested Improvements")
        for imp in analysis['improvements']:
            report.append(f"### {imp['category']}")
            report.append(f"**Issue**: {imp['issue']}")
            report.append(f"**Suggestion**: {imp['suggestion']}\n")
        
        return "\n".join(report)

def analyze_blog_post(content: str, output_dir: str = "analysis") -> str:
    """
    Analyze a blog post and save the results.
    
    Args:
        content: Blog post content
        output_dir: Directory to save analysis results
        
    Returns:
        Path to the analysis report
    """
    # Create checker instance
    checker = ContentQualityChecker()
    
    # Analyze content
    analysis = checker.analyze_content(content)
    
    # Generate report
    report = checker.generate_report(analysis)
    
    # Save results
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Save detailed analysis
    analysis_file = output_path / "content_analysis.json"
    with open(analysis_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    # Save human-readable report
    report_file = output_path / "content_analysis_report.md"
    with open(report_file, 'w') as f:
        f.write(report)
    
    return str(report_file)

if __name__ == "__main__":
    # Example usage
    blog_content = """
    # Example Blog Post
    This is an example blog post about web accessibility...
    """
    
    report_path = analyze_blog_post(blog_content)
    print(f"Analysis report saved to: {report_path}")
