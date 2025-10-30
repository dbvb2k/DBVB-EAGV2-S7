"""Main cognitive agent orchestrator."""

import logging
from typing import Dict, Any, List
from app.services.perception import PerceptionLayer
from app.services.memory import MemoryLayer
from app.services.decision import DecisionLayer
from app.services.action import ActionLayer
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class CognitiveAgent:
    """Main orchestrator for the 4-layer cognitive architecture."""
    
    def __init__(self, config_path: str = None, faiss_index=None, gemini_chat=None):
        """Initialize the cognitive agent with all layers."""
        self.config_path = config_path or Path(__file__).parent.parent / 'config' / 'system_prompts.json'
        self.prompts = self._load_prompts()
        
        # Store references
        self.faiss_index = faiss_index
        self.gemini_chat = gemini_chat
        
        # Initialize layers with dependencies
        self.perception = PerceptionLayer(self.prompts)
        self.memory = MemoryLayer(self.prompts, self.faiss_index)
        self.decision = DecisionLayer(self.prompts, self.gemini_chat)
        self.action = ActionLayer(self.prompts)
        
        logger.info("Cognitive agent initialized with all layers")
    
    def _load_prompts(self) -> Dict[str, Any]:
        """Load system prompts from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading prompts: {e}")
            return {}
    
    def process_user_query(self, query: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main orchestration method - processes user query through all layers.
        
        Flow: User Query -> Perception -> Memory -> Decision -> Action -> Result
        """
        try:
            # Layer 1: PERCEPTION - Understand context and intent
            logger.info(f"Perception: Processing query: {query}")
            perception_result = self.perception.analyze(query, user_context)
            
            # Layer 2: MEMORY - Retrieve relevant memories
            logger.info("Memory: Retrieving relevant memories")
            memory_result = self.memory.retrieve(query, perception_result, user_context)
            
            # Layer 3: DECISION - Decide what actions to take
            logger.info("Decision: Determining actions")
            decision_result = self.decision.make_decision(
                query=query,
                perception=perception_result,
                memory=memory_result,
                user_context=user_context
            )
            
            # Layer 4: ACTION - Execute the decided actions
            logger.info("Action: Executing actions")
            action_result = self.action.execute(
                query=query,
                decision=decision_result,
                context={
                    'perception': perception_result,
                    'memory': memory_result,
                    'user_context': user_context or {}
                }
            )
            
            # Combine all layer results
            final_result = {
                'query': query,
                'perception': perception_result,
                'memory': memory_result,
                'decision': decision_result,
                'action': action_result,
                'user_context': user_context
            }
            
            logger.info("Agent: Completed query processing")
            return final_result
            
        except Exception as e:
            logger.error(f"Error in cognitive agent processing: {e}", exc_info=True)
            return {
                'error': str(e),
                'query': query
            }
    
    def update_user_preferences(self, preferences: Dict[str, Any]) -> bool:
        """Update user preferences in memory."""
        try:
            return self.memory.update_preferences(preferences)
        except Exception as e:
            logger.error(f"Error updating preferences: {e}")
            return False
    
    def get_user_preferences(self) -> Dict[str, Any]:
        """Get current user preferences."""
        return self.memory.get_preferences()
