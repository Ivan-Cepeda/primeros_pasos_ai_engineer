# L3 — El arte y la ciencia de la ingeniería de prompts

El arte es escribirlos. La ciencia es medirlos. Sin la segunda parte, "mejorar
un prompt" es una opinión.

## Ejercicios

| # | Archivo | Qué enseña |
|---|---------|------------|
| 01 | [`01_zero_shot.py`](01_zero_shot.py) | Zero-shot: la diferencia entre un prompt vago y uno de producción |
| 02 | [`02_few_shot.py`](02_few_shot.py) | Few-shot: enseñar con ejemplos, su costo y su riesgo de sesgo |
| 03 | [`03_chain_of_thought.py`](03_chain_of_thought.py) | Chain-of-thought: razonar paso a paso, y cómo hacerlo sin ensuciar la salida |
| 04 | [`04_banco_de_pruebas.py`](04_banco_de_pruebas.py) | Medir las tres estrategias sobre casos con respuesta conocida |
| 05 | [`05_tokens_y_costos.py`](05_tokens_y_costos.py) | Dónde encontrar el conteo de tokens y cómo estimar el costo real |
| 06 | [`06_modelos_de_razonamiento.py`](06_modelos_de_razonamiento.py) | **Qué cambió en 2026**: los tokens que pagás y no ves, la perilla de esfuerzo, y por qué "pensemos paso a paso" envejeció |

```bash
python 04_banco_de_pruebas.py --provider gemini --repeticiones 3
```

## Las tres estrategias

| Estrategia | Qué es | Cuándo usarla | Costo |
|------------|--------|---------------|-------|
| **Zero-shot** | Sólo la instrucción, sin ejemplos | Siempre lo primero que hay que probar | El más bajo |
| **Few-shot** | 2–5 ejemplos resueltos en el prompt | Formato propietario, tono específico, criterios con excepciones | Los ejemplos viajan en **cada** request |
| **Chain-of-thought** | Se pide razonar antes de responder | Cálculos, lógica multipaso, reglas encadenadas | Tokens de salida, los más caros |

## Ideas que hay que llevarse

**Cuando un zero-shot falla, casi nunca es culpa del modelo.** Los cinco
ingredientes que suelen faltar: rol, tarea de un solo verbo, catálogo de salidas
posibles, formato exacto, y qué hacer ante entradas ambiguas (ejercicio 01).

**Los ejemplos comunican lo que las palabras no.** Un formato propietario o un
tono de marca se muestran en tres ejemplos mejor que en tres párrafos de
instrucciones (ejercicio 02).

**Un few-shot mal armado empeora al modelo.** Si todos tus ejemplos son de la
misma clase, el modelo aprende esa clase, no la tarea. Balanceá siempre
(ejercicio 02).

**El orden importa en chain-of-thought.** Razonamiento *y después* respuesta. Al
revés el modelo ya se comprometió con un número y sólo lo justifica (ejercicio 03).

**En producción, el razonamiento va en un campo aparte.** JSON con
`razonamiento` y `respuesta`: el usuario ve una cosa, tu auditoría guarda la
otra (ejercicio 03).

**No existe la mejor estrategia; existe la mejor para tu tarea.** Y sólo se sabe
midiendo contra casos con respuesta conocida. Ese set de casos es el activo más
valioso que vas a construir (ejercicio 04).

**Los casos que fallan son información, no ruido.** Cada fallo te dice qué
criterio le falta al prompt (ejercicio 04).

**Los tokens de salida cuestan 4x los de entrada.** Por eso un chain-of-thought
verboso impacta el costo mucho más que agregar contexto (ejercicio 05).

**El costo de un chat crece de forma cuadrática.** Reenviás todo el historial en
cada turno. Recortalo, resumilo o cacheálo (ejercicio 05).

## Una advertencia importante sobre los modelos de 2026

Si estás usando un modelo de razonamiento (Gemini 3.x, GPT-6, Claude Opus 5),
`max_tokens` **no limita sólo lo que el modelo escribe**: limita el pensamiento
interno más la escritura, todo junto. Si le ponés un límite chico, el modelo lo
gasta pensando y te devuelve una respuesta vacía.

Los ejercicios ya vienen con márgenes amplios y avisan cuando esto pasa. El
ejercicio 06 lo mide en detalle.

## Después de esto

Seguí con [`DESAFIOS.md`](DESAFIOS.md). Son seis consignas. La número 4
—ampliar el banco de pruebas— es la que más se parece al trabajo real de un
AI Engineer, y la número 6 —borrar tu prompt y reconstruirlo midiendo— es el
método que usa el equipo de Claude Code en cada cambio de modelo.

Después seguí con **L4 — Seguridad y ética de la IA**, que es donde todo esto
se convierte en un sistema que se puede poner en producción.
