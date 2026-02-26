import os
from dotenv import load_dotenv

# Load the keys, overriding any existing system environment variables
load_dotenv(override=True)

class Config:
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
    MODEL_NAME = os.getenv("MODEL_NAME")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    HUGGINGFACEHUB_API_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")

    # Auto-fallback mode: try primary, silently switch to fallback on any failure
    AUTO_PRIMARY_PROVIDER  = os.getenv("AUTO_PRIMARY_PROVIDER",  "gemini").lower()
    AUTO_PRIMARY_MODEL     = os.getenv("AUTO_PRIMARY_MODEL",     "gemini-2.5-flash")
    AUTO_FALLBACK_PROVIDER = os.getenv("AUTO_FALLBACK_PROVIDER", "groq").lower()
    AUTO_FALLBACK_MODEL    = os.getenv("AUTO_FALLBACK_MODEL",    "llama-3.1-8b-instant")

    # RAG Settings
    EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "huggingface").lower()
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
    DOCS_DIR = os.getenv("DOCS_DIR", "./docs")
    CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "./chroma_db")
    ANNOTATED_API_KEY = os.getenv("ANTHROPIC_API_KEY")

    # Validation helper
    @staticmethod
    def _check_key(provider: str, label: str):
        key_map = {
            "groq":        ("GROQ_API_KEY",            os.getenv("GROQ_API_KEY")),
            "gemini":      ("GOOGLE_API_KEY",           os.getenv("GOOGLE_API_KEY")),
            "huggingface": ("HUGGINGFACEHUB_API_TOKEN", os.getenv("HUGGINGFACEHUB_API_TOKEN")),
            "anthropic":   ("ANTHROPIC_API_KEY",        os.getenv("ANTHROPIC_API_KEY")),
        }
        if provider not in key_map:
            raise ValueError(f"Unknown provider '{provider}' for {label}. "
                             "Valid: groq, gemini, huggingface, anthropic")
        env_name, value = key_map[provider]
        if not value:
            raise ValueError(f"{env_name} is missing from .env (required for {label} provider={provider})")

    @staticmethod
    def validate_keys():
        provider = Config.LLM_PROVIDER

        if provider == "auto":
            # Validate both primary and fallback providers
            Config._check_key(Config.AUTO_PRIMARY_PROVIDER,  "AUTO_PRIMARY")
            Config._check_key(Config.AUTO_FALLBACK_PROVIDER, "AUTO_FALLBACK")
        else:
            Config._check_key(provider, "LLM_PROVIDER")

# Run validation on import
Config.validate_keys()

settings = Config()
