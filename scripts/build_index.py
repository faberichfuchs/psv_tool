"""
Indexiert alle PDFs unter material/ in eine lokale ChromaDB-Vektordatenbank.
Muss einmalig ausgeführt werden, bevor der Theory-Chat-Tab nutzbar ist.

Voraussetzungen:
    pip install llama-index llama-index-vector-stores-chroma
    pip install llama-index-embeddings-ollama llama-index-llms-ollama
    ollama pull nomic-embed-text

Verwendung:
    python scripts/build_index.py
"""

from pathlib import Path
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
from chromadb import PersistentClient

MATERIAL_DIR = Path(__file__).parent.parent / "material"
CHROMA_DIR   = Path(__file__).parent.parent / "chroma_db"
COLLECTION   = "psv"

Settings.embed_model = OllamaEmbedding(model_name="nomic-embed-text")
Settings.llm = None  # kein LLM beim Indexieren nötig

docs = SimpleDirectoryReader(
    str(MATERIAL_DIR),
    recursive=True,
    required_exts=[".pdf"],
).load_data()

print(f"{len(docs)} Dokument(e) geladen aus {MATERIAL_DIR}")

client = PersistentClient(path=str(CHROMA_DIR))
collection = client.get_or_create_collection(COLLECTION)
vector_store = ChromaVectorStore(chroma_collection=collection)

index = VectorStoreIndex.from_documents(docs, vector_store=vector_store)
print(f"Index gespeichert in {CHROMA_DIR}")
