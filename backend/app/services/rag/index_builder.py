from datetime import UTC, datetime
from pathlib import Path

import mlflow
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.services.rag.engine import get_vectorstore, load_documents


def build_index(
    name: str,
    persist_subdir: str,
    pdf_paths: list[str],
    web_urls: list[str],
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> str:
    docs = load_documents(pdf_paths, web_urls)
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = splitter.split_documents(docs) if docs else []

    persist_dir = Path(settings.chroma_persist_dir) / persist_subdir
    persist_dir.mkdir(parents=True, exist_ok=True)
    vectordb = get_vectorstore(str(persist_dir), collection_name=name)
    if chunks:
        vectordb.add_documents(chunks)
        vectordb.persist()

    mlflow.set_experiment(f"{settings.mlflow_experiment_prefix}_{name}")
    with mlflow.start_run(run_name="index_build"):
        mlflow.log_metric("documents", len(docs))
        mlflow.log_metric("chunks", len(chunks))
        mlflow.log_param("persist_dir", str(persist_dir))
        mlflow.log_param("timestamp", datetime.now(UTC).isoformat())

    return str(persist_dir)
