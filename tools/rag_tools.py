# tools/rag_tools.py
from langchain_core.tools import create_retriever_tool
from langchain_chroma import Chroma
from core.rag_setup import get_embedding_model
from core.config import settings

# 1. Load the Vector Store (Chroma)
# We use the same embedding model used during the build_index step
embed_model = get_embedding_model()
vectorstore = Chroma(persist_directory=settings.CHROMA_DB_DIR, embedding_function=embed_model)

# 2. Create a Retriever
retriever = vectorstore.as_retriever(search_kwargs={"k": 1}) # Returns top 3 relevant docs

# 3. Create the Tool
# This tool will automatically format the retrieved docs into a readable string
policy_search_tool = create_retriever_tool(
    retriever,
    "company_faq_search",
    "Search and return information from the company policy documents."
)