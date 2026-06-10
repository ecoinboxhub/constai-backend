import os
import logging
from pathlib import Path
from typing import Any, List, Optional

os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

from app.core.config import settings

_chromadb = None
_Chroma = None
_CHROMA_CLIENTS: dict[str, Any] = {}

logger = logging.getLogger(__name__)


def _lazy_import_chromadb():
    global _chromadb, _Chroma
    if _chromadb is None:
        import chromadb
        from chromadb.config import Settings as ChromaClientSettings
        from langchain_chroma import Chroma
        _chromadb = chromadb
        _Chroma = Chroma
    return _chromadb, _Chroma


PROMPT_TEMPLATE = """Answer the question based only on the following context:

Context: {context}

Log: {log_text}
Weather: {rainfall_mm}mm, {temperature_c}°C, {wind_speed_kmh}km/h

Analyze for safety hazards and risks.

Question: {input}"""


def _embedding_model():
    try:
        from langchain_openai import OpenAIEmbeddings
    except Exception:
        OpenAIEmbeddings = None

    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
    except Exception:
        HuggingFaceEmbeddings = None

    if settings.openai_api_key and OpenAIEmbeddings is not None:
        try:
            return OpenAIEmbeddings(api_key=settings.openai_api_key)
        except Exception:
            pass

    if HuggingFaceEmbeddings is not None:
        try:
            return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        except Exception:
            pass

    raise RuntimeError("No embedding backend available: install langchain_openai or langchain_community.embeddings")


_embedding_cache = None


def get_embedding_model():
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = _embedding_model()
    return _embedding_cache


def get_vectorstore(persist_dir: str, collection_name: str = "const_ai_knowledge") -> Any:
    chromadb_module, Chroma = _lazy_import_chromadb()
    ChromaClientSettings = chromadb_module.config.Settings

    resolved_dir = str(Path(persist_dir).resolve())
    client = _CHROMA_CLIENTS.get(resolved_dir)

    if client is None:
        os.makedirs(resolved_dir, exist_ok=True)
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


async def query_project_knowledge(
    project_id: int,
    company_id: int,
    question: str,
    persist_dir: str,
    k: int = 4
) -> dict[str, Any]:
    vectorstore = get_vectorstore(persist_dir)

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
