# L4 — Seguridad y ética de la IA

La diferencia entre un prototipo y un producto es casi toda esta lección.

## Ejercicios

| # | Archivo | Qué enseña |
|---|---------|------------|
| 01 | [`01_modos_de_fallo.py`](01_modos_de_fallo.py) | Los cuatro fallos típicos —alucinación, sesgo, desactualización, exceso de confianza— provocados a propósito, con su mitigación |
| 02 | [`02_middleware_moderacion.py`](02_middleware_moderacion.py) | Middleware de moderación con umbrales configurables, en dos backends intercambiables |
| 03 | [`03_logging_estructurado.py`](03_logging_estructurado.py) | Logging JSON, redacción de PII, métricas de costo y latencia |
| 04 | [`04_prompt_injection.py`](04_prompt_injection.py) | Inyección directa e indirecta, y las defensas que realmente funcionan |
| 05 | [`05_pipeline_seguro.py`](05_pipeline_seguro.py) | Todo junto: rate limit → filtros → moderación → LLM → validación → telemetría |

```bash
python 05_pipeline_seguro.py --provider gemini
```

Los ejercicios 03 y 05 escriben en `../logs/` (carpeta ignorada por git).

### Si usás un modelo de razonamiento

`max_tokens` limita el pensamiento interno **más** la respuesta. Los ejercicios
de L4 ya vienen con márgenes amplios porque varios dependen de que el modelo
devuelva un JSON completo: si se corta, el moderador falla. Ver
[L3/06](../L3_prompt_engineering/06_modelos_de_razonamiento.py).

## Nota sobre portabilidad

OpenAI ofrece `/moderations`: un endpoint especializado, gratuito y bien
calibrado. Gemini no tiene equivalente en su API compatible.

El ejercicio 02 implementa los dos caminos detrás de la misma interfaz
(`Protocol` de Python) y elige automáticamente el disponible. Es un buen ejemplo
de cómo se aísla una diferencia entre proveedores sin contaminar el resto del
sistema: el código que llama al moderador no sabe cuál está usando.

## Ideas que hay que llevarse

**El modelo optimiza por respuestas plausibles, no por respuestas verdaderas.**
La verdad la aporta tu arquitectura: fuentes, herramientas, validación
(ejercicio 01).

**Dale permiso explícito de no saber.** Sin una instrucción como *"si no está en
las políticas, decí que no lo sabés"*, el modelo interpreta que su trabajo es
responder siempre —y entonces inventa (ejercicio 01).

**Contra el sesgo, la mitigación más robusta no es pedirle que sea justo: es no
darle el dato.** Lo que el modelo no ve, no lo puede usar (ejercicio 01).

**Tres estados de moderación, no dos.** Bloquear todo lo dudoso arruina la
experiencia; dejar pasar todo arruina la confianza. `REVISAR` es la válvula que
te permite mover los umbrales con datos reales (ejercicio 02).

**Los umbrales van fuera del código.** Son política de producto y de riesgo, no
lógica de programación: tienen que poder cambiarse sin un deploy (ejercicio 02).

**Moderá también la salida.** Un prompt inofensivo puede producir una respuesta
problemática, y el que queda expuesto es tu producto (ejercicio 02).

**Un `print()` no es observabilidad.** Una línea JSON por evento, con `trace_id`,
tokens, costo y latencia. Sin eso no podés saber si algo se rompió, cuánto
gastaste ni por qué se quejó un usuario (ejercicio 03).

**Mirá el p95, no el promedio.** La mediana esconde la cola de usuarios lentos,
que es justamente la que genera las quejas (ejercicio 03).

**Redactá la PII antes de escribir el log.** Los logs se replican, se respaldan y
los lee mucha más gente que la base de datos (ejercicio 03).

**No existe un prompt de sistema a prueba de inyecciones.** Todas las defensas
basadas en texto son probabilísticas: suben el costo del ataque, no lo eliminan
(ejercicio 04).

**Los ataques de manual ya no funcionan — y eso es una trampa.** Corriendo el
ejercicio 04 contra un modelo de 2026 vas a ver que los cuatro ataques clásicos
rebotan, y que el agente con herramientas ignora la instrucción escondida. No
resistió *tu* sistema: resistió el modelo. Esa defensa la puso el proveedor, no
vos, y puede cambiar en la próxima versión o desaparecer si migrás a un modelo
más barato (ejercicio 04, partes 1 y 4).

**La defensa real es arquitectónica.** Si el asistente no tiene la herramienta
para transferir plata, ninguna inyección va a transferir plata. Es la única
mitigación con garantía dura (ejercicio 04).

**Nada de secretos en el prompt de sistema.** Todo lo que entra al contexto es
potencialmente extraíble (ejercicio 04).

**Las capas baratas van primero.** Cada consulta bloqueada por el rate limit o
por un filtro de patrones es una llamada al modelo que no se paga (ejercicio 05).

**El falso positivo es el error más caro.** La primera versión del ejercicio 05
bloqueaba la respuesta legítima "tenés 30 días para devolver" porque el
validador prohibía la cadena `POL-0` — justo el código de política que el
asistente debe citar. Rompía la experiencia de los usuarios honestos, que son
casi todos, para defenderse de un atacante que quizás ni aparezca. El comentario
del código lo explica en detalle (ejercicio 05).

## La pregunta que hay que hacerse siempre

No es *"¿puede el modelo decir algo feo?"*.

Es: **"¿qué es lo peor que pasa si el modelo hace exactamente lo que el atacante
quiere?"**

Si la respuesta involucra plata, datos de terceros o infraestructura, el problema
no está en el prompt: está en los permisos que le diste al agente.

## Después de esto

Seguí con [`DESAFIOS.md`](DESAFIOS.md).
