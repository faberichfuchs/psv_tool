"""
PDF Ingestion Script for PSV Exam Assistant
Run once (or after adding new material): python ingest.py
"""

import os
import sys
import fitz  # PyMuPDF
from pathlib import Path
from chromadb import PersistentClient
from llama_index.core import VectorStoreIndex, Document, StorageContext, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

MATERIAL_DIR = Path(r"C:\Users\Fabio Fuchs\Documents\TU_Wien\SS26\ProgSysVer\material\184.741-2026S_2026066_2327")
CHROMA_DIR   = Path(r"C:\Users\Fabio Fuchs\Documents\TU_Wien\SS26\ProgSysVer\chroma_db")
COLLECTION   = "psv"

# Folders to exclude from first pass (add exams later)
EXCLUDE_EXAM_FOLDERS = {"17_Exams"}

def extract_text(pdf_path: Path, include_page_label: bool = True) -> str:
    doc = fitz.open(str(pdf_path))
    parts = []
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        if not text:
            continue
        if include_page_label:
            parts.append(f"[{pdf_path.parent.name} / {pdf_path.name} / Seite {i+1}]\n{text}")
        else:
            parts.append(text)
    return "\n\n".join(parts)


def load_documents(include_exams: bool = False) -> list[Document]:
    docs = []
    for folder in sorted(MATERIAL_DIR.iterdir()):
        if not folder.is_dir():
            continue
        if not include_exams and folder.name in EXCLUDE_EXAM_FOLDERS:
            print(f"  Überspringe (Altprüfungen): {folder.name}")
            continue
        for pdf in sorted(folder.glob("*.pdf")):
            print(f"  Lese: {folder.name}/{pdf.name}")
            text = extract_text(pdf)
            if text.strip():
                docs.append(Document(
                    text=text,
                    metadata={
                        "source": pdf.name,
                        "folder": folder.name,
                        "type": "exam" if folder.name in EXCLUDE_EXAM_FOLDERS else "lecture",
                    }
                ))
    return docs


def build_index(include_exams: bool = False):
    Settings.embed_model = OllamaEmbedding(model_name="nomic-embed-text")
    Settings.llm = Ollama(model="qwen2.5:14b", request_timeout=180.0)
    Settings.chunk_size = 512
    Settings.chunk_overlap = 64

    print(f"\nLade Dokumente (Altprüfungen: {'ja' if include_exams else 'nein'}) ...")
    docs = load_documents(include_exams=include_exams)
    print(f"  {len(docs)} Dokumente geladen.\n")

    CHROMA_DIR.mkdir(exist_ok=True)
    chroma_client = PersistentClient(path=str(CHROMA_DIR))

    # Drop and recreate collection so re-runs are idempotent
    try:
        chroma_client.delete_collection(COLLECTION)
    except Exception:
        pass
    collection = chroma_client.get_or_create_collection(COLLECTION)

    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_ctx  = StorageContext.from_defaults(vector_store=vector_store)

    print("Erstelle Vektorindex ...")
    VectorStoreIndex.from_documents(docs, storage_context=storage_ctx, show_progress=True)
    print("\nFertig! Index gespeichert in:", CHROMA_DIR)


if __name__ == "__main__":
    include_exams = "--with-exams" in sys.argv
    build_index(include_exams=include_exams)
