"""
config.py
=========
Carga el archivo .env y expone toda la configuración del proyecto como
variables de módulo. Todos los demás archivos importan de aquí en vez de
leer variables de entorno por su cuenta, para tener un solo lugar donde
se define la configuración.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # lee el archivo .env en el directorio del proyecto

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
EMBEDDINGS_PROVIDER = os.getenv("EMBEDDINGS_PROVIDER", "gemini").lower()

GEMINI_CLAVE = os.getenv("GEMINI_API_KEY")
if "gemini" in (LLM_PROVIDER, EMBEDDINGS_PROVIDER) and not GEMINI_CLAVE:
    raise RuntimeError(
        "No se encontró GEMINI_API_KEY, pero LLM_PROVIDER o EMBEDDINGS_PROVIDER "
        "están configurados como 'gemini'. Crea un archivo .env (puedes copiar "
        ".env.example) con tu clave de Gemini, o cambia esas variables a 'ollama'."
    )

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL")


PDF_DIR = Path(os.getenv("PDF_DIR", "./Documentos"))

FAISS_INDEX_DIR = os.getenv("FAISS_INDEX_DIR", "./faiss_index")


TAMANO_LOTE_EMBEDDINGS = int(os.getenv("TAMANO_LOTE_EMBEDDINGS", "20"))
PAUSA_SEGUNDOS_EMBEDDINGS = int(os.getenv("PAUSA_SEGUNDOS_EMBEDDINGS", "15"))


MOSTRAR_MULTIQUERIES = os.getenv("MOSTRAR_MULTIQUERIES", "true").lower() == "true"