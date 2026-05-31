from pathlib import Path

import mlflow


def main() -> None:
    refs = [
        "ILO Construction Safety Standards",
        "COREN Act 2018",
        "FIDIC General Conditions",
        "Nigeria Data Protection Regulation",
    ]

    out = Path("data/processed/rag_corpus.txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(refs), encoding="utf-8")

    mlflow.set_experiment("rag_indexes")
    with mlflow.start_run(run_name="build_reference_index"):
        mlflow.log_param("documents_indexed", len(refs))

    print("RAG reference corpus built.")


if __name__ == "__main__":
    main()
