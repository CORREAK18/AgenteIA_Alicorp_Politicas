"""
busqueda_rag.py
===============
Cadena de generación de respuesta (RAG): dado el retriever y la pregunta,
recupera documentos relevantes y genera la respuesta final con el LLM.
"""

from typing import Dict

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


def construir_prompt_rag() -> ChatPromptTemplate:
    return ChatPromptTemplate(
        [
            (
                "system",
                "Eres el especialista en Politicas de la empresa de alimentos y "
                "manufactura Alicorp.\n"
                "Responde siempre utilizando los conocimientos de las bases de "
                "datos pasadas a ti.\n"
                "Si no hay informacion sobre la pregunta en los datos, responde "
                "solo 'No lo se'.",
            ),
            ("human", "Contexto: {context}\nPregunta del empleado: {input}"),
        ]
    )


def construir_document_chain(llm: BaseChatModel):
    
    prompt_rag = construir_prompt_rag()
    return prompt_rag | llm | StrOutputParser()


def busqueda_de_respuesta_rag(pregunta: str, retriever, document_chain) -> Dict:
    
    documentos_relacionados = retriever.invoke(pregunta)

    if not documentos_relacionados:
        return {
            "respuesta": "No lo se",
            "citaciones": [],
            "documentos_encontrados": False,
        }

    answer = document_chain.invoke(
        {
            "input": pregunta,
            "context": documentos_relacionados,
        }
    )

    if answer.rstrip(".!? ") == "No lo se":
        return {
            "respuesta": "No lo se",
            "citaciones": [],
            "documentos_encontrados": False,
        }

    return {
        "respuesta": answer,
        "citaciones": documentos_relacionados,
        "documentos_encontrados": True,
    }