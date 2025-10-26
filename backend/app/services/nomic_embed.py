import numpy as np
from typing import List
import re
import os
from flask import current_app
import logging

logger = logging.getLogger(__name__)

# IMPORTANT: Set the API key BEFORE importing nomic
# The nomic library reads the environment variable at import time
# So we need to set it before the import happens
if 'NOMIC_API_KEY' not in os.environ:
    # This will be set properly in the app context
    pass

from nomic import embed

class NomicEmbed:
    def __init__(self):
        """Initialize Nomic embedding service."""        
        self.dimension = 768  # nomic-embed-text-v1.5 returns 768-dimensional embeddings
        self._initialized = False
    
    def _ensure_initialized(self):
        """Ensure API key is set in environment and initialize nomic."""
        # Always check for API key on every call (not just first time)
        # This ensures the key is available even if config changed
        
        # Try multiple ways to get the API key
        api_key = current_app.config.get('NOMIC_API_KEY') or current_app.config.get('nomic_api_key') or os.environ.get('NOMIC_API_KEY')
        
        if not api_key or api_key.strip() == '':
            # Log helpful debugging info
            logger.error("NOMIC_API_KEY is missing or empty in configuration")
            logger.error(f"NOMIC_API_KEY from config.get('NOMIC_API_KEY'): {repr(current_app.config.get('NOMIC_API_KEY'))}")
            logger.error(f"NOMIC_API_KEY from env: {repr(os.environ.get('NOMIC_API_KEY'))}")
            logger.error(f"All config keys: {list(current_app.config.keys())[:10]}...")  # Show first 10 keys
            raise ValueError("NOMIC_API_KEY is not set or empty in configuration")
        
        # ALWAYS set the API key in environment variable for this request
        # This is critical - the embed library checks env var on every call
        os.environ['NOMIC_API_KEY'] = api_key
        
        # Initialize the embed client with the API key (only once)
        if not self._initialized:
            logger.info(f"NOMIC_API_KEY initialized (length: {len(api_key)} characters)")
            
            # Initialize the embed client with the API key
            try:
                # Try to initialize with the API key
                embed.init(api_key=api_key)
            except (TypeError, AttributeError):
                # If init() doesn't accept api_key, just set the env var
                # The embed module will pick it up from the environment
                pass
            
            self._initialized = True
        
        # Log when the API key is being used (for debugging)
        logger.debug(f"Using NOMIC_API_KEY for embedding (length: {len(api_key)})")
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for the given text using Nomic."""
        try:
            self._ensure_initialized()
            
            # CRITICAL: Get the API key from Flask config (the primary source)
            # Flask's app.config should have it from the Config class
            api_key = None
            
            # Try Flask config first - this is the primary source
            try:
                api_key = current_app.config.get('NOMIC_API_KEY')
                logger.info(f"Retrieved API key from Flask config: {bool(api_key)}")
            except Exception as e:
                logger.error(f"Error getting API key from Flask config: {e}")
            
            # Fallback to environment variable
            if not api_key or api_key.strip() == '':
                api_key = os.environ.get('NOMIC_API_KEY')
                logger.info(f"Retrieved API key from os.environ: {bool(api_key)}")
            
            # Final check with detailed logging
            if not api_key or api_key.strip() == '':
                logger.error("=" * 80)
                logger.error("FATAL ERROR: API key not found!")
                logger.error(f"current_app.config keys: {list(current_app.config.keys())[:20]}")
                logger.error(f"current_app.config.get('NOMIC_API_KEY'): {repr(current_app.config.get('NOMIC_API_KEY'))}")
                logger.error(f"os.environ.get('NOMIC_API_KEY'): {repr(os.environ.get('NOMIC_API_KEY'))}")
                logger.error("=" * 80)
                raise ValueError("NOMIC_API_KEY is not available in Flask config or environment")
            
            # CRITICAL: The nomic library needs the API key to be set BEFORE the library is imported
            # Since we can't change what happened at import time, we need to re-import or use Atlas client
            # For now, let's try setting it and calling with task_type parameter
            
            # Set the environment variable
            os.environ['NOMIC_API_KEY'] = api_key
            
            logger.info(f"About to call embed.text() with API key (length: {len(api_key)})")
            logger.info(f"os.environ['NOMIC_API_KEY'] is now: {os.environ.get('NOMIC_API_KEY')[:10]}...")
            
            # Try calling embed.text with the API key environment variable set
            # Make absolutely sure the env var is set before calling
            current_api_key = os.environ.get('NOMIC_API_KEY')
            logger.info(f"Current os.environ['NOMIC_API_KEY'] before call: {current_api_key[:10] if current_api_key else 'NOT SET'}...")
            
            # The nomic library needs to see the API key in the environment
            # when it checks. Let's also try calling it with explicit parameters
            try:
                # Try calling with possible API key parameters
                result = embed.text(
                    texts=[text],
                    model='nomic-embed-text-v1.5'
                )
                return np.array(result['embeddings'][0], dtype=np.float32)
            except Exception as embed_error:
                # If that fails, try importing the embed module fresh and calling it
                logger.error(f"embed.text() failed: {embed_error}")
                
                # Last resort: Try to call the Nomic API directly via HTTP
                # This bypasses the library's authentication mechanism
                import requests
                url = "https://api-atlas.nomic.ai/v1/embedding/text"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "nomic-embed-text-v1.5",
                    "texts": [text]
                }
                
                logger.info("Attempting direct HTTP call to Nomic API")
                logger.info(f"Request URL: {url}")
                logger.info(f"Payload: {payload}")
                response = requests.post(url, json=payload, headers=headers)
                
                logger.info(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Response data keys: {data.keys()}")
                    embeddings = data['embeddings'][0]
                    embedding_array = np.array(embeddings, dtype=np.float32)
                    
                    # Log the dimension we got
                    logger.info(f"Received embedding of dimension: {embedding_array.shape}")
                    logger.info(f"Embedding array type: {type(embedding_array)}")
                    logger.info(f"Embedding array ndim: {embedding_array.ndim}")
                    logger.info(f"Embedding array shape: {embedding_array.shape}")
                    logger.info(f"First few values: {embedding_array[:5] if len(embedding_array) > 5 else embedding_array}")
                    
                    # Ensure it's the right shape (1D array)
                    if len(embedding_array.shape) == 1:
                        # Good, it's already 1D
                        pass
                    elif len(embedding_array.shape) == 2:
                        # It's 2D, take the first row
                        embedding_array = embedding_array[0]
                    else:
                        logger.warning(f"Unexpected embedding shape: {embedding_array.shape}")
                        embedding_array = embedding_array.flatten()
                    
                    logger.info(f"Returning embedding of dimension: {embedding_array.shape}")
                    return embedding_array
                else:
                    logger.error(f"Direct API call failed: {response.status_code} - {response.text}")
                    raise Exception(f"Nomic API error: {response.text}")
        except Exception as e:
            error_msg = str(e)
            
            # Log the actual error from nomic
            logger.error(f"Error calling embed.text(): {error_msg}")
            
            # Provide helpful error messages for common issues
            if "not configured" in error_msg or "not set" in error_msg:
                raise Exception("""
NOMIC_API_KEY is not properly configured!

To fix this:
1. Make sure you have a .env file in the backend directory
2. The .env file should contain:
   NOMIC_API_KEY=your-actual-api-key-here

3. Get your API key from: https://atlas.nomic.ai/
4. Restart the backend server

See backend/SETUP_INSTRUCTIONS.md for detailed instructions.
""")
            elif "login" in error_msg.lower():
                raise Exception(f"""
Error: {error_msg}

The Nomic API key is not being recognized. Please check:
1. The .env file exists in the backend directory
2. The NOMIC_API_KEY value has no extra quotes or spaces
3. The API key is valid and active
4. You've restarted the backend after adding the key

Original error: {error_msg}
""")
            else:
                raise Exception(f"Error getting embedding: {error_msg}")

# Singleton instance
nomic_embed = NomicEmbed()
