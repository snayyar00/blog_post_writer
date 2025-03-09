"""
Manager for blog ideas loaded from CSV file, providing additional context
and inspiration for content generation.
"""

import csv
import pandas as pd
from typing import Dict, List, Optional, Any
from pathlib import Path
from src.utils.logging_manager import log_info, log_debug, log_warning, log_error

class BlogIdeasManager:
    """Manages blog ideas and provides relevant context for content generation."""
    
    def __init__(self, ideas_file: str = "ideas.csv"):
        """
        Initialize the blog ideas manager.
        
        Args:
            ideas_file: Path to the CSV file containing blog ideas
        """
        self.ideas_file = ideas_file
        self.ideas_data = self._load_ideas()
        
    def _load_ideas(self) -> pd.DataFrame:
        """Load ideas from CSV file into a pandas DataFrame."""
        try:
            # Read CSV file
            df = pd.read_csv(self.ideas_file)
            
            # Clean up data
            df = df.fillna("")  # Replace NaN with empty string
            
            log_info(f"Loaded {len(df)} blog ideas from {self.ideas_file}", "IDEAS")
            return df
            
        except Exception as e:
            log_error(f"Error loading blog ideas: {str(e)}", "IDEAS")
            return pd.DataFrame()  # Return empty DataFrame on error
    
    def get_related_ideas(self, keyword: str) -> Dict[str, Any]:
        """
        Get ideas related to a specific keyword.
        
        Args:
            keyword: The keyword to find related ideas for
            
        Returns:
            Dictionary containing related ideas and their details
        """
        try:
            # Convert keyword to lowercase for case-insensitive matching
            keyword_lower = keyword.lower()
            
            # Search in Keywords and Research Topics columns
            related_ideas = self.ideas_data[
                self.ideas_data['Keywords'].str.lower().str.contains(keyword_lower, na=False) |
                self.ideas_data['Research Topics'].str.lower().str.contains(keyword_lower, na=False)
            ]
            
            if len(related_ideas) == 0:
                log_debug(f"No related ideas found for keyword: {keyword}", "IDEAS")
                return {
                    "related_titles": [],
                    "research_topics": [],
                    "cool_facts": [],
                    "word_counts": []
                }
            
            # Format results
            result = {
                "related_titles": related_ideas['Blog Title'].tolist(),
                "research_topics": [
                    topics.split(", ")
                    for topics in related_ideas['Research Topics'].fillna("").tolist()
                    if topics
                ],
                "cool_facts": related_ideas['Cool Facts'].fillna("").tolist(),
                "word_counts": related_ideas['Word Count'].fillna("").tolist()
            }
            
            log_debug(f"Found {len(related_ideas)} related ideas for keyword: {keyword}", "IDEAS")
            return result
            
        except Exception as e:
            log_error(f"Error getting related ideas: {str(e)}", "IDEAS")
            return {
                "related_titles": [],
                "research_topics": [],
                "cool_facts": [],
                "word_counts": []
            }
    
    def get_content_suggestions(self, keyword: str) -> str:
        """
        Get formatted content suggestions based on related ideas.
        
        Args:
            keyword: The keyword to get suggestions for
            
        Returns:
            Formatted string with content suggestions
        """
        related = self.get_related_ideas(keyword)
        
        if not any(related.values()):
            return "No specific content suggestions found in ideas database."
        
        suggestions = ["CONTENT SUGGESTIONS FROM IDEAS DATABASE:"]
        
        # Add related titles
        if related["related_titles"]:
            suggestions.append("\nSimilar Blog Titles:")
            for title in related["related_titles"]:
                suggestions.append(f"- {title}")
        
        # Add research topics
        if related["research_topics"]:
            suggestions.append("\nSuggested Research Topics:")
            for topics in related["research_topics"]:
                if isinstance(topics, list):
                    for topic in topics:
                        suggestions.append(f"- {topic}")
                else:
                    suggestions.append(f"- {topics}")
        
        # Add cool facts
        if related["cool_facts"]:
            suggestions.append("\nInteresting Facts to Include:")
            for fact in related["cool_facts"]:
                if fact:  # Only add non-empty facts
                    suggestions.append(f"- {fact}")
        
        # Add word count guidance
        if related["word_counts"]:
            suggestions.append("\nRecommended Word Count Ranges:")
            for count in related["word_counts"]:
                if count:  # Only add non-empty counts
                    suggestions.append(f"- {count} words")
        
        return "\n".join(suggestions)
    
    def get_monthly_plan(self, month: str) -> List[Dict[str, Any]]:
        """
        Get content plan for a specific month.
        
        Args:
            month: Name of the month (e.g., "January")
            
        Returns:
            List of blog post ideas for the month
        """
        try:
            # Filter ideas for the specified month
            monthly_ideas = self.ideas_data[
                self.ideas_data['Month'].str.lower() == month.lower()
            ]
            
            # Convert to list of dictionaries
            plan = monthly_ideas.to_dict('records')
            
            log_debug(f"Found {len(plan)} ideas for month: {month}", "IDEAS")
            return plan
            
        except Exception as e:
            log_error(f"Error getting monthly plan: {str(e)}", "IDEAS")
            return []
    
    def get_topic_clusters(self) -> Dict[str, List[str]]:
        """
        Group blog ideas into topic clusters based on keywords.
        
        Returns:
            Dictionary mapping main topics to lists of related blog titles
        """
        try:
            clusters = {}
            
            # Extract all keywords
            for _, row in self.ideas_data.iterrows():
                if pd.notna(row['Keywords']):
                    keywords = [k.strip() for k in row['Keywords'].split(',')]
                    
                    # Use first keyword as main topic
                    main_topic = keywords[0] if keywords else None
                    if main_topic:
                        if main_topic not in clusters:
                            clusters[main_topic] = []
                        clusters[main_topic].append(row['Blog Title'])
            
            log_debug(f"Generated {len(clusters)} topic clusters", "IDEAS")
            return clusters
            
        except Exception as e:
            log_error(f"Error generating topic clusters: {str(e)}", "IDEAS")
            return {}
