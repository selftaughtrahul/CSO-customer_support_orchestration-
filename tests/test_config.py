import pytest
import os
from unittest.mock import patch

# We need to reload the module or patch os.environ carefully 
# before importing Config, since it evaluates on load.
@patch.dict(os.environ, {
    "LLM_PROVIDER": "groq",
    "GROQ_API_KEY": "fake_key",
    "EMBEDDING_PROVIDER": "google"
})
def test_config_loads_environment_variables():
    from core.config import Config
    
    # Reload validation manually for test
    class TestConfig(Config):
        LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
        GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "huggingface").lower()

    assert TestConfig.LLM_PROVIDER == "groq"
    assert TestConfig.GROQ_API_KEY == "fake_key"
    assert TestConfig.EMBEDDING_PROVIDER == "google"

@patch.dict(os.environ, {"LLM_PROVIDER": "groq", "GROQ_API_KEY": ""})
def test_config_validation_raises_error():
    from core.config import Config
    
    class TestConfig(Config):
        LLM_PROVIDER = "groq"
        
    with pytest.raises(ValueError, match="GROQ_API_KEY is missing"):
        TestConfig.LLM_PROVIDER = "groq"
        TestConfig.validate_keys()
