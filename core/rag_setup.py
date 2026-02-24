import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from core.config import settings


def get_embedding_model():
    if settings.EMBEDDING_PROVIDER == "google":
        return GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    elif settings.EMBEDDING_PROVIDER == "huggingface":
        return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    else:
        return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def build_index():
    pdf_path = os.path.join(settings.DOCS_DIR, "policies.pdf")
    if not os.path.exists(pdf_path):
        print(f"Create a dummy {pdf_path} to test RAG.")
        return
        
    docs = PyPDFLoader(pdf_path).load()
    splits = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100).split_documents(docs)
    
    Chroma.from_documents(
        documents=splits, 
        embedding=get_embedding_model(),
        persist_directory=settings.CHROMA_DB_DIR
    )
    print("Database built.")

if __name__ == "__main__":
    build_index()