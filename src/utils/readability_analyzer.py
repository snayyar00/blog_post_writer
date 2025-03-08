"""
Custom readability analysis module for blog content.
"""

import re
import math
from typing import Dict, List, Tuple

class Readability:
    """
    A class to analyze text readability using various metrics.
    """
    
    def __init__(self, text: str):
        """
        Initialize with text to analyze.
        
        Args:
            text: The text to analyze
        """
        self.text = text
        self._process_text()
    
    def _process_text(self) -> None:
        """Process text to extract sentences, words, and syllables."""
        # Clean the text
        cleaned_text = re.sub(r'[^a-zA-Z0-9\s\.\!\?]', '', self.text)
        
        # Extract sentences
        self.sentences = re.split(r'[.!?]+', cleaned_text)
        self.sentences = [s.strip() for s in self.sentences if s.strip()]
        
        # Extract words
        self.words = re.findall(r'\b[a-zA-Z]+\b', cleaned_text.lower())
        
        # Count syllables
        self.syllable_count = self._count_syllables()
        
        # Calculate averages
        self.avg_sentence_length = len(self.words) / len(self.sentences) if self.sentences else 0
        self.avg_syllables_per_word = self.syllable_count / len(self.words) if self.words else 0
        
        # Count complex words (words with 3+ syllables)
        self.complex_words = self._count_complex_words()
        
    def _count_syllables(self) -> int:
        """Count syllables in all words."""
        total_syllables = 0
        for word in self.words:
            total_syllables += self._count_syllables_in_word(word)
        return total_syllables
    
    def _count_syllables_in_word(self, word: str) -> int:
        """
        Count syllables in a word using a heuristic approach.
        
        Args:
            word: The word to count syllables for
            
        Returns:
            Number of syllables
        """
        # Lower case word
        word = word.lower()
        
        # Special cases
        if len(word) <= 3:
            return 1
            
        # Remove es, ed at the end
        word = re.sub(r'e$', '', word)
        word = re.sub(r'es$', '', word)
        word = re.sub(r'ed$', '', word)
        
        # Count vowel groups
        count = len(re.findall(r'[aeiouy]+', word))
        
        # Adjust count for special patterns
        if word.endswith('le') and len(word) > 2 and word[-3] not in 'aeiouy':
            count += 1
            
        # Ensure at least one syllable
        return max(1, count)
    
    def _count_complex_words(self) -> int:
        """Count words with 3 or more syllables."""
        count = 0
        for word in self.words:
            if self._count_syllables_in_word(word) >= 3:
                count += 1
        return count
    
    def flesch(self) -> float:
        """
        Calculate Flesch Reading Ease score.
        
        Returns:
            Flesch Reading Ease score (0-100, higher is easier to read)
        """
        if not self.sentences or not self.words:
            return 0
            
        score = 206.835 - (1.015 * self.avg_sentence_length) - (84.6 * self.avg_syllables_per_word)
        return max(0, min(100, score))
    
    def flesch_kincaid(self) -> float:
        """
        Calculate Flesch-Kincaid Grade Level.
        
        Returns:
            Grade level (higher means more difficult)
        """
        if not self.sentences or not self.words:
            return 0
            
        score = 0.39 * self.avg_sentence_length + 11.8 * self.avg_syllables_per_word - 15.59
        return max(0, score)
    
    def gunning_fog(self) -> float:
        """
        Calculate Gunning Fog Index.
        
        Returns:
            Gunning Fog Index (years of education needed to understand)
        """
        if not self.sentences or not self.words:
            return 0
            
        complex_word_percentage = (self.complex_words / len(self.words)) * 100 if self.words else 0
        score = 0.4 * (self.avg_sentence_length + complex_word_percentage / 100)
        return max(0, score)
    
    def smog(self) -> float:
        """
        Calculate SMOG Index.
        
        Returns:
            SMOG Index (years of education needed to understand)
        """
        if not self.sentences or not self.words:
            return 0
            
        if len(self.sentences) < 30:
            # SMOG is designed for 30+ sentences, so we'll approximate
            score = 1.043 * math.sqrt(self.complex_words * (30 / len(self.sentences))) + 3.1291
        else:
            score = 1.043 * math.sqrt(self.complex_words) + 3.1291
            
        return max(0, score)
    
    def dale_chall(self) -> float:
        """
        Calculate Dale-Chall Readability Score.
        
        Returns:
            Dale-Chall score (lower is easier to read)
        """
        # Simplified version without the Dale-Chall word list
        # Instead, we'll use word length as a proxy for difficulty
        difficult_words = sum(1 for word in self.words if len(word) > 6)
        percent_difficult = (difficult_words / len(self.words)) * 100 if self.words else 0
        
        score = 0.1579 * percent_difficult + 0.0496 * self.avg_sentence_length
        
        # Adjust if percentage of difficult words is greater than 5%
        if percent_difficult > 5:
            score += 3.6365
            
        return max(0, score)
    
    def analyze(self) -> Dict[str, float]:
        """
        Perform comprehensive readability analysis.
        
        Returns:
            Dictionary with all readability metrics
        """
        return {
            "flesch_reading_ease": self.flesch(),
            "flesch_kincaid_grade": self.flesch_kincaid(),
            "gunning_fog": self.gunning_fog(),
            "smog": self.smog(),
            "dale_chall": self.dale_chall(),
            "avg_sentence_length": self.avg_sentence_length,
            "avg_syllables_per_word": self.avg_syllables_per_word,
            "complex_word_percentage": (self.complex_words / len(self.words) * 100) if self.words else 0
        }

def calculate_readability_metrics(text: str) -> Dict[str, float]:
    """
    Calculate readability metrics for the given text.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dictionary with readability metrics
    """
    r = Readability(text)
    return r.analyze()
