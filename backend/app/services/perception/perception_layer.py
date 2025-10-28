"""Perception layer - handles context understanding and routing."""

import logging
from typing import Dict, Any, List
from app.services.embedding import get_embedding

logger = logging.getLogger(__name__)

class PerceptionLayer:
    """Perception layer for analyzing user queries and content."""
    
    def __init__(self, prompts: Dict[str, Any]):
        """Initialize perception layer with prompts."""
        self.prompts = prompts.get('perception', {})
        self.prompt_template = self.prompts.get('prompt', '')
    
    def analyze(self, query: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze query to understand intent, category, and extract keywords.
        
        Args:
            query: User's search query
            user_context: User preferences and context
            
        Returns:
            Dict with intent, category, keywords, relevance
        """
        if user_context is None:
            user_context = self._get_default_context()
        
        try:
            # Get embedding for semantic understanding
            embedding = get_embedding(query)
            
            # Determine intent
            intent = self._determine_intent(query)
            
            # Extract category
            category = self._extract_category(query, user_context)
            
            # Extract keywords
            keywords = self._extract_keywords(query)
            
            # Calculate relevance score (simplified for now)
            relevance_score = self._calculate_relevance(query, category, user_context)
            
            result = {
                'intent': intent,
                'category': category,
                'keywords': keywords,
                'relevance_score': relevance_score,
                'embedding': embedding,
                'query': query
            }
            
            logger.info(f"Perception analysis complete: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in perception analysis: {e}")
            return {
                'intent': 'unknown',
                'category': 'Others',
                'keywords': query.split(),
                'relevance_score': 0.5,
                'error': str(e)
            }
    
    def _get_default_context(self) -> Dict[str, Any]:
        """Get default user context."""
        return {
            'interests': 'general knowledge',
            'location': 'global',
            'favorite_topics': 'all topics',
            'taste_preferences': 'neutral'
        }
    
    def _determine_intent(self, query: str) -> str:
        """Determine user intent from query."""
        query_lower = query.lower()
        
        # Question words
        if any(word in query_lower for word in ['what', 'who', 'where', 'when', 'why', 'how']):
            if '?' in query:
                return 'question'
            else:
                return 'search'
        
        # Action verbs
        if any(word in query_lower for word in ['find', 'show', 'get', 'download', 'search']):
            return 'search'
        
        # Default
        return 'search'
    
    def _extract_category(self, query: str, user_context: Dict[str, Any]) -> str:
        """Extract category from query."""
        query_lower = query.lower()
        
        # Category keywords mapping
        category_keywords = {
            'Sports': ['sport', 'football', 'basketball', 'soccer', 'cricket', 'tennis', 'olympic', 'game'],
            'Politics': ['politic', 'government', 'election', 'president', 'senate', 'democracy', 'vote'],
            'Financial': ['finance', 'money', 'stock', 'investment', 'bank', 'economy', 'market', 'business'],
            'Health & Medical': ['health', 'medical', 'disease', 'doctor', 'hospital', 'medicine', 'treatment', 'wellness'],
            'Current Affairs': ['news', 'current', 'breaking', 'recent', 'today', 'happening'],
            'Technology': ['tech', 'computer', 'software', 'hardware', 'ai', 'machine learning', 'programming', 'code', 'app'],
            'Others': []
        }
        
        # Check each category
        for category, keywords in category_keywords.items():
            if category != 'Others':
                if any(keyword in query_lower for keyword in keywords):
                    return category
        
        return 'Others'
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from query."""
        # Simple keyword extraction (split by space and remove stop words)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = query.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        return keywords if keywords else query.split()
    
    def _calculate_relevance(self, query: str, category: str, user_context: Dict[str, Any]) -> float:
        """Calculate relevance score based on user preferences."""
        # Default relevance
        relevance = 0.7
        
        # Check if category matches user interests
        interests = user_context.get('favorite_topics', '').lower()
        if category.lower() in interests:
            relevance += 0.2
        
        # Check if query length suggests detailed search
        if len(query.split()) >= 3:
            relevance += 0.1
        
        return min(relevance, 1.0)
