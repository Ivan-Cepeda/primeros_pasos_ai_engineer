# L3 — Desafíos

Todos deben funcionar con ambos proveedores. En esta lección, además,
**todo lo que afirmes tiene que estar medido**.

---

## Desafío 1 — Reescribí un prompt malo
**Dificultad: baja** · *Se apoya en el ejercicio 01*

Partí de este prompt real y roto:

```
Mira este mail y decime que hago
```

Reescribilo aplicando los cinco ingredientes (rol, tarea, catálogo, formato,
bordes) para que clasifique correos internos en `RESPONDER_HOY`,
`RESPONDER_ESTA_SEMANA`, `DELEGAR`, `ARCHIVAR`.

Requisitos:
- Probá los dos prompts sobre los mismos 6 correos (escribilos vos, con al
  menos dos ambiguos).
- Corré cada uno 3 veces y contá cuántas respuestas distintas dio para la misma
  entrada.
- Entregá una tabla: prompt · exactitud · respuestas distintas por entrada.

---

## Desafío 2 — Extractor de estilo con few-shot
**Dificultad: media** · *Se apoya en el ejercicio 02*

Elegí un estilo de escritura difícil de describir con palabras (el tono de un
banco, el de una marca de skate, el de un parte médico) y armá un few-shot que
lo reproduzca.

Requisitos:
- Máximo 4 ejemplos.
- Compará la versión zero-shot ("escribí en tono formal de banco") contra la
  few-shot sobre 5 textos nuevos.
- Medí el costo extra en tokens de entrada de arrastrar los ejemplos.
- **Pregunta:** a partir de cuántas llamadas por mes convendría un fine-tuning
  en vez del few-shot? Estimalo con números reales de pricing.

---

## Desafío 3 — Chain-of-thought para reglas de negocio
**Dificultad: media** · *Se apoya en el ejercicio 03*

Implementá un calculador de comisiones de vendedores con estas reglas:

1. Comisión base: 3% sobre las ventas del mes.
2. Si superó la meta de USD 50.000 → 5% sobre **todo** el monto (no sólo el excedente).
3. Si tiene devoluciones por más del 10% de sus ventas → se le descuenta 1 punto.
4. Los vendedores con menos de 3 meses de antigüedad tienen un piso de USD 800.
5. Ninguna comisión puede superar los USD 8.000.

Requisitos:
- Resolvelo con las tres estrategias y compará la exactitud sobre 8 casos que
  hayas calculado a mano (incluí los que activan varias reglas a la vez).
- Salida en JSON con `razonamiento` (lista de pasos) y `comision_final`.
- **Pregunta incómoda:** si tenés las reglas escritas y son deterministas,
  ¿por qué usarías un LLM para esto? ¿En qué caso sí conviene?

---

## Desafío 4 — Ampliá el banco de pruebas
**Dificultad: media-alta** · *Se apoya en el ejercicio 04*

Tomá `04_banco_de_pruebas.py` y convertilo en una herramienta reutilizable:

- Los casos se leen de un `casos.json` externo, no del código.
- Los prompts a comparar se leen de una carpeta `prompts/`.
- Agregá una cuarta estrategia propia (por ejemplo, few-shot + CoT combinados).
- Reporte en formato tabla y export a CSV.
- Agregá **matriz de confusión**: no alcanza con saber que falló el 20%, hay que
  saber qué confundió con qué.

**Extensión:** corré la misma evaluación con OpenAI y con Gemini y comparalos.
¿La mejor estrategia es la misma para los dos modelos? Es una pregunta con
respuesta empírica, no teórica.

---

## Desafío 5 — Presupuesto de un producto real
**Dificultad: alta** · *Se apoya en el ejercicio 05*

Estimá el costo mensual de este producto:

> Un asistente de soporte para una empresa con 12.000 usuarios activos.
> El 15% usa el asistente al menos una vez por mes. Cada conversación tiene en
> promedio 6 turnos. El prompt de sistema tiene 800 tokens y hay un contexto de
> RAG de ~1.200 tokens por turno. Las respuestas promedian 180 tokens.

Requisitos:
- Calculalo para 3 modelos distintos (al menos uno de cada proveedor).
- Modelá el crecimiento del historial turno a turno; **no** asumas que cada
  turno cuesta lo mismo.
- Calculá el ahorro de: (a) recortar el historial a 3 turnos, (b) cachear el
  prompt de sistema, (c) usar un modelo más chico para clasificar la intención
  y sólo escalar al caro cuando hace falta.
- Entregá una tabla comparativa y una recomendación fundamentada.

**Pregunta final:** ¿cuál es el costo por usuario activo por mes? ¿Es viable
dentro del precio de tu producto?

---

## Desafío 6 — Ablación: borrá tu prompt y reconstruilo
**Dificultad: media-alta** · *Se apoya en los ejercicios 04 y 06*

En julio de 2026 el equipo de Claude Code contó que le borró **más del 80%** del
prompt de sistema a su producto y que el modelo no empeoró. Boris Cherny, su
creador, lo dijo en el escenario de Startup School un día después de que saliera
Opus 5: *"podés probar borrando el resto también"*.

La explicación: la mayoría de esas instrucciones existían para tapar debilidades
que los modelos nuevos ya no tienen. Y encima lo estorbaban.

Aplicá su método a un prompt tuyo.

1. Agarrá el prompt más largo que tengas (el de `01_zero_shot.py` sirve, o uno
   tuyo de otro proyecto).
2. Armá tu set de casos de prueba con la respuesta correcta — al menos 15,
   incluyendo los ambiguos. Sin esto no podés medir nada y el desafío no tiene
   sentido.
3. Medí el prompt completo: exactitud y tokens de entrada.
4. **Borralo entero.** Dejá solo la frase mínima que describe la tarea. Medí.
5. Agregá de vuelta **una instrucción por vez**. Medí después de cada una.
6. Quedate únicamente con las instrucciones que mejoraron un número.

Entregá una tabla: instrucción · exactitud antes · exactitud después · tokens
que cuesta · veredicto (se queda / se va).

**La parte incómoda:** vas a descubrir que varias instrucciones que escribiste
con convicción no mueven la aguja, y que alguna la empeora. Anotá cuáles y por
qué creés que pasó.

**Extensión:** repetí la medición con un modelo distinto. Las instrucciones que
sobreviven no son las mismas para todos los modelos — por eso la ablación se
rehace en cada cambio de modelo, no una vez y listo.
