# Implementación de tickets por correo

Este paquete fue preparado sobre la rama `Api-Agente`, commit base `80a29ef`.
Conserva el flujo `LISTAR_POLITICAS` y las optimizaciones de carga de FAISS.
La implementación usa un flujo sencillo para que sea fácil de estudiar y modificar.

## Archivos incluidos

- `Main.py`: agrega `POST /api/tickets`.
- `config.py`: lee la configuración SMTP.
- `grafo.py`: ofrece el formulario sin afirmar que el ticket ya fue enviado.
- `triaje.py`: diferencia una consulta sobre el procedimiento de una solicitud real.
- `tickets.py`: archivo nuevo; valida y envía el correo mediante SMTP.
- `frontend/src/App.jsx`: muestra el botón **Completar ticket**.
- `frontend/src/TicketPage.jsx`: archivo nuevo; contiene el formulario.
- `frontend/src/styles.css`: estilos del botón y del formulario.
- `.env.example`: ejemplo sin credenciales reales.

## Instalación

1. Haz una copia de seguridad de tu proyecto.
2. Extrae el ZIP dentro de la carpeta raíz `Backend` y permite reemplazar los
   archivos existentes.
3. No reemplaces tu `.env` con `.env.example`. Copia únicamente las variables
   SMTP y coloca tus valores reales.

## Correos utilizados

- `SMTP_USER`: cuenta técnica autenticada que envía el mensaje, por ejemplo
  `alicorp.tickets.demo@gmail.com`.
- `correo` del formulario: identifica al usuario y se coloca como encabezado
  `Reply-To`; si el receptor pulsa **Responder**, la respuesta se dirige allí.
- `TICKET_DESTINO`: buzón fijo que recibe todos los tickets.

Gmail no permite colocar como `From` una dirección escrita libremente en el
formulario sin autenticar esa cuenta. Por eso el remitente SMTP debe ser una
cuenta técnica controlada por la aplicación.

## Variables necesarias

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=correo.tecnico.remitente@gmail.com
SMTP_APP_PASSWORD=contraseña_de_aplicacion_sin_espacios
TICKET_DESTINO=correo.que.recibe.tickets@gmail.com
SMTP_TIMEOUT_SECONDS=30
```

Configura los mismos valores en **Render > Environment**. No subas claves ni
contraseñas a GitHub. Para Gmail utiliza una contraseña de aplicación, no la
contraseña normal de la cuenta.

## Validación

Desde la carpeta `Backend`:

```powershell
python -m py_compile Main.py tickets.py grafo.py triaje.py config.py
cd frontend
npm install
npm run build
cd ..
python Main.py
```

Prueba informativa; no debe mostrar el formulario:

```text
¿Cómo se debe registrar una denuncia por un intento de soborno?
```

Resultado esperado: `CONSULTAR_RAG`.

Prueba de gestión:

```text
Registra una denuncia porque un proveedor me ofreció dinero. Abre un ticket.
```

Resultado esperado: `ABRIR_TICKET` y botón **Completar ticket**. El correo solo
se envía después de completar el formulario y presionar **Enviar ticket**.

## Alcance

Esta versión genera un código y envía un correo, pero no guarda el ticket en una
base de datos. Para producción se recomienda añadir autenticación, persistencia
y protección contra envíos automatizados.
