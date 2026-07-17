
# memoria.py

# Funciones (llamadas desde Main.py):
#   - obtener_historial()  → devuelve los mensajes anteriores de una sesión
#   - guardar_turno()      → guarda un par pregunta+respuesta en el historial
#   - borrar_historial()   → elimina el historial de una sesión
#   - condensar_pregunta() → reformula la pregunta nueva usando el historial


from threading import Lock
from typing import Dict, List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage


MAX_MENSAJES = 4

# Almacén en RAM: { thread_id: [{role, content}, ...] }
_historiales: Dict[str, List[Dict[str, str]]] = {}

# Un lock por sesión para no mezclar mensajes de la misma conversación
_locks_por_thread: Dict[str, Lock] = {}

# Lock auxiliar solo para crear nuevas entradas en el diccionario anterior
_lock_creacion = Lock()


def obtener_lock(thread_id: str) -> Lock:
    """Devuelve el lock de una sesión, creándolo si no existe."""
    with _lock_creacion:
        return _locks_por_thread.setdefault(thread_id, Lock())


def obtener_historial(thread_id: str) -> List[Dict[str, str]]:
    """Devuelve los mensajes anteriores de una sesión. Lista vacía si no existe."""
    return _historiales.get(thread_id, [])


def guardar_turno(thread_id: str, pregunta_original: str, respuesta: str) -> None:
    """Agrega un par pregunta+respuesta al historial y descarta los más viejos si supera el límite."""
    historial = _historiales.setdefault(thread_id, [])

    historial.append({"role": "user",      "content": pregunta_original})
    historial.append({"role": "assistant", "content": respuesta})

    limite = MAX_MENSAJES * 2
    if len(historial) > limite:
        _historiales[thread_id] = historial[-limite:]


def borrar_historial(thread_id: str) -> None:
    """Elimina el historial de una sesión por completo."""
    _historiales.pop(thread_id, None)
    with _lock_creacion:
        _locks_por_thread.pop(thread_id, None)


def condensar_pregunta(
    pregunta_nueva: str,
    historial: List[Dict[str, str]],
    llm: BaseChatModel,
) -> str:
    """
    Reformula la pregunta usando el historial para que sea autónoma.
    Si no hay historial, la devuelve sin cambios.
    """
    if not historial:
        return pregunta_nueva

    historial_texto = "\n".join(
        f"{'Usuario' if m['role'] == 'user' else 'Asistente'}: {m['content']}"
        for m in historial
    )

    prompt_condensacion = (
        "Dado el siguiente historial de conversación y una nueva pregunta del usuario, "
        "reformula la nueva pregunta como una pregunta informativa e independiente sobre "
        "las políticas corporativas de Alicorp, incorporando el contexto necesario del historial. "
        "La pregunta reformulada DEBE ser una consulta de información (¿Qué dice la política sobre...?, "
        "¿Cuáles son las normas de...?, etc.), NUNCA una solicitud de acción o autorización. "
        "Si la nueva pregunta ya es completamente independiente e informativa, devuélvela tal cual. "
        "Devuelve SOLO la pregunta reformulada, sin explicaciones adicionales.\n\n"
        f"Historial de conversación:\n{historial_texto}\n\n"
        f"Nueva pregunta: {pregunta_nueva}\n\n"
        "Pregunta reformulada:"
    )

    respuesta = llm.invoke(
        [
            SystemMessage(content="Eres un asistente que reformula preguntas para facilitar la búsqueda de información."),
            HumanMessage(content=prompt_condensacion),
        ]
    )

    pregunta_condensada = respuesta.content.strip()
    print(f"[Memoria] Pregunta original  : '{pregunta_nueva}'")
    print(f"[Memoria] Pregunta condensada: '{pregunta_condensada}'")
    return pregunta_condensada
