# L2 — Bases técnicas para la integración de un LLM

De "le pregunté algo a un chatbot" a "tengo un modelo integrado en mi sistema".

## Ejercicios

| # | Archivo | Qué enseña |
|---|---------|------------|
| 01 | [`01_primer_llamado.py`](01_primer_llamado.py) | Credenciales, roles de mensaje, `usage`, `finish_reason` y por qué la "memoria" del chat la construís vos |
| 02 | [`02_parametros_de_generacion.py`](02_parametros_de_generacion.py) | `temperature` y `max_tokens`: cuándo querés variedad y cuándo querés que sea siempre igual |
| 03 | [`03_streaming_y_errores.py`](03_streaming_y_errores.py) | Streaming, tiempo hasta el primer texto, reintentos y qué errores **no** hay que reintentar |
| 04 | [`04_salida_estructurada.py`](04_salida_estructurada.py) | Pedir la respuesta en formato JSON y por qué siempre hay que validarla en Python |
| 05 | [`05_tool_calling.py`](05_tool_calling.py) | Function calling: el modelo propone, tu código ejecuta |
| 06 | [`06_comparar_proveedores.py`](06_comparar_proveedores.py) | La misma tarea con OpenAI y Gemini: calidad, latencia y tokens |

Cada uno se corre solo:

```bash
python 01_primer_llamado.py --provider gemini
```

## Ideas que hay que llevarse

**El modelo no recuerda nada.** Cada request es independiente. La conversación
existe porque vos reenviás el historial completo cada vez — y por eso el costo
de un chat largo crece más rápido de lo que uno espera (ejercicio 01 y L3-05).

**`temperature` es una decisión de producto.** Para clasificar querés 0. Para
generar nombres de campaña querés 1. No hay un valor "correcto" universal
(ejercicio 02).

**`max_tokens` trunca, no resume.** Si querés respuestas cortas, pedilas en el
prompt; `max_tokens` es el techo del costo, no un control de estilo (ejercicio 02).

**Streaming no acelera nada, pero cambia todo.** El tiempo total es el mismo; lo
que cambia es que el usuario ve texto en menos de un segundo en vez de mirar una
pantalla en blanco (ejercicio 03).

**Reintentá sólo lo que puede mejorar con el tiempo.** 429, 5xx y errores de red
sí. Un 401 o un 400 se van a repetir igual: reintentarlos quema cuota y esconde
el bug real (ejercicio 03).

**El formato correcto no garantiza el contenido correcto.** Que `presupuesto`
sea un número no significa que sea el número correcto. Las reglas de negocio se validan
en Python, que es determinista y testeable (ejercicio 04).

**En tool calling, el modelo nunca ejecuta nada.** Sólo dice qué le gustaría
ejecutar. Los permisos, la validación y la seguridad son 100% tuyos —y eso es una
buena noticia, porque es la única capa con garantías duras (ejercicio 05).

**Los tokens no son comparables entre proveedores.** Cada familia usa su propio
tokenizador; para comparar costos hay que mirar el precio por millón, no el
número crudo (ejercicio 06).

## Después de esto

Seguí con [`DESAFIOS.md`](DESAFIOS.md), y después con **L3**, donde se ve cómo
escribir el prompt que va adentro de toda esta maquinaria.
