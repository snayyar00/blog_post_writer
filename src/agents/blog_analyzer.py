"""
Advanced blog analyzer focused on accessibility content, quality, and SEO optimization
with special emphasis on long-tail keyword implementation and content engagement metrics.
"""
from typing import Dict, List, Any, Optional, Set, Tuple
import re
from pathlib import Path
import json
from collections import Counter
import nltk
from datetime import datetime

class BlogAnalyzer:
    def __init__(self):
        # Ensure NLTK resources are available
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')
            
        # Key accessibility terms and their importance
        self.accessibility_terms = {
            "wcag": "Web Content Accessibility Guidelines - Core standard for web accessibility",
            "ada": "Americans with Disabilities Act - Legal requirement for accessibility",
            "section 508": "Federal accessibility requirements",
            "screen reader": "Essential tool for visually impaired users",
            "keyboard navigation": "Critical for users who can't use a mouse",
            "color contrast": "Important for users with visual impairments",
            "alt text": "Required for image accessibility",
            "aria": "Accessible Rich Internet Applications",
            "semantic html": "Proper markup for accessibility",
            "focus indicators": "Visual cues for keyboard navigation"
        }
        
        # Empathetic language patterns
        self.empathy_patterns = [
            r"\b(?:understand|appreciate|recognize)\b.*\b(?:needs|challenges|difficulties)\b",
            r"\b(?:help|support|assist|enable)\b.*\b(?:you|users|people)\b",
            r"\b(?:everyone|all users|inclusive|accessible)\b",
            r"\b(?:committed|dedicated|ensure)\b.*\b(?:accessibility|inclusion)\b"
        ]
        
        # Technical requirements
        self.technical_requirements = {
            "wcag_version": r"WCAG\s*2\.[0-9]+",
            "ada_compliance": r"ADA\s+compliance",
            "section_508": r"Section\s+508"
        }
        
        # Transition words for flow
        self.transition_words = [
            "additionally", "furthermore", "moreover",
            "however", "nevertheless", "conversely",
            "therefore", "consequently", "thus",
            "specifically", "for example", "notably"
        ]
        
        # SEO optimization patterns
        self.seo_patterns = {
            "meta_description": r"meta\s+description",
            "heading_structure": r"<h[1-6]|#{1,6}\s",
            "keyword_in_title": r"<h1|^#\s",
            "internal_links": r"\[.*?\]\(.*?\)",
            "external_links": r"\[.*?\]\(https?://.*?\)",
            "image_alt_text": r"!\[.*?\]",
            "list_items": r"[-*]\s|[0-9]+\.\s",
            "schema_markup": r"schema\.org|json-ld"
        }
        
        # Long-tail keyword patterns (3+ word phrases)
        self.long_tail_patterns = [
            r"how\s+to\s+[a-z]+\s+[a-z]+",
            r"why\s+(?:is|are|does|do)\s+[a-z]+\s+[a-z]+",
            r"what\s+(?:is|are)\s+[a-z]+\s+[a-z]+\s+[a-z]+",
            r"best\s+[a-z]+\s+for\s+[a-z]+",
            r"top\s+[0-9]+\s+[a-z]+\s+[a-z]+",
            r"[a-z]+\s+vs\s+[a-z]+\s+[a-z]+",
            r"[a-z]+\s+[a-z]+\s+examples",
            r"[a-z]+\s+[a-z]+\s+benefits"
        ]
        
        # User engagement signals
        self.engagement_patterns = {
            "questions": r"\?",
            "calls_to_action": r"(?:click|download|subscribe|sign up|learn more|contact|try|get started)",
            "personal_pronouns": r"\b(?:you|your|we|our)\b",
            "emotional_words": r"\b(?:amazing|incredible|essential|crucial|vital|exciting|surprising)\b",
            "data_points": r"[0-9]+%|[0-9]+\s+(?:million|billion|trillion)"
        }
        
        # Stop words for keyword analysis
        self.stop_words = set(nltk.corpus.stopwords.words('english'))

    def analyze_structure(self, content: str) -> Dict[str, Any]:
        """Analyze blog structure."""
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        sentences = [s.strip() for s in re.split(r'[.!?]+', content) if s.strip()]
        
        return {
            "paragraphs": {
                "count": len(paragraphs),
                "avg_length": sum(len(p.split()) for p in paragraphs) / len(paragraphs) if paragraphs else 0,
                "issues": [
                    i for i, p in enumerate(paragraphs) 
                    if len(p.split()) > 100 or len(p.split()) < 20
                ]
            },
            "sentences": {
                "count": len(sentences),
                "avg_length": sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
            }
        }

    def analyze_accessibility(self, content: str) -> Dict[str, Any]:
        """Analyze accessibility coverage."""
        content_lower = content.lower()
        covered_terms = {}
        
        for term, description in self.accessibility_terms.items():
            if term in content_lower:
                context = re.search(f".{{0,100}}{term}.{{0,100}}", content_lower)
                covered_terms[term] = {
                    "description": description,
                    "context": context.group(0) if context else None
                }
        
        return {
            "terms_covered": len(covered_terms),
            "coverage_score": (len(covered_terms) / len(self.accessibility_terms)) * 10,
            "covered_terms": covered_terms,
            "missing_terms": [
                term for term in self.accessibility_terms 
                if term not in covered_terms
            ]
        }

    def analyze_empathy(self, content: str) -> Dict[str, Any]:
        """Analyze empathetic language."""
        empathy_matches = []
        for pattern in self.empathy_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            empathy_matches.extend([m.group(0) for m in matches])
        
        return {
            "empathy_score": min(10, len(empathy_matches) * 2),
            "empathy_examples": empathy_matches[:3],
            "needs_improvement": len(empathy_matches) < 3
        }

    def analyze_technical(self, content: str) -> Dict[str, Any]:
        """Analyze technical accuracy."""
        results = {}
        for req_name, pattern in self.technical_requirements.items():
            match = re.search(pattern, content, re.IGNORECASE)
            results[req_name] = bool(match)
        
        return {
            "requirements_met": results,
            "score": (sum(results.values()) / len(results)) * 10
        }

    def analyze_flow(self, content: str) -> Dict[str, Any]:
        """Analyze content flow."""
        transition_count = sum(
            1 for word in self.transition_words 
            if re.search(r'\b' + word + r'\b', content, re.IGNORECASE)
        )
        
        return {
            "transition_count": transition_count,
            "flow_score": min(10, transition_count * 2),
            "needs_improvement": transition_count < 5
        }

    def generate_improvements(self, analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate improvement suggestions for all aspects of the blog."""
        suggestions = []
        
        # Structure improvements
        if analysis["structure"]["paragraphs"]["avg_length"] > 100:
            suggestions.append({
                "category": "Structure",
                "issue": "Some paragraphs are too long",
                "suggestion": "Break down paragraphs longer than 100 words for better readability and mobile optimization"
            })
        
        # Accessibility improvements
        if analysis["accessibility"]["coverage_score"] < 7:
            missing = ", ".join(analysis["accessibility"]["missing_terms"][:3])
            suggestions.append({
                "category": "Accessibility Coverage",
                "issue": "Missing key accessibility terms",
                "suggestion": f"Add coverage of: {missing} to improve topical authority and E-E-A-T signals"
            })
        
        # Empathy improvements
        if analysis["empathy"]["needs_improvement"]:
            suggestions.append({
                "category": "Empathy",
                "issue": "Could use more empathetic language",
                "suggestion": "Add more phrases that acknowledge user challenges and needs to increase engagement and dwell time"
            })
        
        # Technical improvements
        if analysis["technical"]["score"] < 7:
            suggestions.append({
                "category": "Technical Accuracy",
                "issue": "Missing some technical requirements",
                "suggestion": "Ensure all key standards (WCAG, ADA, Section 508) are mentioned with versions to establish expertise and authority"
            })
        
        # Flow improvements
        if analysis["flow"]["needs_improvement"]:
            suggestions.append({
                "category": "Content Flow",
                "issue": "Limited use of transition words",
                "suggestion": "Add more transition words between paragraphs to improve readability and reduce bounce rate"
            })
        
        # SEO improvements
        if "seo" in analysis and analysis["seo"]["needs_improvement"]:
            missing_elements = [
                element for element, data in analysis["seo"]["seo_elements"].items()
                if not data["present"]
            ]
            
            if missing_elements:
                missing_str = ", ".join(missing_elements[:3])
                suggestions.append({
                    "category": "SEO Optimization",
                    "issue": "Missing key SEO elements",
                    "suggestion": f"Add {missing_str} to improve search engine visibility and SERP ranking potential"
                })
            
            if analysis["seo"].get("keyword_stuffing", False):
                suggestions.append({
                    "category": "Keyword Density",
                    "issue": "Potential keyword stuffing detected",
                    "suggestion": "Reduce keyword density to below 3% and focus on natural language optimization for semantic search"
                })
        
        # Long-tail keyword improvements
        if "long_tail" in analysis and analysis["long_tail"]["needs_improvement"]:
            suggestions.append({
                "category": "Long-Tail Keywords",
                "issue": "Limited use of long-tail keywords",
                "suggestion": "Incorporate more specific, niche long-tail keywords (3+ words) to target qualified traffic and capture featured snippets"
            })
            
            # Suggest specific long-tail keywords if available
            if "ngram_candidates" in analysis["long_tail"] and analysis["long_tail"]["ngram_candidates"]:
                top_ngrams = [item["phrase"] for item in analysis["long_tail"]["ngram_candidates"][:3]]
                if top_ngrams:
                    suggestions.append({
                        "category": "Specific Long-Tail Opportunities",
                        "issue": "Missed opportunities for specific keyword phrases",
                        "suggestion": f"Consider expanding on these phrases: {', '.join(top_ngrams)}"
                    })
        
        # Engagement improvements
        if "engagement" in analysis and analysis["engagement"]["needs_improvement"]:
            weak_elements = [
                element for element, data in analysis["engagement"]["engagement_elements"].items()
                if data["count"] < 2
            ]
            
            if weak_elements:
                weak_str = ", ".join(weak_elements[:3])
                suggestions.append({
                    "category": "User Engagement",
                    "issue": f"Low usage of engagement elements: {weak_str}",
                    "suggestion": "Add more questions, calls-to-action, and emotional language to increase user engagement and reduce bounce rate"
                })
        
        return suggestions

    def analyze_seo_optimization(self, content: str) -> Dict[str, Any]:
        """Analyze SEO optimization of the content."""
        content_lower = content.lower()
        
        # Check for SEO patterns
        seo_elements = {}
        for element, pattern in self.seo_patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            seo_elements[element] = {
                "present": len(matches) > 0,
                "count": len(matches),
                "examples": matches[:3] if matches else []
            }
        
        # Extract potential keywords from content
        words = re.findall(r'\b[a-z][a-z-]{2,}\b', content_lower)
        filtered_words = [w for w in words if w not in self.stop_words]
        
        # Count word frequencies
        word_counts = Counter(filtered_words)
        top_keywords = word_counts.most_common(10)
        
        # Calculate keyword density for top keywords
        total_words = len(filtered_words)
        keyword_density = {
            word: (count / total_words) * 100 if total_words > 0 else 0
            for word, count in top_keywords
        }
        
        # Check for keyword stuffing (density > 5%)
        keyword_stuffing = any(density > 5.0 for density in keyword_density.values())
        
        # Calculate overall SEO score
        seo_score = sum(1 for element in seo_elements.values() if element["present"])
        seo_score = (seo_score / len(self.seo_patterns)) * 10
        
        # Adjust score based on keyword stuffing
        if keyword_stuffing:
            seo_score = max(0, seo_score - 2)
        
        return {
            "seo_elements": seo_elements,
            "top_keywords": [{"keyword": k, "count": c, "density": keyword_density[k]} for k, c in top_keywords],
            "keyword_stuffing": keyword_stuffing,
            "seo_score": seo_score,
            "needs_improvement": seo_score < 7
        }
    
    def analyze_long_tail_keywords(self, content: str) -> Dict[str, Any]:
        """Analyze long-tail keyword usage in content."""
        content_lower = content.lower()
        
        # Find long-tail keyword matches
        long_tail_matches = []
        for pattern in self.long_tail_patterns:
            matches = re.finditer(pattern, content_lower)
            long_tail_matches.extend([m.group(0) for m in matches])
        
        # Extract n-grams (3-5 word phrases) as potential long-tail keywords
        sentences = nltk.sent_tokenize(content_lower)
        ngram_candidates = []
        
        for sentence in sentences:
            # Clean and tokenize
            clean_sentence = re.sub(r'[^\w\s]', '', sentence)
            tokens = nltk.word_tokenize(clean_sentence)
            filtered_tokens = [token for token in tokens if token not in self.stop_words]
            
            # Generate n-grams
            for n in range(3, 6):  # 3, 4, and 5-grams
                if len(filtered_tokens) >= n:
                    for i in range(len(filtered_tokens) - n + 1):
                        ngram = ' '.join(filtered_tokens[i:i+n])
                        if len(ngram) > 10:  # Minimum length to be considered
                            ngram_candidates.append(ngram)
        
        # Count frequency of n-grams
        ngram_counter = Counter(ngram_candidates)
        top_ngrams = ngram_counter.most_common(10)
        
        # Calculate long-tail keyword score
        long_tail_count = len(long_tail_matches) + len(top_ngrams)
        long_tail_score = min(10, long_tail_count)
        
        return {
            "long_tail_matches": long_tail_matches[:10],  # Limit to top 10
            "ngram_candidates": [{"phrase": k, "count": c} for k, c in top_ngrams],
            "long_tail_count": long_tail_count,
            "long_tail_score": long_tail_score,
            "needs_improvement": long_tail_score < 5
        }
    
    def analyze_engagement(self, content: str) -> Dict[str, Any]:
        """Analyze user engagement factors in content."""
        # Check for engagement patterns
        engagement_elements = {}
        for element, pattern in self.engagement_patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            engagement_elements[element] = {
                "present": len(matches) > 0,
                "count": len(matches),
                "examples": matches[:3] if matches else []
            }
        
        # Calculate engagement score
        engagement_score = sum(element["count"] for element in engagement_elements.values())
        normalized_score = min(10, engagement_score / 5)  # Normalize to 0-10 scale
        
        return {
            "engagement_elements": engagement_elements,
            "engagement_score": normalized_score,
            "needs_improvement": normalized_score < 6
        }
    
    def analyze_blog(self, content: str) -> Dict[str, Any]:
        """Perform comprehensive blog analysis including SEO and long-tail keywords."""
        analysis = {
            "structure": self.analyze_structure(content),
            "accessibility": self.analyze_accessibility(content),
            "empathy": self.analyze_empathy(content),
            "technical": self.analyze_technical(content),
            "flow": self.analyze_flow(content),
            "seo": self.analyze_seo_optimization(content),
            "long_tail": self.analyze_long_tail_keywords(content),
            "engagement": self.analyze_engagement(content),
            "timestamp": datetime.now().isoformat()
        }
        
        # Calculate overall score with new metrics
        scores = [
            analysis["accessibility"]["coverage_score"],
            analysis["empathy"]["empathy_score"],
            analysis["technical"]["score"],
            analysis["flow"]["flow_score"],
            analysis["seo"]["seo_score"],
            analysis["long_tail"]["long_tail_score"],
            analysis["engagement"]["engagement_score"]
        ]
        analysis["overall_score"] = sum(scores) / len(scores)
        
        # Generate improvements
        analysis["improvements"] = self.generate_improvements(analysis)
        
        return analysis

def generate_report(analysis: Dict[str, Any]) -> str:
    """Generate a comprehensive human-readable report with SEO insights."""
    report = []
    
    # Overall score
    report.append("# Blog Post Analysis Report\n")
    report.append(f"## Overall Score: {analysis['overall_score']:.1f}/10\n")
    report.append(f"*Analysis timestamp: {analysis.get('timestamp', datetime.now().isoformat())}*\n")
    
    # Structure
    report.append("## Structure Analysis")
    struct = analysis["structure"]
    report.append(f"- Paragraphs: {struct['paragraphs']['count']}")
    report.append(f"- Average paragraph length: {struct['paragraphs']['avg_length']:.1f} words")
    report.append(f"- Sentences: {struct['sentences']['count']}")
    report.append(f"- Mobile readability: {'Good' if struct['paragraphs']['avg_length'] < 75 else 'Needs improvement'}\n")
    
    # Accessibility
    report.append("## Accessibility Coverage")
    access = analysis["accessibility"]
    report.append(f"- Coverage Score: {access['coverage_score']:.1f}/10")
    report.append(f"- Terms covered: {access['terms_covered']}/{len(access['covered_terms'] or {}) + len(access['missing_terms'] or [])}")
    if access["missing_terms"]:
        report.append("- Missing Terms:")
        for term in access["missing_terms"][:3]:
            report.append(f"  * {term}")
    report.append("")
    
    # Empathy
    report.append("## Empathy Analysis")
    empathy = analysis["empathy"]
    report.append(f"- Empathy Score: {empathy['empathy_score']}/10")
    if empathy["empathy_examples"]:
        report.append("- Examples of empathetic language:")
        for example in empathy["empathy_examples"]:
            report.append(f"  * {example}")
    report.append("")
    
    # Technical
    report.append("## Technical Analysis")
    tech = analysis["technical"]
    report.append(f"- Technical Score: {tech['score']:.1f}/10")
    report.append("- Requirements Met:")
    for req, met in tech["requirements_met"].items():
        report.append(f"  * {req}: {'✓' if met else '✗'}")
    report.append("")
    
    # Flow
    report.append("## Content Flow")
    flow = analysis["flow"]
    report.append(f"- Flow Score: {flow['flow_score']}/10")
    report.append(f"- Transition words used: {flow['transition_count']}")
    report.append("")
    
    # SEO Analysis (if available)
    if "seo" in analysis:
        seo = analysis["seo"]
        report.append("## SEO Optimization")
        report.append(f"- SEO Score: {seo['seo_score']:.1f}/10")
        report.append("- SEO Elements:")
        for element, data in seo["seo_elements"].items():
            report.append(f"  * {element}: {'✓' if data['present'] else '✗'}")
        
        report.append("\n- Top Keywords (with density):")
        for kw in seo["top_keywords"][:5]:
            report.append(f"  * {kw['keyword']}: {kw['count']} occurrences ({kw['density']:.2f}%)")
        
        if seo.get("keyword_stuffing"):
            report.append("\n⚠️ **Warning**: Potential keyword stuffing detected. Consider reducing keyword density.")
        report.append("")
    
    # Long-tail Keyword Analysis (if available)
    if "long_tail" in analysis:
        lt = analysis["long_tail"]
        report.append("## Long-Tail Keyword Analysis")
        report.append(f"- Long-Tail Score: {lt['long_tail_score']}/10")
        
        if lt["long_tail_matches"]:
            report.append("- Detected Long-Tail Phrases:")
            for phrase in lt["long_tail_matches"][:5]:
                report.append(f"  * {phrase}")
        
        if lt["ngram_candidates"]:
            report.append("\n- Potential Long-Tail Opportunities:")
            for ngram in lt["ngram_candidates"][:5]:
                report.append(f"  * {ngram['phrase']} ({ngram['count']} occurrences)")
        report.append("")
    
    # Engagement Analysis (if available)
    if "engagement" in analysis:
        eng = analysis["engagement"]
        report.append("## User Engagement Factors")
        report.append(f"- Engagement Score: {eng['engagement_score']:.1f}/10")
        report.append("- Engagement Elements:")
        for element, data in eng["engagement_elements"].items():
            report.append(f"  * {element}: {data['count']} occurrences")
        report.append("")
    
    # Improvements
    report.append("## Suggested Improvements")
    for imp in analysis["improvements"]:
        report.append(f"### {imp['category']}")
        report.append(f"**Issue**: {imp['issue']}")
        report.append(f"**Suggestion**: {imp['suggestion']}\n")
    
    return "\n".join(report)

def analyze_and_save(content: str, output_dir: str = "analysis") -> str:
    """Analyze blog and save results."""
    analyzer = BlogAnalyzer()
    analysis = analyzer.analyze_blog(content)
    report = generate_report(analysis)
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Save analysis
    analysis_file = output_path / "blog_analysis.json"
    with open(analysis_file, "w") as f:
        json.dump(analysis, f, indent=2)
    
    # Save report
    report_file = output_path / "blog_analysis_report.md"
    with open(report_file, "w") as f:
        f.write(report)
    
    return str(report_file)
