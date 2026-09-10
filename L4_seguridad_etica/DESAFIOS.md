# L4 — Desafíos

En esta lección los desafíos tienen una regla extra: **todo lo que construyas
tiene que fallar de forma segura.** Si tu solución se rompe, tiene que romperse
del lado de bloquear, no del lado de dejar pasar.

---

## Desafío 1 — Detector de alucinaciones con fuentes
**Dificultad: media** · *Se apoya en el ejercicio 01*

Armá un asistente que responda **sólo** sobre una base de conocimiento que vos
le des (10–15 párrafos sobre cualquier tema), y que cite la fuente de cada
afirmación.

Requisitos:
- Cada afirmación lleva el identificador del párrafo que la respalda.
- Una segunda llamada al modelo verifica: *"¿esta afirmación está realmente
  contenida en el párrafo citado?"* (esto se llama *LLM-as-a-judge*).
- Si el verificador dice que no, la respuesta se marca como no confiable.
- Probalo con 5 preguntas respondibles y 5 que **no** estén en la base.

**Métrica a reportar:** de las 5 preguntas sin respuesta en la base, ¿en cuántas
el sistema admitió no saber? Ése es tu número, no la calidad de la prosa.

---

## Desafío 2 — Auditoría de sesgo
**Dificultad: media** · *Se apoya en el ejercicio 01*

Construí un test automatizado que detecte sesgo por sustitución controlada.

Requisitos:
- Un mismo prompt con un único atributo que varía (nombre asociado a distinto
  género u origen, edad, ciudad).
- 20 pares como mínimo, y 3 corridas de cada uno.
- Compará las salidas del par: longitud, adjetivos usados, recomendación final.
- Reporte: en qué porcentaje de los pares la salida cambió de forma
  significativa, y en qué dirección.

**Pregunta:** ¿cómo definís "cambió de forma significativa" sin que sea tu
opinión? Escribí el criterio antes de correr el test, no después.

---

## Desafío 3 — Moderador con umbrales aprendidos
**Dificultad: media-alta** · *Se apoya en el ejercicio 02*

Extendé el middleware de moderación:

- Armá un set de 30 mensajes etiquetados a mano (`PERMITIR` / `REVISAR` /
  `BLOQUEAR`), con casos límite reales.
- Corré el moderador con distintos umbrales y calculá, para cada configuración,
  falsos positivos y falsos negativos.
- Elegí los umbrales que minimicen los falsos negativos **de la categoría
  `autolesion`**, aun a costa de más falsos positivos en el resto.
- Justificá la elección por escrito.

**Lo que importa acá:** entender que elegir un umbral es elegir qué error
preferís cometer. No existe una configuración sin errores.

---

## Desafío 4 — Torneo de inyecciones
**Dificultad: alta** · *Se apoya en el ejercicio 04*

En parejas (o contra vos mismo, en dos sesiones separadas):

1. **Defensa:** escribí un prompt de sistema que guarde un secreto y un
   pipeline con validación de salida.
2. **Ataque:** conseguí que el secreto salga. Documentá cada intento, funcione o no.
3. Iterá tres rondas: la defensa se refuerza con lo aprendido del ataque.

Entregá:
- La bitácora completa de los intentos (los fallidos también son datos).
- La versión final de la defensa.
- **La conclusión honesta:** ¿lograste una defensa impenetrable? Si creés que
  sí, seguí atacando 20 minutos más.

**Regla que hay que descubrir sola:** el secreto no debería haber estado nunca
en el prompt.

---

## Desafío 5 — API de producción
**Dificultad: alta** · *Integra todo el módulo*

Envolvé `05_pipeline_seguro.py` en una API HTTP real (FastAPI o Flask).

Requisitos mínimos:
- `POST /chat` con `{usuario_id, mensaje}` → respuesta + `trace_id`.
- `GET /health` que verifique que el proveedor de LLM responde.
- `GET /metrics` con: llamadas, tasa de error, latencia p50/p95, costo acumulado.
- Rate limit por usuario **y** global.
- Streaming vía Server-Sent Events en `POST /chat/stream`.
- El proveedor se elige por variable de entorno, y hay fallback automático al
  otro si el primario falla.
- Ni un solo secreto en el código ni en el repositorio.

**Prueba de fuego:** entregale la URL a un compañero sin explicarle nada y
pedile que intente romperla. Después revisá tus logs: ¿podés reconstruir
exactamente qué hizo? Si no podés, tu telemetría no alcanza.

---

## Cierre del módulo

Si terminaste estos cinco, sabés hacer las tres cosas que separan un demo de un
producto:

1. **Integrar** un modelo sin atarte a un proveedor.
2. **Medir** si un cambio mejoró algo, en vez de suponerlo.
3. **Contener** lo que puede salir mal, antes de que salga mal.
