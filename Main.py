"""
main.py
=======
Punto de entrada del proyecto:

    python main.py

todas las piezas de los demás módulos:
  1. config       -> variables de entorno
  2. providers    -> LLM y modelo de embeddings
  3. documentos   -> carga y trocea los PDFs, arma la lista de políticas
  4. triaje       -> prompt de triaje + cadena de clasificación
  5. vectorstore  -> índice FAISS (nuevo o cacheado) + retriever multipregunta
  6. busqueda_rag -> cadena de generación de respuesta
  7. grafo        -> arma y compila el grafo de LangGraph
"""

import logging

import config
from busqueda_rag import construir_document_chain
from documentos import cargar_documentos, generar_lista_politicas, trocear_documentos
from grafo import construir_grafo, guardar_diagrama_grafo
from providers import construir_embeddings, construir_llm
from triaje import construir_cadena_triaje, construir_prompt_triaje
from vectorstore import construir_o_cargar_vectorstore, construir_retriever


def main() -> None:
    if config.MOSTRAR_MULTIQUERIES:
        logging.basicConfig()
        logging.getLogger("langchain.retrievers.multi_query").setLevel(logging.INFO)

    # Primero levantamos el modelo principal y el de embeddings.
    llm = construir_llm()
    modelo_embeddings = construir_embeddings()

    # Después cargamos los PDFs y armamos los fragmentos de texto.
    docs = cargar_documentos()
    lista_politicas = generar_lista_politicas(docs)
    chunks = trocear_documentos(docs)

    # Con esto construimos el prompt y la cadena de triaje.
    prompt_triaje = construir_prompt_triaje(lista_politicas)
    cadena_triaje = construir_cadena_triaje(llm)

    # Luego generamos o cargamos el índice FAISS y el retriever.
    vectorstore = construir_o_cargar_vectorstore(chunks, modelo_embeddings)
    retriever = construir_retriever(vectorstore, llm)

    # Con el retriever listo, armamos la cadena de respuesta RAG.
    document_chain = construir_document_chain(llm)

    # Finalmente ensamblamos el grafo y generamos su diagrama.
    grafo = construir_grafo(cadena_triaje, prompt_triaje, retriever, document_chain)
    guardar_diagrama_grafo(grafo)

    # Ejemplo local de ejecución completa.
    pregunta = "Cuales son las politicas de sanciones economicas?"
    respuesta = grafo.invoke({"pregunta": pregunta})

    print(f"Pregunta: {pregunta}")
    print(f"Respuesta: {respuesta['respuesta']}")


if __name__ == "__main__":
    main()