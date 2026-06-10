"""
Tab 4 — Theory Chat
(This tab was declared in st.tabs() in the original app.py but had no implementation.)
"""

import streamlit as st

from tools.shared import CHROMA_DIR, COLLECTION


def render():
    st.header("Theory Chat")
    st.caption("PSV-Theorie-Fragen — RAG-gestützter LLM-Assistent.")

    if not CHROMA_DIR.exists():
        st.warning("Kein Index gefunden. Bitte zuerst Materialien indexieren.")
        return

    question = st.text_area(
        "Frage zur PSV-Theorie:",
        height=150,
        placeholder="Was ist der Unterschied zwischen CTL und LTL?",
        key="chat_question",
    )
    debug_chat = st.checkbox("Debug: Quellen anzeigen", key="chat_debug")

    if st.button("Fragen", type="primary", key="chat_btn"):
        if not question.strip():
            st.warning("Bitte eine Frage eingeben.")
            return
        with st.spinner("Denke nach..."):
            try:
                from chromadb import PersistentClient
                from llama_index.core import VectorStoreIndex, Settings
                from llama_index.vector_stores.chroma import ChromaVectorStore
                from llama_index.embeddings.ollama import OllamaEmbedding
                from llama_index.llms.ollama import Ollama

                Settings.embed_model = OllamaEmbedding(model_name="nomic-embed-text")
                Settings.llm = Ollama(model="qwen2.5:14b", request_timeout=180.0,
                                     system_prompt="Du bist ein PSV-Experte. Beantworte Fragen zur Programmverifikation, Temporallogik, Hoare-Logik, Coverage und SAT/SMT präzise und lehrreich.")
                client = PersistentClient(path=str(CHROMA_DIR))
                collection = client.get_or_create_collection(COLLECTION)
                vector_store = ChromaVectorStore(chroma_collection=collection)
                index = VectorStoreIndex.from_vector_store(vector_store)
                qe = index.as_query_engine(similarity_top_k=5)

                response = qe.query(question)
                st.markdown(str(response))

                if debug_chat and hasattr(response, "source_nodes"):
                    with st.expander("Abgerufene Quellen (Rohtext)"):
                        for i, node in enumerate(response.source_nodes):
                            st.markdown(f"**Quelle {i+1}** — {node.metadata.get('folder')}/{node.metadata.get('source')} (Score: {node.score:.3f})")
                            st.text(node.text[:800])
                            st.divider()

            except Exception as e:
                st.error(f"Fehler: {e}")
