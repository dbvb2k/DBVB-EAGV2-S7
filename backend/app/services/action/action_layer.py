"""Action layer - executes decided actions."""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ActionLayer:
    """Action layer for executing operations."""
    
    def __init__(self, prompts: Dict[str, Any]):
        """Initialize action layer."""
        self.prompts = prompts.get('action', {})
        self.prompt_template = self.prompts.get('prompt', '')
        
        logger.info("Action layer initialized")
    
    def execute(self, query: str, decision: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute actions based on decision.
        
        Args:
            query: User query
            decision: Decision results
            context: Context from other layers
            
        Returns:
            Dict with execution results
        """
        try:
            actions = decision.get('actions', ['search'])
            results = {}
            
            # Execute each action in priority order
            for action in actions:
                if action == 'search':
                    results['search'] = self._execute_search(query, decision, context)
                elif action == 'highlight':
                    results['highlight'] = self._execute_highlight(query, decision, context)
                elif action == 'categorize':
                    results['categorize'] = self._execute_categorize(decision, context)
                elif action == 'favorite_enabled':
                    results['favorite_enabled'] = True
            
            logger.info(f"Actions executed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error executing actions: {e}")
            return {'error': str(e)}
    
    def _execute_search(self, query: str, decision: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute search action."""
        try:
            # Get memories from context
            memory_results = context.get('memory', {}).get('long_term', [])
            
            # Apply filtering rules
            filtering_rules = decision.get('filtering_rules', {})
            filtered_results = self._apply_filters(memory_results, filtering_rules)
            
            # Apply scoring
            scoring_config = decision.get('scoring_config', {})
            scored_results = self._apply_scoring(filtered_results, scoring_config)
            
            # Categorize results automatically
            user_context = context.get('user_context', {})
            for result in scored_results:
                # Add category tag to result
                category = self._detect_category(result, user_context)
                result['category'] = category
            
            # Sort by score
            scored_results.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            return {
                'success': True,
                'results': scored_results,
                'count': len(scored_results)
            }
            
        except Exception as e:
            logger.error(f"Error executing search: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_highlight(self, query: str, decision: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute highlight action."""
        return {
            'success': True,
            'enabled': True,
            'query': query
        }
    
    def _execute_categorize(self, decision: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute categorization action."""
        # This will be handled during search result processing
        return {
            'success': True,
            'enabled': decision.get('categorization', False)
        }
    
    def _apply_filters(self, results: List[Dict[str, Any]], filtering_rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply filtering rules to results."""
        if not filtering_rules:
            return results
        
        filtered = []
        
        for result in results:
            # Filter confidential sites
            if filtering_rules.get('skip_confidential_sites', False):
                url = result.get('url', '')
                if self._is_confidential(url):
                    continue
            
            # Filter by category
            categories = filtering_rules.get('categories', [])
            if categories:
                result_category = result.get('category', 'Others')
                if result_category not in categories:
                    # Reduce score instead of filtering completely
                    result['score'] = result.get('score', 0.5) * 0.3
                    result['relevance_reduced'] = True
            
            # Filter by minimum relevance
            min_score = filtering_rules.get('min_relevance_score', 0)
            if result.get('score', 0) >= min_score:
                filtered.append(result)
        
        return filtered
    
    def _apply_scoring(self, results: List[Dict[str, Any]], scoring_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply scoring adjustments to results."""
        for result in results:
            base_score = result.get('score', 0.5)
            
            # Boost matching categories if enabled
            if scoring_config.get('boost_matching_categories', False):
                # This would be based on user preferences
                pass
            
            # Store original score for reference
            result['original_score'] = base_score
        
        return results
    
    def _is_confidential(self, url: str) -> bool:
        """Check if URL is confidential."""
        confidential_patterns = [
            'mail.google.com', 'gmail.com', 'drive.google.com',
            'bank', 'banking', 'login', 'signin', 'medical', 'healthcare'
        ]
        
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in confidential_patterns)
    
    def _detect_category(self, content: Dict[str, Any], user_context: Dict[str, Any]) -> str:
        """Detect category from content."""
        text = (content.get('title', '') + ' ' + content.get('content', '')).lower()
        url = content.get('url', '').lower()
        
        # Category keyword detection
        category_keywords = {
            'Sports': ['sport', 'football', 'basketball', 'soccer', 'cricket', 'tennis', 'game', 'match', 'player', 'league', 'championship', 'tournament', 'olympic', 'athletics'],
            'Politics': ['politic', 'government', 'election', 'president', 'senate', 'democracy', 'vote', 'congress', 'parliament', 'minister', 'party', 'candidate', 'campaign'],
            'Financial': ['finance', 'money', 'stock', 'investment', 'bank', 'economy', 'market', 'business', 'financial', 'trading', 'currency', 'dollar', 'economy'],
            'Health & Medical': ['health', 'medical', 'disease', 'doctor', 'hospital', 'medicine', 'treatment', 'wellness', 'cure', 'therapy', 'patient', 'clinic', 'pharmacy', 'symptom'],
            'Current Affairs': ['news', 'current', 'breaking', 'recent', 'today', 'happening', 'update', 'report', 'event', 'announcement'],
            'Technology': ['tech', 'computer', 'software', 'hardware', 'ai', 'programming', 'code', 'digital', 'internet', 'cyber', 'data', 'system', 'app', 'device', 'innovation'],
            'Others': []
        }
        
        for category, keywords in category_keywords.items():
            if category != 'Others':
                if any(keyword in text or keyword in url for keyword in keywords):
                    return category
        
        return 'Others'
