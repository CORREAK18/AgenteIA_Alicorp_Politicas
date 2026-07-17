# Implementa el clasificador de mensajes del agente.
# Decide qué hacer con cada consulta antes de buscar en los PDFs.

import json
import time
from typing import Dict, List, Literal

import config
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field


PROMPT_TRIAJE_TEMPLATE = """
Eres el clasificador de rutas de un asistente interno de Alicorp.
Elige una sola decisión. No respondas la consulta ni expliques tu razonamiento.

Políticas disponibles:
{lista_politicas}

Decisiones y reglas:
- SALUDO: interacción social, saludo, agradecimiento o despedida sin una
  necesidad de información. Si expresa intención de consultar pero no precisa
  el asunto, no es SALUDO: es PEDIR_MAS_INFORMACION.
- FUERA_DE_AMBITO: asunto sin relación con Alicorp, sus políticas o el trabajo
  interno; por ejemplo información general o una solicitud creativa, recreativa
  o cotidiana.
- PEDIR_MAS_INFORMACION: parece una consulta interna, pero es tan vaga o
  incompleta que no permite identificar la información solicitada. Indica en
  campos_faltantes qué debe precisar. También corresponde cuando pide
  requisitos, formatos, vacaciones o un procedimiento sin indicar cuál,
  para qué trámite o de qué política está hablando.
  IMPORTANTE: Si la pregunta ya es una consulta informativa muy concreta (p. ej., solicita un porcentaje, un monto o límite específico de un beneficio como el plan de salud EPS o viáticos), NO debe ir a PEDIR_MAS_INFORMACION, sino a CONSULTAR_RAG, incluso si el término (como EPS) no está en la lista de políticas disponibles.
- ABRIR_TICKET: pide ejecutar una gestión real, registrar una denuncia o
  incidente, obtener una excepción, autorización, acceso o desbloqueo.
  IMPORTANTE: Las consultas donde el usuario pide u orienta a solicitar/obtener una excepción, permiso o autorización especial para saltarse, evadir, omitir o infringir una regla de alguna política (como ciberseguridad, ética o regalos), o pregunta ante quién o dónde realizar dicho pedido de bypass, deben clasificarse obligatoriamente como ABRIR_TICKET.
- CONSULTAR_RAG: pregunta informativa concreta sobre Alicorp, sus políticas,
  reglas, beneficios, compromisos, prohibiciones, requisitos o procedimientos.

Preguntar cómo se hace una gestión es CONSULTAR_RAG; pedir que la ejecutes es
ABRIR_TICKET. Una consulta corporativa concreta va a CONSULTAR_RAG aunque no
sepas si el PDF contiene la respuesta: el RAG comprobará el respaldo.
Usa urgencia BAJA salvo en un ABRIR_TICKET que justifique MEDIA o ALTA.
campos_faltantes debe estar vacío salvo en PEDIR_MAS_INFORMACION.

Ejemplos importantes:
- "Quiero ver los requisitos mínimos" -> PEDIR_MAS_INFORMACION porque no
  identifica los requisitos de qué trámite, beneficio o política.
- "¿De qué trata la política corporativa?" -> PEDIR_MAS_INFORMACION porque no
  identifica cuál política corporativa.
- "Tengo una consulta sobre vacaciones" -> PEDIR_MAS_INFORMACION porque no
  formula una pregunta concreta.
- "Necesito descargar el formato oficial" -> PEDIR_MAS_INFORMACION porque no
  identifica el formato, el trámite ni la política correspondiente.
- "¿Cuál es el porcentaje de cobertura del plan de salud EPS para mis cónyuges?" ->
  CONSULTAR_RAG porque es una consulta concreta de información de beneficios (EPS),
  aunque "EPS" no figure en la lista de políticas disponibles.
- "¿Ante qué área pido una autorización para saltarme una regla de la política de ciberseguridad?" ->
  ABRIR_TICKET porque solicita u orienta a obtener una autorización/excepción para omitir o evadir una regla de seguridad.
- "¿Cuáles son los requisitos para aceptar un regalo de un proveedor?" ->
  CONSULTAR_RAG porque identifica claramente el tema y solicita información.

Genera exclusivamente un objeto JSON con esta estructura:
{{
  "decision": "CONSULTAR_RAG | PEDIR_MAS_INFORMACION | ABRIR_TICKET | FUERA_DE_AMBITO | SALUDO",
  "urgencia": "BAJA | MEDIA | ALTA",
  "campos_faltantes": []
}}
"""


class TriajeOut(BaseModel):
    """Estructura de la respuesta que debe devolver el LLM del triaje."""
    decision: Literal[
        "CONSULTAR_RAG",
        "PEDIR_MAS_INFORMACION",
        "ABRIR_TICKET",
        "FUERA_DE_AMBITO",
        "SALUDO",
    ]
    urgencia: Literal["BAJA", "MEDIA", "ALTA"]
    campos_faltantes: List[str] = Field(default_factory=list)


def construir_prompt_triaje(lista_politicas: str) -> str:
    """Inserta la lista de políticas en el template del prompt y lo devuelve listo."""
    return PROMPT_TRIAJE_TEMPLATE.format(lista_politicas=lista_politicas)


def construir_cadena_triaje(llm: BaseChatModel):
    """
    Configura el LLM para devolver respuestas en formato JSON estructurado (TriajeOut).
    Cohere requiere json_schema; otros proveedores usan el modo por defecto.
    """
    print(f"[TRIAJE-INIT] Proveedor activo: {config.LLM_PROVIDER}")

    if config.LLM_PROVIDER == "cohere":
        return llm.with_structured_output(TriajeOut, method="json_schema")

    return llm.with_structured_output(TriajeOut)


def sub_triaje_extraer_json(contenido) -> Dict:
    """Extrae el JSON del texto cuando el LLM no devolvió un objeto Pydantic."""
    if not isinstance(contenido, str):
        raise TypeError("La respuesta del LLM no contiene texto")

    texto  = contenido.strip()
    inicio = texto.find("{")
    fin    = texto.rfind("}")

    if inicio == -1 or fin < inicio:
        raise ValueError("La respuesta del LLM no contiene un objeto JSON válido")

    return json.loads(texto[inicio : fin + 1])


def ejecutar_triaje(mensaje: str, cadena_triaje, prompt_triaje: str) -> Dict:
    """
    Envía el mensaje al LLM de triaje y devuelve la decisión como diccionario.
    Aplica reglas fijas para evitar combinaciones inválidas (urgencia ALTA en un SALUDO, etc.).
    """
    print(f"[TRIAJE] Clasificando con '{config.LLM_PROVIDER}'...")
    inicio = time.perf_counter()

    try:
        salida = cadena_triaje.invoke(
            [
                SystemMessage(content=prompt_triaje.strip()),
                HumanMessage(content=mensaje.strip()),
            ]
        )

        if isinstance(salida, TriajeOut):
            resultado = salida.model_dump()
        elif isinstance(salida, dict):
            resultado = TriajeOut.model_validate(salida).model_dump()
        else:
            contenido = getattr(salida, "content", salida)
            resultado = TriajeOut.model_validate(
                sub_triaje_extraer_json(contenido)
            ).model_dump()

    except Exception as error:
        print(f"[TRIAJE] Error del LLM: {type(error).__name__}: {error!r}")
        raise RuntimeError("El LLM de triaje no respondió correctamente") from error

    duracion = time.perf_counter() - inicio
    print(f"[TRIAJE] Respondió en {duracion:.2f}s")

    # Solo ABRIR_TICKET puede tener urgencia MEDIA o ALTA
    if resultado["decision"] != "ABRIR_TICKET":
        resultado["urgencia"] = "BAJA"

    # Solo PEDIR_MAS_INFORMACION puede tener campos_faltantes
    if resultado["decision"] != "PEDIR_MAS_INFORMACION":
        resultado["campos_faltantes"] = []

    print(
        f"[TRIAJE] decisión={resultado['decision']} | "
        f"urgencia={resultado['urgencia']}"
    )
    return resultado
