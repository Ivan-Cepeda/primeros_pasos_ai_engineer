# L2 — Desafíos

Cinco consignas, de menor a mayor dificultad. Todas deben funcionar con
**ambos proveedores** sin cambios en el código.

---

## Desafío 1 — Traductor con detección de idioma
**Dificultad: baja** · *Se apoya en los ejercicios 01 y 04*

Escribí `desafio_1_traductor.py` que reciba un texto por línea de comandos y
devuelva un JSON con:

```json
{
  "idioma_detectado": "es",
  "traduccion_en": "...",
  "traduccion_pt": "...",
  "es_formal": true
}
```

Requisitos:
- `temperature=0` (es una tarea determinista).
- Si el texto ya está en inglés, `traduccion_en` debe repetirlo tal cual, no
  re-traducirlo.
- Validá en Python que las tres claves existan y que `idioma_detectado` sea un
  código ISO de dos letras.

**Pregunta para responder en un comentario:** ¿qué pasa si el texto de entrada
mezcla dos idiomas? Probalo y decidí qué debería hacer tu sistema.

---

## Desafío 2 — Chat con ventana deslizante
**Dificultad: media** · *Se apoya en el ejercicio 01*

Un chat que mantenga conversación pero **nunca supere N tokens de historial**.

- Estimá los tokens de cada mensaje (podés usar la función de L3-05).
- Cuando el historial supere el límite, eliminá los mensajes más viejos —pero
  **nunca** el mensaje `system`.
- Mostrá en cada turno cuántos tokens se están enviando.

**Extensión:** en vez de descartar los mensajes viejos, resumilos con una
llamada barata y reemplazalos por ese resumen. Compará el consumo de tokens de
las dos estrategias en una conversación de 15 turnos.

---

## Desafío 3 — Agente de viajes con herramientas
**Dificultad: media-alta** · *Se apoya en el ejercicio 05*

Construí un asistente con al menos cuatro herramientas:

1. `buscar_vuelos(origen, destino, fecha)` — datos simulados
2. `consultar_clima(ciudad, fecha)` — datos simulados
3. `convertir_moneda(monto, de, a)` — con tasas fijas
4. `reservar_vuelo(vuelo_id, pasajero)` — **acción con efecto secundario**

Requisitos:
- `reservar_vuelo` debe pedir confirmación explícita antes de ejecutarse.
  Pensá cómo implementarlo: ¿el modelo pregunta y vos leés la respuesta, o
  interceptás la tool call en tu código?
- Manejá el caso de la herramienta que falla (por ejemplo, sin vuelos
  disponibles) devolviéndole el error al modelo.
- Limitá a 5 turnos de tool calling y registrá cuántos usó cada consulta.

Probá con: *"Quiero volar a Bariloche el próximo viernes, decime cuánto sale en
euros y cómo va a estar el clima."*

---

## Desafío 4 — Router de modelos por costo
**Dificultad: alta** · *Se apoya en los ejercicios 02 y 06*

Un `RouterLLM` que elija automáticamente el modelo según la tarea:

- Clasificación y extracción → el modelo más barato disponible.
- Redacción y razonamiento → un modelo más capaz.
- Si el proveedor primario falla (429 o 5xx tres veces) → **fallback automático
  al otro proveedor**.

Requisitos:
- La decisión de ruteo tiene que estar en una tabla de configuración, no
  dispersa en `if`s.
- Registrá cada decisión: tarea, modelo elegido, motivo, costo estimado.
- Al final, un reporte: cuánto se gastó y cuánto se habría gastado usando
  siempre el modelo caro.

---

## Desafío 5 — Extractor de facturas resiliente
**Dificultad: alta** · *Integra 03, 04 y 05*

Procesá un lote de 5 textos de facturas (escribilos vos, con formatos distintos
y al menos uno deliberadamente incompleto) y produci un CSV normalizado.

Requisitos:
- Salida estructurada con schema, con degradación a `json_object` si el
  proveedor no lo soporta.
- Reintentos con backoff ante errores transitorios.
- Cada campo extraído lleva un nivel de confianza; los de confianza baja van a
  un archivo `revision_manual.csv` en vez del CSV principal.
- Ni una sola factura debe poder tirar abajo el proceso completo.
- Reporte final: procesadas, marcadas para revisión, fallidas, costo total.

**Pregunta:** si el 5% de las facturas necesita revisión humana, ¿el sistema
sigue siendo útil? ¿Y con 40%? ¿Dónde está tu umbral y por qué?
