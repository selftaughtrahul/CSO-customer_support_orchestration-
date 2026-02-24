import os
from dotenv import load_dotenv

# Load the keys
load_dotenv()

class Config:
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
    MODEL_NAME = os.getenv("MODEL_NAME")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    HUGGINGFACEHUB_API_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")
    
    # Validation helper
    @staticmethod
    def validate_keys():
        if Config.LLM_PROVIDER == "groq" and not os.getenv("GROQ_API_KEY"):
            raise ValueError("GROQ_API_KEY is missing from .env")
        if Config.LLM_PROVIDER == "gemini" and not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("GOOGLE_API_KEY is missing from .env")
        if Config.LLM_PROVIDER == "huggingface" and not os.getenv("HUGGINGFACEHUB_API_TOKEN"):
            raise ValueError("HUGGINGFACEHUB_API_TOKEN is missing from .env")

# Run validation on import
Config.validate_keys()