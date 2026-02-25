import pytest
from core.llm_setup import LLMSetup
from unittest.mock import patch, MagicMock

@patch("core.llm_setup.Config")
def test_llm_setup_initialization(mock_config):
    # Setup mock config to bypass dotenv
    mock_instance = mock_config.return_value
    mock_instance.LLM_PROVIDER = "groq"
    mock_instance.MODEL_NAME = "llama-3.1-8b-instant"
    
    with patch("core.llm_setup.ChatGroq") as mock_groq:
        setup = LLMSetup(temperature=0.5)
        
        assert setup.temperature == 0.5
        mock_groq.assert_called_once_with(
            model="llama-3.1-8b-instant",
            temperature=0.5,
            max_tokens=None
        )

@patch("core.llm_setup.Config")
def test_llm_setup_unknown_provider(mock_config):
    mock_instance = mock_config.return_value
    mock_instance.LLM_PROVIDER = "unknown_provider"
    
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER: unknown_provider"):
        LLMSetup()
