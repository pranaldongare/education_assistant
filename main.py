# main.py
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

# Configure logging with UTF-8 encoding support
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_tutor.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Set console encoding to UTF-8 for Windows
if sys.platform == "win32":
    import locale
    # Try to set console to UTF-8
    try:
        import io
        import codecs
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        # Fallback: remove emojis from logging
        pass

logger = logging.getLogger(__name__)

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = ['OPENAI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please create a .env file with the following variables:")
        for var in missing_vars:
            logger.error(f"{var}=your_value_here")
        return False
    
    return True

def main():
    """Main application entry point"""
    try:
        logger.info("Starting AI Tutor Agent...")
        
        # Check environment
        if not check_environment():
            logger.error("Environment check failed. Exiting.")
            sys.exit(1)
        
        # Import after environment check
        from config.settings import settings
        from ui.gradio_interface import gradio_interface
        from models.database import create_tables
        
        logger.info(f"Initializing AI Tutor Agent v{settings.app_version}")
        logger.info(f"Using OpenAI model: {settings.openai_model}")
        
        # Initialize database
        logger.info("Initializing database...")
        create_tables()
        
        # Launch the interface
        logger.info("Launching web interface...")
        gradio_interface.launch()
        
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Application error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()