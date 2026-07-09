"""
documentos.py
=============
Carga de los PDFs de políticas, trozado (chunking) en fragmentos indexables,
y generación dinámica de la lista de políticas que se le muestra al LLM en
el prompt de triaje.
"""

from pathlib import Path
from typing import List, Optional

from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config


def cargar_documentos(pdf_dir: Optional[Path] = None) -> List[Document]:
    """Carga todos los PDFs de pdf_dir (por defecto, config.PDF_DIR)."""
    pdf_dir = pdf_dir or config.PDF_DIR
    docs: List[Document] = []

    if not pdf_dir.exists():
        raise FileNotFoundError(
            f"No existe la carpeta {pdf_dir}. Crea la carpeta y coloca ahí "
            "los PDFs de las políticas ."
        )

    for n in pdf_dir.glob("*.pdf"):
        try:
            loader = PyMuPDFLoader(str(n))
            docs.extend(loader.load())
            print(f"Archivo cargado: {n.name}")
        except Exception as e:
            print(f"Error cargando archivo: {n.name}: {e}")

    print(f"Total de documentos cargados: {len(docs)}")
    if not docs:
        raise RuntimeError(
            f"No se cargó ningún PDF desde {pdf_dir}. Verifica que la "
            "carpeta contenga archivos .pdf válidos."
        )
    return docs


def trocear_documentos(
    docs: List[Document], chunk_size: int = 1000, chunk_overlap: int = 100
) -> List[Document]:
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    chunks = splitter.split_documents(docs)
    print(f"Total de chunks a indexar: {len(chunks)}")
    return chunks


def generar_lista_politicas(docs: List[Document]) -> str:
    
    nombres = sorted(
        {Path(d.metadata.get("source", "")).stem for d in docs if d.metadata.get("source")}
    )
    lista = "\n".join(f"- {nombre}." for nombre in nombres)
    print(f"Políticas detectadas para el triaje: {nombres}")
    return lista