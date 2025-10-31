"""Memory layer - manages long-term, short-term memory and user preferences."""

import logging
from typing import Dict, Any, List, Optional
from app.services.faiss_index import FaissIndex
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class MemoryLayer:
    """Memory layer managing long-term, short-term memory and preferences."""
    
    def __init__(self, prompts: Dict[str, Any], faiss_index: Optional[FaissIndex] = None):
        """Initialize memory layer."""
        self.prompts = prompts.get('memory', {})
        self.prompt_template = self.prompts.get('prompt', '')
        
        # Initialize memory storage
        self.faiss_index = faiss_index
        self.short_term_memory = []
        self.preferences_path = Path('backend/data/user_preferences.json')
        self._load_preferences()
        
        # Configuration
        self.short_term_limit = 100  # Max items in short-term memory
        self.short_term_timeout = 3600  # 1 hour in seconds
        
        logger.info("Memory layer initialized")
    
    def retrieve(self, query: str, perception: Dict[str, Any], user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Retrieve relevant memories based on query.
        
        Args:
            query: Search query
            perception: Perception layer results
            user_context: User context
            
        Returns:
            Dict with long-term and short-term memories
        """
        try:
            # Retrieve from long-term memory (FAISS index)
            long_term_memories = self._retrieve_long_term(query, perception, user_context)
            
            # Retrieve from short-term memory
            short_term_memories = self._retrieve_short_term(query, user_context)
            
            # Combine and rank memories
            combined_memories = {
                'long_term': long_term_memories,
                'short_term': short_term_memories,
                'total_count': len(long_term_memories) + len(short_term_memories)
            }
            
            logger.info(f"Retrieved {combined_memories['total_count']} memories")
            return combined_memories
            
        except Exception as e:
            logger.error(f"Error retrieving memories: {e}")
            return {'long_term': [], 'short_term': [], 'total_count': 0, 'error': str(e)}
    
    def store(self, content: Dict[str, Any], memory_type: str = 'long_term') -> bool:
        """
        Store content in memory.
        
        Args:
            content: Content to store
            memory_type: 'long_term' or 'short_term'
            
        Returns:
            True if successful
        """
        try:
            if memory_type == 'long_term':
                return self._store_long_term(content)
            elif memory_type == 'short_term':
                return self._store_short_term(content)
            else:
                logger.error(f"Unknown memory type: {memory_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            return False
    
    def update_preferences(self, preferences: Dict[str, Any]) -> bool:
        """Update user preferences with deep merge for nested structures."""
        try:
            self._deep_update(self.preferences, preferences)
            self._save_preferences()
            logger.info("User preferences updated")
            return True
        except Exception as e:
            logger.error(f"Error updating preferences: {e}")
            return False
    
    def _deep_update(self, base: Dict[str, Any], updates: Dict[str, Any]):
        """Recursively update nested dictionaries."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                self._deep_update(base[key], value)
            else:
                # Update or add the value
                base[key] = value
    
    def get_preferences(self) -> Dict[str, Any]:
        """Get current user preferences."""
        return self.preferences.copy()
    
    def _retrieve_long_term(self, query: str, perception: Dict[str, Any], user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Retrieve memories from long-term storage (FAISS)."""
        if not self.faiss_index:
            logger.warning("FAISS index not available")
            return []
        
        try:
            # Use FAISS to search
            from app.services.embedding import get_embedding
            query_embedding = get_embedding(query)
            results = self.faiss_index.search(query_embedding, k=10)
            
            # Apply user preferences filtering
            filtered_results = self._filter_by_preferences(results, user_context)
            
            return filtered_results
        except Exception as e:
            logger.error(f"Error retrieving long-term memory: {e}")
            return []
    
    def _retrieve_short_term(self, query: str, user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Retrieve memories from short-term storage."""
        import time
        current_time = time.time()
        
        # Filter expired short-term memories
        self.short_term_memory = [
            mem for mem in self.short_term_memory
            if current_time - mem.get('timestamp', 0) < self.short_term_timeout
        ]
        
        # Search in short-term memory (simple keyword matching)
        query_lower = query.lower()
        results = []
        
        for memory in self.short_term_memory:
            content = memory.get('content', '').lower()
            if query_lower in content or any(word in content for word in query_lower.split()):
                results.append(memory)
        
        return results[:5]  # Limit to 5 results
    
    def _store_long_term(self, content: Dict[str, Any]) -> bool:
        """Store content in long-term memory (FAISS)."""
        if not self.faiss_index:
            logger.warning("Cannot store in long-term memory: FAISS index not available")
            return False
        
        try:
            from app.services.embedding import get_embedding
            embedding = get_embedding(content.get('content', ''))
            self.faiss_index.add(embedding, content)
            logger.info("Stored in long-term memory")
            return True
        except Exception as e:
            logger.error(f"Error storing in long-term memory: {e}")
            return False
    
    def _store_short_term(self, content: Dict[str, Any]) -> bool:
        """Store content in short-term memory."""
        import time
        
        try:
            memory_item = {
                'content': content.get('content', ''),
                'url': content.get('url', ''),
                'title': content.get('title', ''),
                'timestamp': time.time(),
                'metadata': content.get('metadata', {})
            }
            
            self.short_term_memory.insert(0, memory_item)
            
            # Limit size
            if len(self.short_term_memory) > self.short_term_limit:
                self.short_term_memory = self.short_term_memory[:self.short_term_limit]
            
            logger.info("Stored in short-term memory")
            return True
        except Exception as e:
            logger.error(f"Error storing in short-term memory: {e}")
            return False
    
    def _filter_by_preferences(self, results: List[Dict[str, Any]], user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter results based on user preferences."""
        if not user_context or not results:
            return results
        
        # Get preference settings
        skip_confidential = user_context.get('skip_confidential_sites', True)
        
        filtered = []
        
        for result in results:
            # Check confidential sites
            if skip_confidential:
                url = result.get('url', '')
                if self._is_confidential(url):
                    continue
            
            # Note: Category filtering is handled in the action layer after categorization
            # Don't filter or adjust scores by category here since categories aren't set yet
            
            filtered.append(result)
        
        return filtered
    
    def _is_confidential(self, url: str) -> bool:
        """Check if URL is confidential."""
        confidential_patterns = [
            'mail.google.com', 'gmail.com', 'drive.google.com',
            'bank', 'banking', 'login', 'signin', 'medical', 'healthcare'
        ]
        
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in confidential_patterns)
    
    def _load_preferences(self):
        """Load user preferences from file."""
        try:
            if self.preferences_path.exists():
                with open(self.preferences_path, 'r') as f:
                    self.preferences = json.load(f)
            else:
                self.preferences = {
                    'interests': 'general knowledge',
                    'location': 'global',
                    'favorite_topics': 'all topics',
                    'taste_preferences': 'neutral',
                    'skip_confidential_sites': True,
                    'highlight_search_terms': True,
                    'categories': [],
                    'favorites': []
                }
                self._save_preferences()
        except Exception as e:
            logger.error(f"Error loading preferences: {e}")
            self.preferences = self._get_default_preferences()
    
    def _save_preferences(self):
        """Save user preferences to file."""
        try:
            self.preferences_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.preferences_path, 'w') as f:
                json.dump(self.preferences, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving preferences: {e}")
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Get default user preferences."""
        return {
            'interests': 'general knowledge',
            'location': 'global',
            'favorite_topics': 'all topics',
            'taste_preferences': 'neutral',
            'skip_confidential_sites': True,
            'highlight_search_terms': True,
            'categories': [],
            'favorites': []
        }
