import os
import re
import logging
from pathlib import Path
from typing import Any

# Disable telemetry BEFORE any imports
os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# Silence telemetry logs early
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

from app.core.config import settings

# Lazy-loaded globals (not loaded until actually used)
_chromadb = None
_Chroma = None
_OllamaLLM = None
_CHROMA_CLIENTS: dict[str, Any] = {}

def _lazy_import_chromadb():
    """Lazy load chromadb only when needed."""
    global _chromadb, _Chroma
    if _chromadb is None:
        import chromadb
        from chromadb.config import Settings as ChromaClientSettings
        from langchain_chroma import Chroma
        _chromadb = chromadb
        _Chroma = Chroma
    return _chromadb, _Chroma

def _lazy_import_ollama():
    """Lazy load OllamaLLM only when needed."""
    global _OllamaLLM
    if _OllamaLLM is None:
        try:
            from langchain_ollama import OllamaLLM
            _OllamaLLM = OllamaLLM
        except Exception:
            _OllamaLLM = False  # Mark as tried but failed
    return _OllamaLLM if _OllamaLLM is not False else None

# Updated to ChatPromptTemplate (required for v1 chains)
PROMPT_TEMPLATE = """Answer the question based only on the following context:

Context: {context}

Log: {log_text}
Weather: {rainfall_mm}mm, {temperature_c}°C, {wind_speed_kmh}km/h

Analyze for safety hazards and risks.

Question: {input}"""

# Text splitter will be imported lazily inside functions


# -----------------------------
# Embedding model
# -----------------------------
def _embedding_model():
    """Get embedding model, preferring OpenAI if available, falling back to HuggingFace."""
    # Import embedding implementations lazily to avoid import-time failures
    try:
        from langchain_openai import OpenAIEmbeddings
    except Exception:
        OpenAIEmbeddings = None

    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
    except Exception:
        HuggingFaceEmbeddings = None

    if settings.openai_api_key and OpenAIEmbeddings is not None:
        return OpenAIEmbeddings(api_key=settings.openai_api_key)

    if HuggingFaceEmbeddings is not None:
        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    raise RuntimeError("No embedding backend available: install langchain_openai or langchain_community.embeddings")

# Cache embedding model
_embedding_cache = None

def get_embedding_model():
    """Get cached embedding model."""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = _embedding_model()
    return _embedding_cache

# -----------------------------
# Vector store
# -----------------------------
def get_vectorstore(persist_dir: str, collection_name: str = "const_ai_knowledge") -> Any:
    """Get Chroma vector store with lazy chromadb initialization."""
    chromadb_module, Chroma = _lazy_import_chromadb()
    ChromaClientSettings = chromadb_module.config.Settings
    
    resolved_dir = str(Path(persist_dir).resolve())
    client = _CHROMA_CLIENTS.get(resolved_dir)
    
    if client is None:
        client = chromadb_module.PersistentClient(
            path=resolved_dir,
            settings=ChromaClientSettings(anonymized_telemetry=False),
        )
        _CHROMA_CLIENTS[resolved_dir] = client

    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embedding_model(),
        persist_directory=resolved_dir,
        client=client,
    )

def chunk_document(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    """Split document into chunks. Lazy import to avoid startup overhead."""
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except Exception:
        raise RuntimeError("langchain_text_splitters is required for document chunking")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    return splitter.split_text(text)

# -----------------------------
# Isolated Retrieval with Citations
# -----------------------------
async def query_project_knowledge(
    project_id: int, 
    company_id: int, 
    question: str, 
    persist_dir: str,
    k: int = 4
) -> dict[str, Any]:
    """Query vector store for project-specific knowledge with lazy initialization."""
    vectorstore = get_vectorstore(persist_dir)
    
    # Isolation via metadata filtering
    search_filter = {
        "$and": [
            {"project_id": project_id},
            {"company_id": company_id}
        ]
    }
    
    docs = vectorstore.similarity_search(question, k=k, filter=search_filter)
    
    if not docs:
        return {"answer": "No relevant documents found for this project.", "sources": []}

    context = "\n\n".join(d.page_content for d in docs)
    sources = list(set(d.metadata.get("source", "Unknown") for d in docs))
    
    prompt = f"""You are a construction project assistant. Use the following context to answer the question.
If the answer isn't in the context, say you don't know based on provided docs.

Context:
{context}

Question: {question}

Helpful Answer:"""

    from app.services.llm import ask_ai
    answer = await ask_ai(prompt)
    
    return {
        "answer": answer,
        "sources": sources
    }