"""Decision layer - determines what actions to take."""

import logging
from typing import Dict, Any, List
from app.services.gemini_chat import GeminiChat

logger = logging.getLogger(__name__)

class DecisionLayer:
    """Decision layer for action planning and content categorization."""
    
    def __init__(self, prompts: Dict[str, Any], gemini_chat: GeminiChat = None):
        """Initialize decision layer."""
        self.prompts = prompts.get('decision_making', {})
        self.gemini_chat = gemini_chat
        
        # Prompts
        self.categorization_prompt = self.prompts.get('categorization_prompt', '')
        self.scoring_prompt = self.prompts.get('scoring_prompt', '')
        self.filtering_prompt = self.prompts.get('filtering_prompt', '')
        self.action_selection_prompt = self.prompts.get('action_selection_prompt', '')
        
        logger.info("Decision layer initialized")
    
    def make_decision(self, query: str, perception: Dict[str, Any], memory: Dict[str, Any], 
                     user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make decisions about what actions to take.
        
        Args:
            query: User query
            perception: Perception results
            memory: Memory results
            user_context: User context
            
        Returns:
            Dict with action plan
        """
        try:
            # Determine what actions to take
            actions = self._select_actions(query, perception, memory, user_context)
            
            # Categorize if needed
            categorization = self._should_categorize(user_context)
            
            # Scoring configuration
            scoring_config = self._get_scoring_config(user_context)
            
            # Filtering rules
            filtering_rules = self._get_filtering_rules(user_context)
            
            result = {
                'actions': actions,
                'categorization': categorization,
                'scoring_config': scoring_config,
                'filtering_rules': filtering_rules,
                'priority': self._calculate_priority(actions, perception)
            }
            
            logger.info(f"Decision made: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in decision making: {e}")
            return {
                'actions': ['search'],
                'categorization': False,
                'scoring_config': {},
                'filtering_rules': {},
                'error': str(e)
            }
    
    def categorize_content(self, content: Dict[str, Any], user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Categorize content based on user preferences.
        
        Args:
            content: Content to categorize
            user_context: User preferences
            
        Returns:
            Dict with category and confidence
        """
        if user_context is None:
            user_context = {}
        
        try:
            # Simple category detection (can be enhanced with LLM)
            category = self._detect_category(content, user_context)
            
            return {
                'categories': [category],
                'confidence': 0.8,
                'primary_category': category
            }
            
        except Exception as e:
            logger.error(f"Error categorizing content: {e}")
            return {'categories': ['Others'], 'confidence': 0.5}
    
    def score_result(self, result: Dict[str, Any], query: str, user_context: Dict[str, Any]) -> float:
        """
        Score a search result based on relevance and user preferences.
        
        Args:
            result: Search result
            query: Original query
            user_context: User preferences
            
        Returns:
            Score (0-1)
        """
        try:
            # Base score from semantic search
            base_score = result.get('score', 0.5)
            
            # Adjust based on user preferences
            interests = user_context.get('favorite_topics', '')
            content = result.get('content', '').lower()
            
            # Boost score if matches interests
            if interests and any(topic.lower() in content for topic in interests.split(',')):
                base_score += 0.1
            
            # Penalize confidential sites if user wants to skip them
            if user_context.get('skip_confidential_sites', True):
                url = result.get('url', '')
                if self._is_confidential(url):
                    base_score *= 0.5
            
            return min(base_score, 1.0)
            
        except Exception as e:
            logger.error(f"Error scoring result: {e}")
            return result.get('score', 0.5)
    
    def _select_actions(self, query: str, perception: Dict[str, Any], memory: Dict[str, Any], 
                       user_context: Dict[str, Any]) -> List[str]:
        """Select actions based on intent and context."""
        intent = perception.get('intent', 'search')
        actions = []
        
        # Always add search action
        actions.append('search')
        
        # Add highlight action if enabled
        if user_context and user_context.get('highlight_search_terms', True):
            actions.append('highlight')
        
        # Add categorization action if enabled
        if user_context and user_context.get('categorize_results', False):
            actions.append('categorize')
        
        # Add favorite action for bookmarking
        actions.append('favorite_enabled')
        
        return actions
    
    def _should_categorize(self, user_context: Dict[str, Any]) -> bool:
        """Determine if results should be categorized."""
        return user_context and user_context.get('categorize_results', False)
    
    def _get_scoring_config(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get configuration for scoring results."""
        return {
            'boost_matching_categories': True,
            'penalize_confidential': user_context and user_context.get('skip_confidential_sites', True),
            'user_preferences_weight': 0.3
        }
    
    def _get_filtering_rules(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get filtering rules from user preferences."""
        return {
            'skip_confidential_sites': user_context and user_context.get('skip_confidential_sites', True),
            'categories': user_context and user_context.get('categories', []),
            'min_relevance_score': 0.3
        }
    
    def _calculate_priority(self, actions: List[str], perception: Dict[str, Any]) -> Dict[str, int]:
        """Calculate priority for each action."""
        priority_map = {}
        
        for i, action in enumerate(actions):
            if action == 'search':
                priority_map[action] = 1
            elif action == 'highlight':
                priority_map[action] = 2
            elif action == 'categorize':
                priority_map[action] = 3
            else:
                priority_map[action] = i + 1
        
        return priority_map
    
    def _detect_category(self, content: Dict[str, Any], user_context: Dict[str, Any]) -> str:
        """Detect category from content."""
        text = (content.get('title', '') + ' ' + content.get('content', '')).lower()
        url = content.get('url', '').lower()
        
        # Category keyword detection
        category_keywords = {
            'Sports': ['sport', 'football', 'basketball', 'soccer', 'cricket', 'tennis', 'game'],
            'Politics': ['politic', 'government', 'election', 'president', 'senate', 'vote'],
            'Financial': ['finance', 'money', 'stock', 'investment', 'bank', 'economy', 'market'],
            'Health & Medical': ['health', 'medical', 'disease', 'doctor', 'hospital', 'medicine'],
            'Current Affairs': ['news', 'current', 'breaking', 'recent', 'today'],
            'Technology': ['tech', 'computer', 'software', 'hardware', 'ai', 'programming', 'code'],
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in text or keyword in url for keyword in keywords):
                return category
        
        return 'Others'
    
    def _is_confidential(self, url: str) -> bool:
        """Check if URL is confidential."""
        confidential_patterns = [
            'mail.google.com', 'gmail.com', 'drive.google.com',
            'bank', 'banking', 'login', 'signin', 'medical', 'healthcare'
        ]
        
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in confidential_patterns)
