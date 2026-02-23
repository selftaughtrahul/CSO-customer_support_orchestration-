import os
from core.config import Config

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

class LLMSetup:
    def __init__(self, temperature: float = 0.0, max_tokens: int = None, model_name: str = None):
        self.config = Config()
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # If the user didn't specify a model_name in the function, check the .env file
        self.requested_model_name = model_name or self.config.MODEL_NAME
        
        # This will securely hold the final resolved model string
        self.final_model_name = None 
        
        # Initialize the LangChain ChatModel
        self.llm = self._initialize_llm()
        
    def _initialize_llm(self):
        """
        Dynamically load the LLM based on the .env configuration.
        Returns a LangChain BaseChatModel.
        """
        provider = self.config.LLM_PROVIDER
        
        # 1. GROQ (Llama 3 / Mixtral)
        if provider == "groq":
            self.final_model_name = self.requested_model_name or "llama-3.1-8b-instant"
            return ChatGroq(
                model=self.final_model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
        # 2. GEMINI (Google)
        elif provider == "gemini":
            self.final_model_name = self.requested_model_name or "gemini-1.5-flash"
            return ChatGoogleGenerativeAI(
                model=self.final_model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                convert_system_message_to_human=True 
            )
            
        # 3. HUGGING FACE (Serverless Inference API)
        elif provider == "huggingface":
            self.final_model_name = self.requested_model_name or "meta-llama/Meta-Llama-3-8B-Instruct"
            llm_endpoint = HuggingFaceEndpoint(
                repo_id=self.final_model_name,
                temperature=self.temperature if self.temperature > 0 else 0.01,
                max_new_tokens=self.max_tokens or 1024,
                huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN") 
            )
            return ChatHuggingFace(llm=llm_endpoint)
            
        else:
            raise ValueError(f"Unknown LLM_PROVIDER: {provider}. Please check your .env file.")

    def get_llm(self):
        """Returns the initialized LLM."""
        return self.llm

# Helper function to maintain backward compatibility with agents/ files
def get_llm(temperature: float = 0.0, max_tokens: int = None, model_name: str = None):
    setup = LLMSetup(temperature=temperature, max_tokens=max_tokens, model_name=model_name)
    return setup.get_llm()