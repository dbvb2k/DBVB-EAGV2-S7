"""Configuration module."""

from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

def load_prompts():
    """Load system prompts from JSON file."""
    config_path = Path(__file__).parent / 'system_prompts.json'
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading prompts: {e}")
        return {}
