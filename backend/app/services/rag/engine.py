import os
import re
import logging
from pathlib import Path
from typing import Any

# Disable telemetry
os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# Vector DB
import chromadb
from chromadb.config import Settings as ChromaClientSettings
from langchain_chroma import Chroma

# LLM (safe import for optional integrations)
try:
    from langchain_ollama import OllamaLLM
except Exception:
    OllamaLLM = None

from app.core.config import settings

# Silence telemetry logs
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

# Updated to ChatPromptTemplate (required for v1 chains)
PROMPT_TEMPLATE = """Answer the question based only on the following context:

Context: {context}

Log: {log_text}
Weather: {rainfall_mm}mm, {temperature_c}°C, {wind_speed_kmh}km/h

Analyze for safety hazards and risks.

Question: {input}"""

# Cache Chroma clients
_CHROMA_CLIENTS: dict[str, chromadb.ClientAPI] = {}

# Text splitter will be imported lazily inside functions to avoid import-time
# failures when langchain-related packages are not installed in the environment.


# -----------------------------
# Embedding model
# -----------------------------
def _embedding_model():
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

# -----------------------------
# Vector store
# -----------------------------
def get_vectorstore(persist_dir: str, collection_name: str = "const_ai_knowledge") -> Chroma:
    resolved_dir = str(Path(persist_dir).resolve())
    client = _CHROMA_CLIENTS.get(resolved_dir)
    if client is None:
        client = chromadb.PersistentClient(
            path=resolved_dir,
            settings=ChromaClientSettings(anonymized_telemetry=False),
        )
        _CHROMA_CLIENTS[resolved_dir] = client

    return Chroma(
        collection_name=collection_name,
        embedding_function=_embedding_model(),
        persist_directory=resolved_dir,
        client=client,
    )

def chunk_document(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
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