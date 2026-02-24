import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from core.config import settings


def get_embedding_model():
    if settings.EMBEDDING_PROVIDER == "google":
        model_name = settings.EMBEDDING_MODEL or "models/embedding-001"
        return GoogleGenerativeAIEmbeddings(model=model_name)
    elif settings.EMBEDDING_PROVIDER == "huggingface":
        model_name = settings.EMBEDDING_MODEL or "all-MiniLM-L6-v2"
        return HuggingFaceEmbeddings(model_name=model_name)
    else:
        model_name = settings.EMBEDDING_MODEL or "all-MiniLM-L6-v2"
        return HuggingFaceEmbeddings(model_name=model_name)

def build_index():
    docs_dir = settings.DOCS_DIR
    if not os.path.exists(docs_dir):
        print(f"Directory {docs_dir} does not exist.")
        return
    all_docs = []

    # 🔁 Walk recursively through directory
    for root, _, files in os.walk(docs_dir):
        for file in files:
            file_path = os.path.join(root, file)

            try:
                # 📄 Handle PDF
                if file.lower().endswith(".pdf"):
                    loader = PyPDFLoader(file_path)
                    all_docs.extend(loader.load())

                # 📃 Handle text files
                elif file.lower().endswith(".txt"):
                    loader = TextLoader(file_path)
                    all_docs.extend(loader.load())
                    
                elif file.lower().endswith(".docx"):
                    loader = TextLoader(file_path)
                    all_docs.extend(loader.load())

                # You can add more loaders here (docx, csv, etc.)

            except Exception as e:
                print(f"Error loading {file_path}: {e}")

    if not all_docs:
        print("No documents found to ingest.")
        return

    # ✂️ Split documents
    splits = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    ).split_documents(all_docs)

    # 🧠 Create / Persist Vector DB
    if os.path.exists(settings.CHROMA_DB_DIR):
        import shutil
        shutil.rmtree(settings.CHROMA_DB_DIR)

    Chroma.from_documents(
        documents=splits,
        embedding=get_embedding_model(),
        persist_directory=settings.CHROMA_DB_DIR
    )

    print(f"Database built with {len(splits)} chunks.")

if __name__ == "__main__":
    build_index()