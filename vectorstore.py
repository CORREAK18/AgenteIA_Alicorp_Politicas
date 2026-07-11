"""
vectorstore.py
==============
Construcción o carga desde disco del índice FAISS, y armado del retriever
final envuelto en MultiQueryRetriever (la parte de "multipregunta" que
fortalece la búsqueda: en vez de buscar solo con la pregunta literal del
usuario, le pide al LLM generar variantes de la misma pregunta, busca con
cada una, y devuelve la unión de documentos únicos encontrados).

Nota por cia :si se cambia de EMBEDDINGS_PROVIDER (ejemplo: de "gemini" a "ollama"),
    borra la carpeta FAISS_INDEX_DIR antes de correr el script — los
    vectores de un modelo de embeddings no son compatibles con los de otro.
"""

import time
from pathlib import Path
from typing import List

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from langchain_classic.retrievers.multi_query import MultiQueryRetriever

import config


def construir_o_cargar_vectorstore(
    chunks: List[Document], modelo_embeddings: Embeddings
) -> FAISS:
    if modelo_embeddings is None or config.EMBEDDINGS_PROVIDER not in {"ollama", "gemini"}:
        raise RuntimeError(
            "No hay un proveedor de embeddings válido. Configura EMBEDDINGS_PROVIDER "
            "como 'ollama' o 'gemini' y asegúrate de crear el modelo de embeddings antes "
            "de construir el vectorstore."
        )

    faiss_dir = config.FAISS_INDEX_DIR
    
    if Path(faiss_dir).exists():
        print(f"Cargando índice FAISS ya existente desde {faiss_dir}...")
        return FAISS.load_local(
            faiss_dir, modelo_embeddings, allow_dangerous_deserialization=True
        )

    if config.EMBEDDINGS_PROVIDER == "ollama":
        print(f"No hay índice guardado en {faiss_dir}. Calculando embeddings con Ollama...")
        vectorstore = FAISS.from_documents(chunks, modelo_embeddings)
        vectorstore.save_local(faiss_dir)
        print(f"Índice FAISS guardado en {faiss_dir} para futuras ejecuciones.")
        return vectorstore

    return _construir_vectorstore_en_lotes(chunks, modelo_embeddings, faiss_dir)


def _construir_vectorstore_en_lotes(chunks, modelo_embeddings, faiss_dir: str) -> FAISS:
    
    print(f"No hay índice guardado en {faiss_dir}. Calculando embeddings...")

    tamano_lote = config.TAMANO_LOTE_EMBEDDINGS
    pausa_segundos = config.PAUSA_SEGUNDOS_EMBEDDINGS

    vectorstore = None
    total_lotes = (len(chunks) + tamano_lote - 1) // tamano_lote

    for i in range(0, len(chunks), tamano_lote):
        lote = chunks[i : i + tamano_lote]
        numero_lote = i // tamano_lote + 1
        print(f"Embebiendo lote {numero_lote}/{total_lotes} ({len(lote)} chunks)...")

        intentos = 0
        while True:
            try:
                if vectorstore is None:
                    vectorstore = FAISS.from_documents(lote, modelo_embeddings)
                else:
                    vectorstore.add_documents(lote)
                break
            except Exception as e:
                intentos += 1
                if intentos > 3:
                    raise
                print(
                    f"  Error en el lote {numero_lote} ({e}). "
                    f"Reintentando en {pausa_segundos}s (intento {intentos}/3)..."
                )
                time.sleep(pausa_segundos)

        vectorstore.save_local(faiss_dir)

        if numero_lote < total_lotes:
            time.sleep(pausa_segundos)

    print(f"Índice FAISS guardado en {faiss_dir} para futuras ejecuciones.")
    return vectorstore


def construir_retriever(vectorstore: FAISS, llm: BaseChatModel) -> MultiQueryRetriever:
    """Envuelve el retriever base de FAISS con MultiQueryRetriever."""
    retriever_base = vectorstore.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"score_threshold": 0.3, "k": 4},
    )
    return MultiQueryRetriever.from_llm(retriever=retriever_base, llm=llm)