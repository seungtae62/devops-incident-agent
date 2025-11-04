import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    BASE_DIR = Path(__file__).resolve().parent
    DATA_DIR = BASE_DIR / "data"
    VECTORDB_DIR = BASE_DIR / "vectordb"

    # LLM Settings
    AI_ENDPOINT = os.getenv("AI_ENDPOINT")
    AI_API_KEY = os.getenv("AI_API_KEY")
    AI_DEPLOY_GPT4O_MINI = os.getenv("AI_DEPLOY_GPT4O_MINI")
    AI_DEPLOY_GPT4O = os.getenv("AI_DEPLOY_GPT4O")
    AI_DEPLOY_EMBED_3_LARGE = os.getenv("AI_DEPLOY_EMBED_3_LARGE")
    AI_DEPLOY_EMBED_3_SMALL = os.getenv("AI_DEPLOY_EMBED_3_SMALL")
    AI_DEPLOY_EMBED_ADA = os.getenv("AI_DEPLOY_EMBED_ADA")

    @classmethod
    def validate(cls):
        """Validate environments"""
        if not cls.AI_API_KEY:
            raise ValueError("LLM API Key is not set")
