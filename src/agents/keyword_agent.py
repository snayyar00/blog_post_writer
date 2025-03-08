"""Keyword topology agent that analyzes and generates related keywords."""

from typing import Dict, List, TypedDict, Any
from dataclasses import dataclass
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

@dataclass
class KeywordCluster:
    main_keyword: str
    related_keywords: List[str]
    search_volume: int
    difficulty: float
    intent: str

class KeywordMetrics(TypedDict):
    search_volume: int
    difficulty: float
    intent: str
    related_terms: List[str]

class KeywordTopologyAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4")
        self.parser = JsonOutputParser()
        
    async def analyze_keyword(self, keyword: str) -> KeywordCluster:
        """
        Analyze a keyword and generate related keywords and metrics.
        
        Args:
            keyword: The main keyword to analyze
            
        Returns:
            KeywordCluster containing related keywords and metrics
        """
        prompt = PromptTemplate.from_template("""
            Analyze this keyword and provide:
            1. Related keywords and variations
            2. Estimated search volume (1-100)
            3. Keyword difficulty (0.0-1.0)
            4. Search intent (informational/transactional/navigational)
            
            Keyword: {keyword}
            
            Format response as JSON with these keys:
            - related_keywords: list of strings
            - search_volume: integer
            - difficulty: float
            - intent: string
        """)
        
        chain = prompt | self.llm | self.parser
        
        try:
            result = await chain.ainvoke({"keyword": keyword})
            return KeywordCluster(
                main_keyword=keyword,
                related_keywords=result["related_keywords"],
                search_volume=result["search_volume"],
                difficulty=result["difficulty"],
                intent=result["intent"]
            )
        except Exception as e:
            print(f"Error analyzing keyword: {str(e)}")
            return KeywordCluster(
                main_keyword=keyword,
                related_keywords=[],
                search_volume=0,
                difficulty=0.0,
                intent="unknown"
            )
            
    async def generate_keyword_topology(self, main_keywords: str | List[str], depth: int = 2) -> Dict[str, List[KeywordCluster]]:
        """
        Generate a topology of related keywords organized by relevance levels.
        
        Args:
            main_keywords: The seed keyword or list of keywords
            depth: How many levels deep to analyze (1-3)
            
        Returns:
            Dictionary of keyword clusters organized by relevance level
        """
        topology: Dict[str, List[KeywordCluster]] = {
            "primary": [],
            "secondary": [],
            "tertiary": []
        }
        
        # Convert single keyword to list for consistent processing
        if isinstance(main_keywords, str):
            keywords_list = [main_keywords]
        else:
            keywords_list = main_keywords
            
        # Process each keyword in the list
        for keyword in keywords_list:
            # Analyze main keyword
            primary_cluster = await self.analyze_keyword(keyword)
            topology["primary"].append(primary_cluster)
            
            if depth > 1:
                # Analyze related keywords from primary cluster
                # Limit the number of secondary keywords to analyze based on the input size
                related_limit = max(1, 3 // len(keywords_list))  # Dynamically adjust based on input size
                for related_kw in primary_cluster.related_keywords[:related_limit]:
                    secondary_cluster = await self.analyze_keyword(related_kw)
                    topology["secondary"].append(secondary_cluster)
                
                if depth > 2:
                    # Analyze tertiary keywords
                    for tertiary_kw in secondary_cluster.related_keywords[:2]:
                        tertiary_cluster = await self.analyze_keyword(tertiary_kw)
                        topology["tertiary"].append(tertiary_cluster)
                        
        return topology
        
    def get_semantic_groups(self, clusters: List[KeywordCluster]) -> Dict[str, List[str]]:
        """Group keywords by semantic similarity."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.cluster import KMeans
        import numpy as np
        
        # Extract all keywords
        all_keywords = []
        for cluster in clusters:
            all_keywords.append(cluster.main_keyword)
            all_keywords.extend(cluster.related_keywords)
            
        # Create TF-IDF vectors
        vectorizer = TfidfVectorizer()
        X = vectorizer.fit_transform(all_keywords)
        
        # Cluster keywords
        n_clusters = min(5, len(all_keywords))
        kmeans = KMeans(n_clusters=n_clusters)
        kmeans.fit(X)
        
        # Group keywords by cluster
        groups: Dict[str, List[str]] = {}
        for i in range(n_clusters):
            mask = kmeans.labels_ == i
            keywords = np.array(all_keywords)[mask]
            groups[f"group_{i}"] = keywords.tolist()
            
        return groups
        
    def suggest_content_structure(self, topology: Dict[str, List[KeywordCluster]]) -> Dict:
        """Suggest content structure based on keyword topology."""
        prompt = PromptTemplate.from_template("""
            Based on this keyword topology, suggest a content structure that:
            1. Targets primary keywords in main sections
            2. Incorporates secondary keywords in subsections
            3. Uses tertiary keywords naturally in content
            4. Maintains topical relevance
            5. Follows SEO best practices
            
            Keyword topology:
            {topology}
            
            Format response as JSON with these keys:
            - main_sections: list of dictionaries with 'title' and 'subsections'
            - recommended_headings: list of strings
            - keyword_placement: dictionary of section:keyword mappings
        """)
        
        chain = prompt | self.llm | self.parser
        
        try:
            return chain.invoke({"topology": str(topology)})
        except Exception as e:
            print(f"Error suggesting content structure: {str(e)}")
            return {}


def generate_keywords(topic: str, context_data: Dict[str, str]) -> List[str]:
    """
    Generate keywords for a given topic using context data.
    
    Args:
        topic: The main topic to generate keywords for
        context_data: Dictionary of context data from files
        
    Returns:
        List of generated keywords
    """
    llm = ChatOpenAI(model="gpt-4")
    parser = JsonOutputParser()
    
    # Extract relevant context
    context_text = "\n\n".join(context_data.values())
    
    prompt = PromptTemplate.from_template("""
        Generate a list of SEO-optimized keywords related to this topic: {topic}
        
        Use the following context information to inform your keyword selection:
        {context}
        
        Generate 10-15 keywords that are:
        1. Highly relevant to the topic
        2. Have good search potential
        3. Range from short-tail to long-tail keywords
        4. Include question-based keywords where appropriate
        
        Format response as a JSON array of strings.
    """)
    
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({"topic": topic, "context": context_text[:2000]})
        return result if isinstance(result, list) else []
    except Exception as e:
        print(f"Error generating keywords: {str(e)}")
        # Fallback to basic keywords if parsing fails
        return [topic, f"{topic} best practices", f"{topic} guide", f"how to {topic}", f"what is {topic}"]
