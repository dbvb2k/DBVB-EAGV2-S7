import os
from dotenv import load_dotenv
from pathlib import Path
import logging

basedir = Path(os.path.abspath(os.path.dirname(__file__)))

# Load environment variables from .env file
env_path = basedir / '.env'
load_dotenv(env_path)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if .env file exists
if not env_path.exists():
    logger.error("=" * 80)
    logger.error("ERROR: .env file not found!")
    logger.error("=" * 80)
    logger.error(f"Expected location: {env_path}")
    logger.error("")
    logger.error("Please create a .env file in the backend directory with the following content:")
    logger.error("")
    logger.error("  NOMIC_API_KEY=your-api-key-here")
    logger.error("  GEMINI_API_KEY=your-api-key-here  # Optional")
    logger.error("  SECRET_KEY=dev-key-please-change-in-production")
    logger.error("")
    logger.error("See backend/SETUP_INSTRUCTIONS.md for detailed setup instructions.")
    logger.error("=" * 80)
else:
    logger.info(f"✓ Loaded .env file from {env_path}")

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    NOMIC_API_KEY = os.environ.get('NOMIC_API_KEY')
    FAISS_INDEX_PATH = str(basedir / 'data' / 'faiss_index')
    EMBEDDING_MODEL = 'nomic-embed-text-v1.5'  # Updated to match the model used in nomic_embed.py
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max content length
    
    # Validate required configuration
    @staticmethod
    def validate():
        """Validate that all required configuration is present."""
        errors = []
        
        if not Config.NOMIC_API_KEY or Config.NOMIC_API_KEY == '':
            errors.append("""
ERROR: NOMIC_API_KEY is not configured!
==================================================
The NOMIC_API_KEY environment variable is missing or empty.

To fix this:
1. Create or edit the .env file in the backend directory
2. Add the following line:
   NOMIC_API_KEY=your-actual-api-key-here

3. Get your API key from: https://atlas.nomic.ai/

See backend/SETUP_INSTRUCTIONS.md for detailed instructions.
==================================================
""")
        
        if errors:
            logger.error("\n" + "".join(errors))
            raise ValueError("Configuration validation failed. See error messages above.")
        
        logger.info("✓ Configuration validated successfully")
        logger.info(f"  - NOMIC_API_KEY: {'✓ Set' if Config.NOMIC_API_KEY else '✗ Missing'}")
        logger.info(f"  - GEMINI_API_KEY: {'✓ Set' if Config.GEMINI_API_KEY else '○ Optional (not set)'}")
        logger.info(f"  - FAISS index path: {Config.FAISS_INDEX_PATH}")
    
    # Create data directory if it doesn't exist
    (basedir / 'data').mkdir(parents=True, exist_ok=True) 