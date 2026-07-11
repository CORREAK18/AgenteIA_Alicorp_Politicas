"""
triaje.py
=========
Primer paso del flujo: clasifica el mensaje del colaborador en
CONSULTAR_RAG / PEDIR_MAS_INFORMACION / ABRIR_TICKET, usando salida
estructurada (with_structured_output) validada con pydantic.
"""

from typing import Dict, List, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

PROMPT_TRIAJE_TEMPLATE = """
Eres un especialista en triaje para consultas internas de colaboradores sobre las políticas corporativas de Alicorp.
Dado el mensaje del usuario, devuelve SÓLO un JSON con:

{{
    "decision": "CONSULTAR_RAG" | "PEDIR_MAS_INFORMACION" | "ABRIR_TICKET",
    "urgencia": "BAJA" | "MEDIA" | "ALTA",
    "campos_faltantes": ["..."]
}}

Las políticas disponibles son:
{lista_politicas}

Reglas:
- **CONSULTAR_RAG**: Cuando exista información suficiente en alguna de las políticas corporativas para responder total o parcialmente la consulta del colaborador. No solicites información adicional si la respuesta puede obtenerse consultando las políticas.
- **PEDIR_MAS_INFORMACION**: Cuando el mensaje sea ambiguo, incompleto o no proporcione suficiente contexto para comprender la consulta. Indica en **campos_faltantes** la información que falta.
- **ABRIR_TICKET**: Cuando el colaborador solicite una autorización, una excepción, quiera reportar un posible incumplimiento o requiera una acción o decisión que corresponda al área responsable y no pueda resolverse únicamente consultando las políticas.
Analiza el mensaje y decide la acción más adecuada.
"""


class TriajeOut(BaseModel):
    decision: Literal["CONSULTAR_RAG", "PEDIR_MAS_INFORMACION", "ABRIR_TICKET"]
    urgencia: Literal["BAJA", "MEDIA", "ALTA"]
    campos_faltantes: List[str] = Field(default_factory=list)


def construir_prompt_triaje(lista_politicas: str) -> str:
    """Arma el prompt de triaje final, insertando la lista real de políticas."""
    return PROMPT_TRIAJE_TEMPLATE.format(lista_politicas=lista_politicas)


def construir_cadena_triaje(llm: BaseChatModel):
    """Envuelve el LLM para que devuelva siempre un TriajeOut validado."""
    return llm.with_structured_output(TriajeOut)


def triaje(mensaje: str, cadena_triaje, prompt_triaje: str) -> Dict:
    """Ejecuta el triaje sobre un mensaje y devuelve un dict (no un objeto pydantic)."""
    salida: TriajeOut = cadena_triaje.invoke(
        [
            SystemMessage(content=prompt_triaje),
            HumanMessage(content=mensaje),
        ]
    )
    return salida.model_dump()