# Reporte de Pruebas Automatizadas del Agente Alicorp

## Resumen Ejecutivo

| Métrica | Valor |
| :--- | :--- |
| **Casos ejecutados** | 4 |
| **Pasados** | 4 |
| **Fallidos** | 0 |
| **Tasa de éxito** | **100.0%** |

## Detalle de los Casos de Prueba

| # | Categoría | Pregunta | Acción Esperada | Acción Obtenida | Validación | Duración | Estado |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 38 | Triaje -> Abrir Ticket | Necesito pedir la liberación y desbloqueo de mi laptop personal bloqueada por seguridad de la información | `ABRIR_TICKET` | `ABRIR_TICKET` | No requiere validación adicional de RAG | 3.10s | **🟢 PASS** |
| 39 | Triaje -> Abrir Ticket | ¿Ante qué área pido una autorización para saltarme una regla de la política de ciberseguridad? | `ABRIR_TICKET` | `ABRIR_TICKET` | No requiere validación adicional de RAG | 3.01s | **🟢 PASS** |
| 40 | Triaje -> Abrir Ticket | Quiero abrir un ticket de soporte técnico para el canal de denuncias de ética | `ABRIR_TICKET` | `ABRIR_TICKET` | No requiere validación adicional de RAG | 3.05s | **🟢 PASS** |
| 41 | Memoria -> Sesión Regalos -> Turno 1 | ¿Cuál es el límite permitido para recibir un regalo de un proveedor? | `AUTO_RESOLVER` | `AUTO_RESOLVER` | Respuesta respaldada por 4 citación(es) | 8.34s | **🟢 PASS** |


## Respuestas del Agente

### Caso 38: Triaje -> Abrir Ticket

**Pregunta:** "Necesito pedir la liberación y desbloqueo de mi laptop personal bloqueada por seguridad de la información"

**Respuesta obtenida:**
> Clasificación de triaje: ABRIR_TICKET

**Validación:** No requiere validación adicional de RAG

---

### Caso 39: Triaje -> Abrir Ticket

**Pregunta:** "¿Ante qué área pido una autorización para saltarme una regla de la política de ciberseguridad?"

**Respuesta obtenida:**
> Clasificación de triaje: ABRIR_TICKET

**Validación:** No requiere validación adicional de RAG

---

### Caso 40: Triaje -> Abrir Ticket

**Pregunta:** "Quiero abrir un ticket de soporte técnico para el canal de denuncias de ética"

**Respuesta obtenida:**
> Clasificación de triaje: ABRIR_TICKET

**Validación:** No requiere validación adicional de RAG

---

### Caso 41: Memoria -> Sesión Regalos -> Turno 1

**Pregunta:** "¿Cuál es el límite permitido para recibir un regalo de un proveedor?"

**Respuesta obtenida:**
> El límite permitido para recibir un regalo de un proveedor es de US$10 (diez dólares americanos) o su equivalente en moneda local al tipo de cambio vigente. Estos regalos deben ser de valor modesto o simbólico, como lapiceros con logotipo, pequeña canasta de productos, trofeos, cuadernos de apunte y agendas.

**Validación:** Respuesta respaldada por 4 citación(es)

---

