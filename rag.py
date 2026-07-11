"""
Agente de Políticas Corporativas - Alicorp


"""


import os
import time
import logging
from pathlib import Path
from typing import Literal, List, Dict, Optional, TypedDict
# hola
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_classic.retrievers.multi_query import MultiQueryRetriever

from langgraph.graph import START, END, StateGraph


# 0. Configuración inicial

load_dotenv()  # lee el archivo .env en el directorio del proyecto

GEMINI_CLAVE = os.getenv("GEMINI_API_KEY")
if not GEMINI_CLAVE:
    raise RuntimeError(
        "No se encontró GEMINI_API_KEY"
    )

# Carpeta donde deben ir tus PDFs de políticas (cámbiala si quieres otra ruta)
PDF_DIR = Path(os.getenv("PDF_DIR", "./Documentos"))

# Activa esto si quieres ver en consola las variantes de pregunta que genera
# el MultiQueryRetriever (útil para depurar / entender qué está buscando)
MOSTRAR_MULTIQUERIES = os.getenv("MOSTRAR_MULTIQUERIES", "true").lower() == "true"
if MOSTRAR_MULTIQUERIES:
    logging.basicConfig()
    logging.getLogger("langchain.retrievers.multi_query").setLevel(logging.INFO)


def construir_llm():
    print("LLM: usando Gemini API, modelo 'gemini-3.5-flash'")
    return ChatGoogleGenerativeAI(
        model="gemini-3.5-flash",
        temperature=0,
        google_api_key=GEMINI_CLAVE,
    )


def construir_embeddings():
    print("Embeddings: usando Gemini API, modelo 'gemini-embedding-2-preview'")
    return GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2-preview",
        google_api_key=GEMINI_CLAVE,
    )



# 1. LLM

llm = construir_llm()



# 2. Triaje

PROMPT_TRIAJE = """
Eres un especialista en triaje para consultas internas de colaboradores sobre las políticas corporativas de Alicorp.
Dado el mensaje del usuario, devuelve SÓLO un JSON con:

{
    "decision": "CONSULTAR_RAG" | "PEDIR_MAS_INFORMACION" | "ABRIR_TICKET",
    "urgencia": "BAJA" | "MEDIA" | "ALTA",
    "campos_faltantes": ["..."]
}

Las políticas disponibles son:
- Política Corporativa de Sanciones Económicas.
- Nuestro Compromiso con el Marketing Responsable.

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


cadena_triaje = llm.with_structured_output(TriajeOut)


def triaje(mensaje: str) -> Dict:
    salida: TriajeOut = cadena_triaje.invoke(
        [
            SystemMessage(content=PROMPT_TRIAJE),
            HumanMessage(content=mensaje),
        ]
    )
    return salida.model_dump()



# 3. Carga y trozado de documentos

def cargar_documentos(pdf_dir: Path):
    docs = []
    if not pdf_dir.exists():
        raise FileNotFoundError(
            f"No existe la carpeta {pdf_dir}. Crea la carpeta y coloca ahí "
            "los PDFs de las políticas (o cambia PDF_DIR en el .env)."
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


docs = cargar_documentos(PDF_DIR)

# Chunks un poco más grandes que el original (300) para reducir la cantidad

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
chunks = splitter.split_documents(docs)
print(f"Total de chunks a indexar: {len(chunks)}")



# 4. Embeddings + Vectorstore

modelo_embeddings = construir_embeddings()

# Carpeta donde se guarda el índice FAISS ya calculado. Si existe, se carga
# directamente desde disco . Si no existe ,se calcula desde cero y se guarda para la próxima ejecución.
FAISS_INDEX_DIR = os.getenv("FAISS_INDEX_DIR", "./faiss_index")

if Path(FAISS_INDEX_DIR).exists():
    print(f"Cargando índice FAISS ya existente desde {FAISS_INDEX_DIR}")
    vectorstore = FAISS.load_local(
        FAISS_INDEX_DIR,
        modelo_embeddings,
        allow_dangerous_deserialization=True,
    )
else:
    print(f"No hay índice guardado en {FAISS_INDEX_DIR}. Calculando embeddings")
    TAMANO_LOTE = 20
    PAUSA_SEGUNDOS = 15

    vectorstore = None
    total_lotes = (len(chunks) + TAMANO_LOTE - 1) // TAMANO_LOTE

    for i in range(0, len(chunks), TAMANO_LOTE):
        lote = chunks[i : i + TAMANO_LOTE]
        numero_lote = i // TAMANO_LOTE + 1
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
                    f"Reintentando en {PAUSA_SEGUNDOS}s (intento {intentos}/3)..."
                )
                time.sleep(PAUSA_SEGUNDOS)

        vectorstore.save_local(FAISS_INDEX_DIR)

        if numero_lote < total_lotes:
            time.sleep(PAUSA_SEGUNDOS)

    print(f"Índice FAISS guardado en {FAISS_INDEX_DIR} para futuras ejecuciones.")

retriever_base = vectorstore.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={"score_threshold": 0.3, "k": 4},
)


# 4bis. Multi-Query Retriever 

# En vez de buscar solo con la pregunta literal del usuario, este retriever le pide al LLM generar varias reformulaciones de la misma pregunta
# Por ejemplo :. "¿Puedo aprobar esta excepción?", el LLM puede generar variantes como
# "¿Cuál es el procedimiento para aprobar excepciones?", "¿Qué políticas aplican a ESTO? y asi.

retriever = MultiQueryRetriever.from_llm(
    retriever=retriever_base,
    llm=llm,
)



# 5. Cadena RAG

prompt_rag = ChatPromptTemplate(
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

document_chain = prompt_rag | llm | StrOutputParser()


def busqueda_de_respuesta_RAG(pregunta: str) -> Dict:
    """
    Recupera documentos con el MultiQueryRetriever (variantes de la
    pregunta) y genera la respuesta con document_chain.
    """
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



# 6. Estado del agente y nodos de LangGraph

class AgentState(TypedDict, total=False):
    pregunta: str
    triaje: dict
    respuesta: Optional[str]
    citaciones: Optional[list]
    rag_exito: bool
    accion_final: str


def nodo_triaje(state: AgentState) -> AgentState:
    print("nodo triaje.......")
    return {"triaje": triaje(state["pregunta"])}


def nodo_auto_resolver(state: AgentState) -> AgentState:
    print("nodo auto resolver.......")
    respuesta_RAG = busqueda_de_respuesta_RAG(state["pregunta"])

    update: AgentState = {
        "respuesta": respuesta_RAG["respuesta"],
        "citaciones": respuesta_RAG["citaciones"],
        "rag_exito": respuesta_RAG["documentos_encontrados"],
    }
    if respuesta_RAG["documentos_encontrados"]:
        update["accion_final"] = "AUTO_RESOLVER"

    return update


def nodo_pedir_info(state: AgentState) -> AgentState:
    print("Ejecutando nodo 'pedir_info'...")
    return {
        "respuesta": "Necesito más informaciones sobre tu pedido.",
        "citaciones": [],
        "accion_final": "PEDIR_INFO",
    }


def nodo_abrir_ticket(state: AgentState) -> AgentState:
    print("Ejecutando nodo 'abrir_ticket'...")
    tri = state["triaje"]
    return {
        "respuesta": f"Abrir ticket con urgencia {tri['urgencia']}. Pedido: {state['pregunta']}.",
        "citaciones": [],
        "accion_final": "ABRIR_TICKET",
    }


def arista_decision_triaje(state: AgentState) -> str:
    print("Ejecutando arista 'decision_triaje'...")
    tri = state["triaje"]
    if tri["decision"] == "CONSULTAR_RAG":
        return "rag"
    elif tri["decision"] == "PEDIR_MAS_INFORMACION":
        return "info"
    else:
        return "ticket"


def arista_decision_rag(state: AgentState) -> str:
    print("Ejecutando arista 'decision_rag'...")

    if state["rag_exito"]:
        print("rag exitoso")
        return "ok"

    KEYWORDS_ABRIR_TICKET = [
        "aprobación", "aprobar", "excepción", "liberación", "autorización",
        "autorizar", "abrir ticket", "acceso especial",
    ]

    if any(keyword in state["pregunta"].lower() for keyword in KEYWORDS_ABRIR_TICKET):
        print("Pregunta relacionada con abrir ticket, finalizando el flujo.")
        return "ticket"

    print("RAG ha fallado, pediré más informaciones al usuario.")
    return "info"



# 7. Construcción del grafo

workflow = StateGraph(AgentState)
workflow.add_node("triaje", nodo_triaje)
workflow.add_node("auto_resolver", nodo_auto_resolver)
workflow.add_node("pedir_info", nodo_pedir_info)
workflow.add_node("abrir_ticket", nodo_abrir_ticket)

workflow.add_edge(START, "triaje")
workflow.add_conditional_edges(
    "triaje",
    arista_decision_triaje,
    {
        "rag": "auto_resolver",
        "info": "pedir_info",
        "ticket": "abrir_ticket",
    },
)
workflow.add_conditional_edges(
    "auto_resolver",
    arista_decision_rag,
    {
        "info": "pedir_info",
        "ticket": "abrir_ticket",
        "ok": END,
    },
)
workflow.add_edge("pedir_info", END)
workflow.add_edge("abrir_ticket", END)

grafo = workflow.compile()


def guardar_diagrama_grafo(ruta_salida: str = "grafo_agente.png") -> None:
    """Guarda el diagrama del grafo como PNG."""
    try:
        graph_bytes = grafo.get_graph().draw_mermaid_png()
        with open(ruta_salida, "wb") as f:
            f.write(graph_bytes)
        print(f"Diagrama del grafo guardado en: {ruta_salida}")
    except Exception as e:
        print(f"No se pudo generar el diagrama (revisa tu conexión): {e}")



# 8. Ejecución

if __name__ == "__main__":
    guardar_diagrama_grafo()

    PREGUNTA = "Cuales son las politicas de sanciones economicas?"
    respuesta = grafo.invoke({"pregunta": PREGUNTA})

    print(f"Pregunta: {PREGUNTA}")
    print(f"Respuesta: {respuesta['respuesta']}")