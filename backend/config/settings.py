
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Base Paths
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    BACKEND_DIR = BASE_DIR / "backend"
    FRONTEND_DIR = BASE_DIR / "frontend"
    LOG_DIR = BASE_DIR / "logs"
    OUTPUT_DIR = BASE_DIR / "output"
    UPLOAD_DIR = BASE_DIR / "uploads"
    
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    
    # Service Configuration
    API_PORT = int(os.getenv("API_PORT", "8000"))
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # default LLM
    DEFAULT_LLM_PROVIDER = "claude"

    # Build Configuration
    MAVEN_BUILD_TIMEOUT = int(os.getenv("MAVEN_BUILD_TIMEOUT", "900")) # 15 minutes default

    def __init__(self):
        # Ensure directories exist
        self.LOG_DIR.mkdir(exist_ok=True, parents=True)
        self.OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
        self.UPLOAD_DIR.mkdir(exist_ok=True, parents=True)

settings = Settings()
