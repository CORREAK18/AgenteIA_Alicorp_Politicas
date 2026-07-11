"""
grafo.py
========
Define el estado del agente (AgentState) y arma el grafo de LangGraph:
triaje -> (auto_resolver | pedir_info | abrir_ticket).

construir_grafo() recibe las piezas ya armadas (cadena de triaje, prompt de
triaje, retriever y document_chain) para no depender directamente de
providers.py ni de config.py — solo necesita objetos ya construidos.
"""

from typing import Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from busqueda_rag import busqueda_de_respuesta_rag
from triaje import triaje as ejecutar_triaje

KEYWORDS_ABRIR_TICKET = [
    "aprobación", "aprobar", "excepción", "liberación", "autorización",
    "autorizar", "abrir ticket", "acceso especial",
]


class AgentState(TypedDict, total=False):
    pregunta: str
    triaje: dict
    respuesta: Optional[str]
    citaciones: Optional[list]
    rag_exito: bool
    accion_final: str


def construir_grafo(cadena_triaje, prompt_triaje: str, retriever, document_chain):
    

    def nodo_triaje(state: AgentState) -> AgentState:
        print("nodo triaje.......")
        return {"triaje": ejecutar_triaje(state["pregunta"], cadena_triaje, prompt_triaje)}

    def nodo_auto_resolver(state: AgentState) -> AgentState:
        print("nodo auto resolver.......")
        respuesta_rag = busqueda_de_respuesta_rag(state["pregunta"], retriever, document_chain)

        update: AgentState = {
            "respuesta": respuesta_rag["respuesta"],
            "citaciones": respuesta_rag["citaciones"],
            "rag_exito": respuesta_rag["documentos_encontrados"],
        }
        if respuesta_rag["documentos_encontrados"]:
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

        if any(k in state["pregunta"].lower() for k in KEYWORDS_ABRIR_TICKET):
            print("Pregunta relacionada con abrir ticket, finalizando el flujo.")
            return "ticket"

        print("RAG ha fallado, pediré más informaciones al usuario.")
        return "info"

    workflow = StateGraph(AgentState)
    workflow.add_node("triaje", nodo_triaje)
    workflow.add_node("auto_resolver", nodo_auto_resolver)
    workflow.add_node("pedir_info", nodo_pedir_info)
    workflow.add_node("abrir_ticket", nodo_abrir_ticket)

    workflow.add_edge(START, "triaje")
    workflow.add_conditional_edges(
        "triaje",
        arista_decision_triaje,
        {"rag": "auto_resolver", "info": "pedir_info", "ticket": "abrir_ticket"},
    )
    workflow.add_conditional_edges(
        "auto_resolver",
        arista_decision_rag,
        {"info": "pedir_info", "ticket": "abrir_ticket", "ok": END},
    )
    workflow.add_edge("pedir_info", END)
    workflow.add_edge("abrir_ticket", END)

    return workflow.compile()


def guardar_diagrama_grafo(grafo, ruta_salida: str = "grafo_agente.png") -> None:
    """Guarda un PNG del grafo."""
    try:
        graph_bytes = grafo.get_graph().draw_mermaid_png()
        with open(ruta_salida, "wb") as f:
            f.write(graph_bytes)
        print(f"Diagrama del grafo guardado en: {ruta_salida}")
    except Exception as e:
        print(f"No se pudo generar el diagrama (revisa tu conexión): {e}")