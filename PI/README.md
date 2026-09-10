# Multitasking Text Utility — Asistente para agentes de soporte

Proyecto Integrador del Módulo 1 de AI Engineering.

Recibe la consulta de un cliente y devuelve un **JSON estructurado** con la
respuesta sugerida, un nivel de confianza y las acciones recomendadas, para que
un sistema downstream lo consuma sin transformaciones. Registra **tokens,
latencia y costo estimado** de cada ejecución.

---

## Puesta en marcha

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

> En Linux o macOS: `source .venv/bin/activate`

```bash
pip install -r requirements.txt
```

Copiá el archivo de ejemplo y completá tu clave:

```bash
copy .env.example .env
```

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=tu-clave-aca
```

- Clave de OpenAI: https://platform.openai.com/api-keys
- Clave de Gemini (alternativa con capa gratuita): https://aistudio.google.com/apikey

---

## Cómo se ejecuta

```bash
python -m src.run_query "Compre un monitor y llego con un pixel muerto. Puedo cambiarlo?"
```

Salida:

```json
{
  "answer": "El monitor esta dentro del periodo para reclamos por falla de fabrica. Pedile al cliente una foto del pixel y el comprobante de compra.",
  "confidence": 0.90,
  "actions": ["responder_directo", "abrir_ticket_tecnico"],
  "category": "producto",
  "requires_human": false
}
```

El JSON sale por **stdout** y todo lo informativo por **stderr**, así se puede
redirigir a un archivo o encadenar con otro programa sin que se mezcle:

```bash
python -m src.run_query "mi consulta" > respuesta.json
```

Otras opciones:

| Comando | Qué hace |
|---------|----------|
| `python -m src.run_query --resumen` | Métricas acumuladas de todas las ejecuciones |
| `python -m src.run_query "..." --provider gemini` | Fuerza el proveedor |
| `python -m src.run_query "..." --model gpt-4o` | Fuerza el modelo |
| `python -m src.run_query "..." --sin-seguridad` | Saltea la capa de seguridad (para comparar) |
| `python -m src.run_query "..." --sin-metricas` | No registra esta ejecución |

Sin argumento, pide la consulta por teclado.

---

## Tests

```bash
python -m pytest tests/ -v
```

O sin instalar pytest:

```bash
python tests/test_core.py
```

Son **21 tests** y cubren parseo de JSON, validación del contrato, reglas de
negocio, cálculo de costo y las tres capas de seguridad. Ninguno llama a la
API: corren en segundos, gratis y sin conexión.

---

## Estructura

```
PI/
├── src/
│   ├── run_query.py     Punto de entrada: orquesta los 7 pasos del flujo
│   ├── config.py        Credenciales y parámetros de la llamada
│   ├── llm_client.py    Conexión, reintentos y medición
│   ├── schema.py        El contrato JSON y su validación
│   ├── safety.py        Capa de seguridad (bonus)
│   └── metrics.py       Persistencia de métricas en CSV y JSON
├── prompts/
│   └── main_prompt.txt  La plantilla del prompt, con los ejemplos few-shot
├── metrics/
│   ├── metrics.csv      Una fila por ejecución
│   └── metrics.json     Una línea JSON por ejecución, con más detalle
├── reports/
│   └── PI_report_en.md  Informe: arquitectura, prompting, métricas, trade-offs
├── tests/
│   └── test_core.py     21 tests
├── .env.example
└── requirements.txt
```

Cada archivo de `src/` tiene **una responsabilidad**. El prompt vive fuera del
código porque se itera: cambiarlo no debería requerir tocar Python, y su
historial de cambios se ve en git como el de cualquier archivo.

---

## El flujo, paso a paso

```
consulta del usuario
  → 1. seguridad de entrada     patrones de manipulación y datos personales
  → 2. armado del prompt        plantilla + few-shot + contrato
  → 3. llamada al modelo        con timeout y reintentos con backoff
  → 4. parseo y validación      nunca confiamos en que el JSON esté bien
  → 5. reglas de negocio        umbral de confianza → revisión humana
  → 6. seguridad de salida      que no se filtren las instrucciones
  → 7. registro de métricas     CSV + JSON
JSON válido por stdout
```

Cualquier paso puede cortar el flujo, pero **la salida siempre respeta el
contrato**: quien nos consume recibe los mismos cinco campos pase lo que pase.
Cuando algo falla, cambia el contenido, no la forma.

---

## El contrato de salida

| Campo | Tipo | Qué es |
|-------|------|--------|
| `answer` | string | La respuesta para el agente. Máximo 3 oraciones |
| `confidence` | number 0.0–1.0 | Qué tan seguro está el modelo |
| `actions` | array | Una o más de una lista cerrada de 5 acciones |
| `category` | string | Una de: facturacion, tecnico, cuenta, producto, otro |
| `requires_human` | boolean | Si una persona tiene que revisar antes de responder |

Las listas cerradas convierten texto libre en valores que el código puede
comparar con `==`. Esa es la diferencia entre un dato y una frase.

**Validamos en Python, no confiamos en el modelo.** Un `confidence` de 3.7 es
JSON perfectamente válido y a la vez imposible: la forma la garantiza el
modelo, la coherencia la garantiza `schema.py`.

---

## Decisiones técnicas

Están justificadas en detalle en [`reports/PI_report_en.md`](reports/PI_report_en.md).
El resumen:

**Técnica de prompting: few-shot con 4 ejemplos.** Elegida porque el formato de
salida es propietario y porque los casos límite —una consulta vacía, un cliente
enojado, un intento de manipulación— se muestran mejor de lo que se explican.
Está documentada la comparación contra zero-shot.

**`temperature=0`.** La tarea es clasificar y estructurar, no redactar. La misma
consulta debe devolver siempre lo mismo, porque el resultado alimenta a otros
sistemas.

**`max_tokens=1200`, que parece mucho.** Los modelos de razonamiento gastan
tokens *pensando* antes de escribir, y `max_tokens` limita pensamiento más
respuesta juntos. Con un valor chico el modelo se queda sin margen y devuelve
texto vacío.

**El costo suma los tokens de razonamiento.** No aparecen en la respuesta pero
se facturan, y al precio de salida, que es el caro. Se deducen restando entrada
y salida visible del total. Sin sumarlos, el costo calculado da hasta 7 veces
menos que el real.

---

## Sobre el proveedor

La consigna pide usar la API de OpenAI. Este proyecto la soporta y es el valor
por defecto en `.env.example`.

Además funciona con **Google Gemini sin cambiar una línea de código**, porque el
SDK `openai` no está atado a OpenAI: es un cliente del protocolo
`/chat/completions`, y Google publica ese mismo protocolo en una URL de
compatibilidad. Cambia `base_url` y la clave, nada más.

Se agregó por dos razones: Gemini tiene capa gratuita, y desacoplar el
proveedor convierte un cambio de modelo de un refactor en una variable de
entorno.

Diferencias a tener presentes:

| | OpenAI | Gemini |
|---|---|---|
| Chat completions, streaming, JSON | ✅ | ✅ |
| Endpoint `/moderations` | ✅ | ❌ *(por eso la moderación es propia)* |
| Conteo local con `tiktoken` | ✅ | ❌ *(tokenizador propio)* |

---

## Credenciales

**Ninguna clave se escribe nunca en el código.** Viven en `.env`, que está en
`.gitignore`. Lo que se versiona es `.env.example`, con los nombres de las
variables pero sin valores. En producción las inyecta el servidor y el código
no cambia.

---

## Limitaciones conocidas

Es un MVP. Lo que **no** hace, y conviene saberlo antes de usarlo en serio:

- **No tiene base de conocimiento.** Responde con el conocimiento general del
  modelo, no con las políticas reales de una empresa. El siguiente paso natural
  es RAG: recuperar el fragmento de política que corresponda y pasárselo.
- **`confidence` es una autoevaluación del modelo**, no una probabilidad
  calibrada. Sirve para ordenar casos por prioridad, no como medida estadística.
  Por eso hay un umbral fijo encima.
- **El rate limit no existe.** Un uso intensivo puede gastar el presupuesto sin
  freno.
- **Las métricas están en archivos locales.** Con varias instancias corriendo a
  la vez habría que mandarlas a un almacén compartido.
- **La detección de patrones adversariales es una lista de frases.** No para a
  un atacante creativo. Su valor real es que te enteres del intento, no que lo
  bloquee.
- **Los precios cambian.** Los de Gemini 3.6/3.7/3.8 son promocionales hasta el
  31/12/2026 y después se duplican.

---

## Reproducir las métricas del informe

```bash
python -m src.run_query "Compre un monitor hace 10 dias y llego con un pixel muerto. Puedo cambiarlo?"
```

```bash
python -m src.run_query --resumen
```

Los números del informe salieron de cinco ejecuciones así, con
`gemini-3.7-flash`. Van a variar según el modelo y el momento.
