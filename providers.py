"""
providers.py
============
Construye el LLM y el modelo de embeddings según el proveedor configurado
en config.py (Gemini u Ollama). Esta es la única capa que sabe de las
librerías específicas de cada proveedor (langchain_google_genai /
langchain_ollama) — el resto del código trabaja contra la interfaz genérica
de LangChain (BaseChatModel / Embeddings) sin importarle de dónde vienen.
"""

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_ollama import ChatOllama, OllamaEmbeddings

import config


def construir_llm():
    """Devuelve el LLM (chat model) según LLM_PROVIDER en config."""
    if config.LLM_PROVIDER == "ollama":
        print(
            f"LLM: usando Ollama local, modelo '{config.OLLAMA_LLM_MODEL}' "
            f"en {config.OLLAMA_BASE_URL}"
        )
        return ChatOllama(
            model=config.OLLAMA_LLM_MODEL,
            temperature=0,
            base_url=config.OLLAMA_BASE_URL,
        )

    if config.LLM_PROVIDER == "gemini":
        print("LLM: usando Gemini API, modelo 'gemini-3.5-flash'")
        return ChatGoogleGenerativeAI(
            model="gemini-3.5-flash",
            temperature=0,
            google_api_key=config.GEMINI_CLAVE,
        )

    raise ValueError(
        f"LLM_PROVIDER='{config.LLM_PROVIDER}' no reconocido. Usa 'gemini' u 'ollama'."
    )


def construir_embeddings():
    
    if config.EMBEDDINGS_PROVIDER == "ollama":
        print(
            f"Embeddings: usando Ollama local, modelo "
            f"'{config.OLLAMA_EMBEDDING_MODEL}' en {config.OLLAMA_BASE_URL}"
        )
        return OllamaEmbeddings(
            model=config.OLLAMA_EMBEDDING_MODEL,
            base_url=config.OLLAMA_BASE_URL,
        )

    if config.EMBEDDINGS_PROVIDER == "gemini":
        print("Embeddings: usando Gemini API, modelo 'gemini-embedding-2-preview'")
        return GoogleGenerativeAIEmbeddings(
            model="gemini-embedding-2-preview",
            google_api_key=config.GEMINI_CLAVE,
        )

    raise ValueError(
        f"EMBEDDINGS_PROVIDER='{config.EMBEDDINGS_PROVIDER}' no reconocido. "
        "Usa 'gemini' u 'ollama'."
    )