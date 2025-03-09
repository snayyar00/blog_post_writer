"""
Test suite for enhanced keyword selection system.
"""

import pytest
from pathlib import Path
import json
from datetime import datetime, timedelta

@pytest.fixture
def test_data():
    """Set up test environment."""
    # Create test data directory
    test_data_dir = Path("test_data")
    test_data_dir.mkdir(exist_ok=True)
    
    # Create test keyword history
    history_file = test_data_dir / "test_keyword_history.json"
    test_history = {
        "Web Accessibility": [
            (datetime.now() - timedelta(days=5)).isoformat(),
            (datetime.now() - timedelta(days=10)).isoformat()
        ],
        "WCAG Compliance": [
            (datetime.now() - timedelta(days=3)).isoformat()
        ],
        "Screen Readers": [
            (datetime.now() - timedelta(days=1)).isoformat()
        ]
    }
    with open(history_file, "w") as f:
        json.dump(test_history, f)
        
    # Create test context files
    context_dir = test_data_dir / "context"
    context_dir.mkdir(exist_ok=True)
    
    # Create test SEO content file
    seo_content = """
    ### **High-Value Keywords**
    * **Web Accessibility**: Making websites accessible to all users
    * **WCAG Compliance**: Meeting web content accessibility guidelines
    * **ADA Requirements**: Americans with Disabilities Act standards
    * **Screen Readers**: Tools for visually impaired users
    * **Keyboard Navigation**: Accessing websites without a mouse
    """
    with open(context_dir / "SEO Content.md", "w") as f:
        f.write(seo_content)
        
    yield {
        "test_data_dir": test_data_dir,
        "context_dir": context_dir,
        "history_file": history_file
    }
    
    # Cleanup after tests
    import shutil
    if test_data_dir.exists():
        shutil.rmtree(test_data_dir)

@pytest.mark.asyncio
async def test_core_topic_rotation(test_data):
        """Test that core topics rotate correctly."""
        from src.utils.enhanced_keyword_selector import EnhancedKeywordSelector
        
        selector = EnhancedKeywordSelector(
            data_dir=test_data["test_data_dir"],
            context_dir=test_data["context_dir"]
        )
        
        # First selection should be a core topic since none used recently
        keyword = await selector.get_next_keyword()
        assert keyword in ["Web Accessibility", "WCAG Compliance", "ADA Requirements"]
        assert selector.is_core_topic(keyword)
        
        # Record use of all core topics to force variation selection
        for topic in ["Web Accessibility", "WCAG Compliance", "ADA Requirements"]:
            selector.record_keyword_use(topic)
        
        # After using all core topics, should get a variation
        next_keyword = await selector.get_next_keyword()
        assert next_keyword in ["Screen Readers", "Keyboard Navigation"]
    
def test_keyword_history(test_data):
        """Test keyword history tracking."""
        from src.utils.enhanced_keyword_selector import EnhancedKeywordSelector
        
        selector = EnhancedKeywordSelector(
            data_dir=test_data["test_data_dir"],
            context_dir=test_data["context_dir"]
        )
        
        # Use a keyword
        keyword = "Web Accessibility"
        selector.record_keyword_use(keyword)
        
        # Check it's in history
        history = selector.get_keyword_history(keyword)
        assert len(history) > 0
        assert isinstance(history[-1], str)  # Should be ISO format timestamp
    
@pytest.mark.asyncio
async def test_variation_generation(test_data):
        """Test generation of keyword variations."""
        from src.utils.enhanced_keyword_selector import EnhancedKeywordSelector
        
        selector = EnhancedKeywordSelector(
            data_dir=test_data["test_data_dir"],
            context_dir=test_data["context_dir"]
        )
        
        variations = await selector.get_keyword_variations("Web Accessibility")
        assert isinstance(variations, list)
        assert len(variations) > 0
        assert all(isinstance(v, str) for v in variations)
    
def test_core_topic_validation(test_data):
        """Test core topic validation."""
        from src.utils.enhanced_keyword_selector import EnhancedKeywordSelector
        
        selector = EnhancedKeywordSelector(
            data_dir=test_data["test_data_dir"],
            context_dir=test_data["context_dir"]
        )
        
        assert selector.is_core_topic("Web Accessibility")
        assert selector.is_core_topic("WCAG Compliance")
        assert not selector.is_core_topic("Random Topic")
    
@pytest.mark.asyncio
async def test_safe_fallback(test_data):
        """Test system falls back safely if something goes wrong."""
        from src.utils.enhanced_keyword_selector import EnhancedKeywordSelector
        
        selector = EnhancedKeywordSelector(
            data_dir=test_data["test_data_dir"],
            context_dir=test_data["context_dir"]
        )
        
        # Simulate error by using invalid directory
        selector.context_dir = Path("nonexistent")
        
        # Should still get a valid keyword
        keyword = await selector.get_next_keyword()
        assert isinstance(keyword, str)
        assert len(keyword) > 0
    
def test_keyword_metrics(test_data):
        """Test keyword metrics tracking."""
        from src.utils.enhanced_keyword_selector import EnhancedKeywordSelector
        
        selector = EnhancedKeywordSelector(
            data_dir=test_data["test_data_dir"],
            context_dir=test_data["context_dir"]
        )
        
        metrics = selector.get_keyword_metrics("Web Accessibility")
        assert isinstance(metrics, dict)
        assert "last_used" in metrics
        assert "use_count" in metrics
        assert "variations" in metrics
