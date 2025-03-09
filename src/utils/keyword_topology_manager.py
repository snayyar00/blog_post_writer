"""
Keyword Topology Manager for organizing and cycling through all keywords 
from context folder to ensure complete coverage for SEO.
"""

import json
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple
import datetime
import networkx as nx
from collections import defaultdict, Counter
import random
import os
from openai import AsyncOpenAI
from src.utils.context_keyword_manager import load_context_files, extract_keywords_from_context
from src.utils.logging_manager import log_info, log_debug, log_warning, log_error

class KeywordTopology:
    """
    Manages SEO keyword relationships and ensures systematic coverage 
    of all keywords extracted from context folder.
    """
    
    def __init__(self, 
                context_dir: Path = Path("./context"), 
                data_dir: Path = Path("./data"),
                cooldown_days: int = 30):
        """
        Initialize the keyword topology manager.
        
        Args:
            context_dir: Directory containing context files
            data_dir: Directory for storing keyword data
            cooldown_days: Days before a keyword can be reused
        """
        self.context_dir = context_dir
        self.data_dir = data_dir
        self.cooldown_days = cooldown_days
        self.topology_file = data_dir / "keyword_topology.json"
        self.usage_file = data_dir / "keyword_usage.json"
        
        # Create directories if they don't exist
        self.data_dir.mkdir(exist_ok=True, parents=True)
        
        # Load existing data
        self.topology = self._load_topology()
        self.usage_history = self._load_usage_history()
        
        # Create graph of keyword relationships
        self.graph = self._build_keyword_graph()
        
        # OpenAI client for keyword relationship analysis
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        log_info("Keyword topology manager initialized", "KEYWORD")
    
    def _load_topology(self) -> Dict[str, Any]:
        """Load keyword topology from file."""
        try:
            if self.topology_file.exists():
                with open(self.topology_file, "r") as f:
                    return json.load(f)
            else:
                log_info("No existing keyword topology found, creating new", "KEYWORD")
        except Exception as e:
            log_warning(f"Error loading keyword topology: {e}", "KEYWORD")
        
        return {
            "version": 1,
            "last_updated": datetime.datetime.now().isoformat(),
            "keywords": {},
            "clusters": {},
            "relationships": []
        }
    
    def _save_topology(self) -> None:
        """Save keyword topology to file."""
        try:
            # Update timestamp
            self.topology["last_updated"] = datetime.datetime.now().isoformat()
            
            with open(self.topology_file, "w") as f:
                json.dump(self.topology, f, indent=2)
            log_debug("Keyword topology saved successfully", "KEYWORD")
        except Exception as e:
            log_error(f"Error saving keyword topology: {e}", "KEYWORD")
    
    def _load_usage_history(self) -> Dict[str, List[str]]:
        """Load keyword usage history."""
        try:
            if self.usage_file.exists():
                with open(self.usage_file, "r") as f:
                    return json.load(f)
            else:
                log_info("No existing keyword usage history found, creating new", "KEYWORD")
        except Exception as e:
            log_warning(f"Error loading keyword usage history: {e}", "KEYWORD")
        
        return {}
    
    def _save_usage_history(self) -> None:
        """Save keyword usage history."""
        try:
            with open(self.usage_file, "w") as f:
                json.dump(self.usage_history, f, indent=2)
            log_debug("Keyword usage history saved successfully", "KEYWORD")
        except Exception as e:
            log_error(f"Error saving keyword usage history: {e}", "KEYWORD")
    
    def _build_keyword_graph(self) -> nx.Graph:
        """Build a graph of keyword relationships."""
        graph = nx.Graph()
        
        # Add all keywords as nodes
        for keyword in self.topology.get("keywords", {}):
            graph.add_node(keyword)
        
        # Add relationships as edges
        for rel in self.topology.get("relationships", []):
            if len(rel) >= 2:
                graph.add_edge(rel[0], rel[1], weight=rel.get("weight", 1.0))
        
        return graph
    
    async def update_topology(self) -> None:
        """
        Update the keyword topology by extracting keywords from context folder
        and analyzing their relationships.
        """
        # Load context files
        context_data = load_context_files(self.context_dir)
        if not context_data:
            log_warning("No context files found, cannot update topology", "KEYWORD")
            return
        
        # Extract keywords from context
        extracted_keywords = extract_keywords_from_context(context_data)
        
        # If no keywords extracted, nothing to update
        if not extracted_keywords:
            log_warning("No keywords extracted from context, cannot update topology", "KEYWORD")
            return
        
        # Process each extracted keyword
        keyword_list = []
        for kw_data in extracted_keywords:
            keyword = kw_data["keyword"]
            keyword_list.append(keyword)
            
            # Update or add keyword in topology
            if keyword not in self.topology["keywords"]:
                self.topology["keywords"][keyword] = {
                    "priority": kw_data["priority"],
                    "source": kw_data["source"],
                    "frequency": kw_data["frequency"],
                    "added_date": datetime.datetime.now().isoformat()
                }
            else:
                # Update existing keyword data
                self.topology["keywords"][keyword]["priority"] = kw_data["priority"]
                self.topology["keywords"][keyword]["frequency"] = kw_data["frequency"]
                # Keep source and added_date as they were
        
        # Find new keywords not yet in the graph
        existing_keywords = set(self.graph.nodes())
        new_keywords = set(keyword_list) - existing_keywords
        
        if new_keywords:
            # Analyze relationships for new keywords
            await self._analyze_keyword_relationships(list(new_keywords), keyword_list)
        
        # Rebuild the graph with updated relationships
        self.graph = self._build_keyword_graph()
        
        # Update clusters
        self._update_clusters()
        
        # Save changes
        self._save_topology()
        log_info(f"Updated keyword topology with {len(new_keywords)} new keywords", "KEYWORD")
    
    async def _analyze_keyword_relationships(self, new_keywords: List[str], all_keywords: List[str]) -> None:
        """
        Analyze relationships between new keywords and existing keywords.
        
        Args:
            new_keywords: List of new keywords to analyze
            all_keywords: List of all keywords for context
        """
        # Skip if no new keywords
        if not new_keywords:
            return
            
        try:
            # Prepare prompt for OpenAI
            prompt = f"""Analyze these new SEO keywords and their relationships to existing keywords:

New keywords: {', '.join(new_keywords)}

Existing keywords: {', '.join(all_keywords[:50])}  # Limit to first 50 for token limits

For each new keyword, identify the 2-3 most closely related existing keywords based on:
1. Semantic relevance
2. Search intent overlap
3. Topical hierarchy (parent/child relationships)

Return a JSON array where each object contains:
- "keyword": The new keyword
- "related": Array of 2-3 related keywords from the existing list
- "relationship_type": A label like "parent", "child", "sibling", or "related"
- "weight": A number from 0.1 to 1.0 indicating relationship strength (1.0 = strongest)

Example:
[
  {{
    "keyword": "WCAG 2.1",
    "related": ["Web Accessibility", "WCAG Compliance"],
    "relationship_type": "child",
    "weight": 0.9
  }}
]
"""
            
            # Get OpenAI's analysis
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            # Parse response
            try:
                result = json.loads(response.choices[0].message.content)
                relationships = result.get("relationships", [])
                if not relationships and isinstance(result, list):
                    relationships = result  # Handle if result is directly the array
                
                # Add new relationships to topology
                existing_relationships = {(r[0], r[1]) for r in self.topology["relationships"]}
                
                for rel_data in relationships:
                    keyword = rel_data.get("keyword")
                    related_keywords = rel_data.get("related", [])
                    weight = float(rel_data.get("weight", 0.5))
                    
                    for related in related_keywords:
                        # Skip if both keywords don't exist in our topology
                        if keyword not in self.topology["keywords"] or related not in self.topology["keywords"]:
                            continue
                            
                        # Skip if relationship already exists
                        if (keyword, related) in existing_relationships or (related, keyword) in existing_relationships:
                            continue
                            
                        # Add new relationship
                        self.topology["relationships"].append({
                            "source": keyword,
                            "target": related,
                            "type": rel_data.get("relationship_type", "related"),
                            "weight": weight
                        })
                        
                        # Add edge to graph
                        self.graph.add_edge(keyword, related, weight=weight)
                
                log_info(f"Analyzed relationships for {len(new_keywords)} keywords", "KEYWORD")
                
            except json.JSONDecodeError:
                log_error("Failed to parse OpenAI response as JSON", "KEYWORD")
                
        except Exception as e:
            log_error(f"Error analyzing keyword relationships: {e}", "KEYWORD")
    
    def _update_clusters(self) -> None:
        """Update keyword clusters in the topology."""
        try:
            # Use community detection to find clusters
            import community as community_louvain
            
            # Find communities
            communities = community_louvain.best_partition(self.graph)
            
            # Group keywords by community
            clusters = defaultdict(list)
            for node, community_id in communities.items():
                clusters[str(community_id)].append(node)
            
            # Find central keywords for each cluster
            cluster_data = {}
            for cluster_id, keywords in clusters.items():
                # Find the highest degree keyword as the central one
                central_keyword = max(keywords, key=lambda k: self.graph.degree(k))
                
                # Calculate cluster metrics
                keyword_priorities = [self.topology["keywords"].get(k, {}).get("priority", "medium") for k in keywords]
                priority_scores = {"critical": 3, "high": 2, "medium": 1, "low": 0}
                avg_priority = sum(priority_scores.get(p, 0) for p in keyword_priorities) / len(keywords) if keywords else 0
                
                cluster_data[cluster_id] = {
                    "keywords": keywords,
                    "central_keyword": central_keyword,
                    "size": len(keywords),
                    "average_priority": avg_priority
                }
            
            # Update topology
            self.topology["clusters"] = cluster_data
            log_info(f"Updated keyword clusters: found {len(cluster_data)} clusters", "KEYWORD")
            
        except ImportError:
            log_warning("python-louvain package not installed, skipping cluster update", "KEYWORD")
        except Exception as e:
            log_error(f"Error updating keyword clusters: {e}", "KEYWORD")
    
    def record_keyword_use(self, keyword: str) -> None:
        """
        Record the use of a keyword.
        
        Args:
            keyword: The keyword that was used
        """
        timestamp = datetime.datetime.now().isoformat()
        
        if keyword not in self.usage_history:
            self.usage_history[keyword] = []
        
        self.usage_history[keyword].append(timestamp)
        self._save_usage_history()
        log_info(f"Recorded use of keyword: {keyword}", "KEYWORD")
    
    def get_next_keyword(self) -> str:
        """
        Get the next keyword to use based on topology coverage and content diversity.
        
        Returns:
            str: The next keyword to use
        """
        try:
            # Get all available keywords
            all_keywords = list(self.topology["keywords"].keys())
            if not all_keywords:
                log_warning("No keywords in topology, using default", "KEYWORD")
                return "Web Accessibility"
            
            # Get keywords that haven't been used or are past cooldown
            now = datetime.datetime.now()
            cooldown_period = datetime.timedelta(days=self.cooldown_days)
            
            # Track keyword types to ensure diversity
            keyword_types = {
                "overview": ["guide", "introduction", "basics", "101"],
                "technical": ["implementation", "code", "development", "testing"],
                "compliance": ["wcag", "ada", "section 508", "standards"],
                "specific": ["screen readers", "keyboard navigation", "color contrast"],
                "industry": ["healthcare", "education", "finance", "e-commerce"],
                "impact": ["benefits", "roi", "case studies", "statistics"]
            }
            
            # Get recent keyword types
            recent_types = set()
            if self.usage_history:
                recent_keywords = []
                for kw, timestamps in self.usage_history.items():
                    if timestamps:
                        last_used = datetime.datetime.fromisoformat(max(timestamps))
                        if now - last_used < datetime.timedelta(days=14):  # Last 2 weeks
                            recent_keywords.append(kw.lower())
                
                # Identify types of recent keywords
                for kw in recent_keywords:
                    for type_name, patterns in keyword_types.items():
                        if any(pattern in kw.lower() for pattern in patterns):
                            recent_types.add(type_name)
            
            # Get available keywords
            available_keywords = []
            for kw in all_keywords:
                # Skip if recently used
                if kw in self.usage_history and self.usage_history[kw]:
                    last_used = datetime.datetime.fromisoformat(max(self.usage_history[kw]))
                    if now - last_used <= cooldown_period:
                        continue
                    
                # Skip if similar to recent content
                kw_lower = kw.lower()
                skip = False
                for type_name, patterns in keyword_types.items():
                    if type_name in recent_types and any(pattern in kw_lower for pattern in patterns):
                        skip = True
                        break
                if skip:
                    continue
                
                available_keywords.append(kw)
            
            # If no available keywords after filtering, relax constraints
            if not available_keywords:
                log_warning("No diverse keywords available, using least recently used", "KEYWORD")
                last_used_dates = {}
                for kw, timestamps in self.usage_history.items():
                    if timestamps:
                        last_used_dates[kw] = datetime.datetime.fromisoformat(max(timestamps))
                
                if last_used_dates:
                    return min(last_used_dates.items(), key=lambda x: x[1])[0]
                return random.choice(all_keywords)
            
            # Find keywords from clusters with lowest coverage
            clusters_coverage = self._calculate_cluster_coverage()
            sorted_clusters = sorted(clusters_coverage.items(), key=lambda x: x[1]["coverage"])
            
            # Try to find an available keyword from the least covered cluster
            for cluster_id, data in sorted_clusters:
                cluster_keywords = self.topology["clusters"].get(cluster_id, {}).get("keywords", [])
                available_in_cluster = [kw for kw in cluster_keywords if kw in available_keywords]
                
                if available_in_cluster:
                    # Score keywords based on multiple factors
                    keyword_scores = []
                    for kw in available_in_cluster:
                        score = 0
                        kw_lower = kw.lower()
                        
                        # Prefer specific topics over general ones
                        if any(pattern in kw_lower for pattern in keyword_types["specific"]):
                            score += 3
                        elif any(pattern in kw_lower for pattern in keyword_types["technical"]):
                            score += 2
                        
                        # Consider keyword priority
                        priority = self.topology["keywords"].get(kw, {}).get("priority", "medium")
                        priority_score = {"critical": 3, "high": 2, "medium": 1, "low": 0}
                        score += priority_score.get(priority, 0)
                        
                        # Prefer keywords with relationships
                        relationships = self.get_keyword_relationships(kw)
                        score += min(len(relationships), 3)  # Cap at 3 points
                        
                        keyword_scores.append((kw, score))
                    
                    # Sort by score (highest first)
                    sorted_keywords = sorted(keyword_scores, key=lambda x: x[1], reverse=True)
                    selected = sorted_keywords[0][0]
                    
                    log_info(f"Selected diverse keyword '{selected}' from lowest coverage cluster", "KEYWORD")
                    return selected
            
            # If we get here, just use the first available keyword
            selected = available_keywords[0]
            log_info(f"Selected keyword '{selected}' as fallback", "KEYWORD")
            return selected
            
        except Exception as e:
            log_error(f"Error getting next keyword: {e}", "KEYWORD")
            return "Web Accessibility"  # Fallback to default keyword
    
    def _calculate_cluster_coverage(self) -> Dict[str, Dict[str, Any]]:
        """
        Calculate coverage metrics for each cluster.
        
        Returns:
            Dict mapping cluster IDs to coverage metrics
        """
        coverage = {}
        
        for cluster_id, cluster_data in self.topology.get("clusters", {}).items():
            keywords = cluster_data.get("keywords", [])
            if not keywords:
                continue
                
            used_count = 0
            for kw in keywords:
                if kw in self.usage_history and self.usage_history[kw]:
                    used_count += 1
            
            coverage_percent = used_count / len(keywords) if keywords else 0
            
            coverage[cluster_id] = {
                "total_keywords": len(keywords),
                "used_keywords": used_count,
                "coverage": coverage_percent
            }
        
        return coverage
    
    def get_keyword_relationships(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Get relationships for a specific keyword.
        
        Args:
            keyword: The keyword to get relationships for
            
        Returns:
            List of related keywords with relationship data
        """
        if not self.graph.has_node(keyword):
            return []
            
        neighbors = list(self.graph.neighbors(keyword))
        relationships = []
        
        for neighbor in neighbors:
            edge_data = self.graph.get_edge_data(keyword, neighbor)
            
            # Find relationship type from topology
            rel_type = "related"  # Default
            for rel in self.topology.get("relationships", []):
                if (rel.get("source") == keyword and rel.get("target") == neighbor) or \
                   (rel.get("source") == neighbor and rel.get("target") == keyword):
                    rel_type = rel.get("type", "related")
                    break
            
            relationships.append({
                "keyword": neighbor,
                "weight": edge_data.get("weight", 0.5),
                "type": rel_type,
                "priority": self.topology["keywords"].get(neighbor, {}).get("priority", "medium")
            })
        
        # Sort by weight (highest first)
        relationships.sort(key=lambda x: x["weight"], reverse=True)
        
        return relationships
    
    def get_coverage_report(self) -> Dict[str, Any]:
        """
        Generate a coverage report for all keywords.
        
        Returns:
            Dict containing coverage metrics
        """
        total_keywords = len(self.topology.get("keywords", {}))
        used_keywords = len(self.usage_history)
        unused_keywords = total_keywords - used_keywords
        
        # Calculate usage by priority
        priority_usage = defaultdict(lambda: {"total": 0, "used": 0})
        for kw, data in self.topology.get("keywords", {}).items():
            priority = data.get("priority", "medium")
            priority_usage[priority]["total"] += 1
            if kw in self.usage_history and self.usage_history[kw]:
                priority_usage[priority]["used"] += 1
        
        # Calculate coverage by cluster
        cluster_coverage = self._calculate_cluster_coverage()
        
        return {
            "total_keywords": total_keywords,
            "used_keywords": used_keywords,
            "unused_keywords": unused_keywords,
            "coverage_percent": (used_keywords / total_keywords) * 100 if total_keywords else 0,
            "priority_coverage": {k: v for k, v in priority_usage.items()},
            "cluster_coverage": cluster_coverage
        }
