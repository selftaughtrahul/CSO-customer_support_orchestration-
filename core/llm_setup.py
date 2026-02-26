import os
import logging
from core.config import Config

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_anthropic import ChatAnthropic

_log = logging.getLogger(__name__)

# Errors that signal a transient API-side problem and should trigger fallback
_FALLBACK_EXCEPTIONS = (
    Exception,   # catch-all: timeout, rate-limit, 5xx — let the fallback decide
)


class LLMSetup:
    # Default read timeout (seconds) for all LLM HTTP calls
    _TIMEOUT = 120

    def __init__(self, temperature: float = 0.0, max_tokens: int = None, model_name: str = None):
        self.config = Config()
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.requested_model_name = model_name or self.config.MODEL_NAME
        self.final_model_name = None
        self.llm = self._initialize_llm()

    # ------------------------------------------------------------------
    # Internal: build one concrete LLM for a given provider
    # ------------------------------------------------------------------

    def _build_single_llm(self, provider: str, model_name: str = None):
        """Return a configured LangChain chat model for *provider*."""
        if provider == "groq":
            name = model_name or "llama-3.1-8b-instant"
            return ChatGroq(
                model=name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self._TIMEOUT,
            )

        if provider == "gemini":
            name = model_name or "gemini-2.5-flash"
            return ChatGoogleGenerativeAI(
                model=name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                convert_system_message_to_human=True,
                timeout=self._TIMEOUT,
            )

        if provider == "huggingface":
            name = model_name or "meta-llama/Meta-Llama-3-8B-Instruct"
            endpoint = HuggingFaceEndpoint(
                repo_id=name,
                temperature=self.temperature if self.temperature > 0 else 0.01,
                max_new_tokens=self.max_tokens or 1024,
                huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
                timeout=self._TIMEOUT,
            )
            return ChatHuggingFace(llm=endpoint)

        if provider == "anthropic":
            name = model_name or "claude-3-5-sonnet-latest"
            return ChatAnthropic(
                model_name=name,
                temperature=self.temperature,
                max_tokens=self.max_tokens or 1024,
                default_request_timeout=self._TIMEOUT,
            )

        raise ValueError(f"Unknown LLM provider '{provider}'. "
                         "Valid: groq, gemini, huggingface, anthropic, auto")

    # ------------------------------------------------------------------
    # Internal: pick single or auto-fallback chain
    # ------------------------------------------------------------------

    def _initialize_llm(self):
        """
        Build and return the LLM (or auto-fallback chain).

        LLM_PROVIDER=auto  →  primary.with_fallbacks([fallback])
            If the primary raises ANY exception (timeout, rate-limit, 5xx …),
            LangChain transparently retries the same call on the fallback model.

        LLM_PROVIDER=<provider>  →  a single ChatModel as before.
        """
        provider = self.config.LLM_PROVIDER

        if provider == "auto":
            p_prov  = self.config.AUTO_PRIMARY_PROVIDER
            p_model = self.config.AUTO_PRIMARY_MODEL
            f_prov  = self.config.AUTO_FALLBACK_PROVIDER
            f_model = self.config.AUTO_FALLBACK_MODEL

            primary  = self._build_single_llm(p_prov, p_model)
            fallback = self._build_single_llm(f_prov, f_model)

            self.final_model_name = (
                f"auto | primary={p_prov}/{p_model} "
                f"→ fallback={f_prov}/{f_model}"
            )
            _log.info(
                "LLM auto-fallback chain: %s/%s  →  %s/%s",
                p_prov, p_model, f_prov, f_model,
            )
            return primary.with_fallbacks(
                [fallback],
                exceptions_to_handle=_FALLBACK_EXCEPTIONS,
            )

        # Single provider mode (unchanged behaviour)
        self.final_model_name = self.requested_model_name
        return self._build_single_llm(provider, self.requested_model_name)

    def get_llm(self):
        """Returns the initialized LLM (or auto-fallback chain)."""
        return self.llm


# Helper function — backward-compatible with all agents
def get_llm(temperature: float = 0.0, max_tokens: int = None, model_name: str = None):
    setup = LLMSetup(temperature=temperature, max_tokens=max_tokens, model_name=model_name)
    return setup.get_llm()
