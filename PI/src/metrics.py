"""
Persistencia de las metricas de cada ejecucion.

POR QUE SE GUARDAN EN ARCHIVO Y NO SOLO EN PANTALLA
  Una metrica que solo se imprime no sirve para nada al dia siguiente. Guardarlas
  permite responder preguntas concretas: cuanto gastamos esta semana, cuanto
  tarda el percentil 95, que consulta disparo el costo.

POR QUE DOS FORMATOS
  metrics.csv  -> se abre en cualquier planilla, es lo que pide la consigna y
                  es lo que va a mirar una persona.
  metrics.json -> una linea JSON por ejecucion, con mas detalle. Es el formato
                  que consumen las herramientas de monitoreo.

Los dos se escriben agregando al final, nunca reescribiendo: asi no se pierde
el historial y dos ejecuciones simultaneas no se pisan.
"""

import csv
import datetime
import json
import os

from src import safety


# Carpeta metrics/, que esta al lado de src/
CARPETA_DEL_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARPETA_METRICAS = os.path.join(CARPETA_DEL_PROYECTO, "metrics")

ARCHIVO_CSV = os.path.join(CARPETA_METRICAS, "metrics.csv")
ARCHIVO_JSON = os.path.join(CARPETA_METRICAS, "metrics.json")


# El orden de las columnas del CSV. Lo definimos una sola vez para que el
# encabezado y las filas no se puedan desincronizar.
COLUMNAS = [
    "timestamp",
    "provider",
    "model",
    "tokens_prompt",
    "tokens_completion",
    "tokens_reasoning",
    "total_tokens",
    "latency_ms",
    "estimated_cost_usd",
    "finish_reason",
    "retries",
    "valid_json",
    "requires_human",
    "confidence",
    "flagged_by_safety",
    "question_preview",
]


def _timestamp():
    """Fecha y hora en formato ISO 8601 y en UTC.

    Usamos UTC para que los registros de servidores en distintos paises se
    puedan comparar y ordenar sin ambiguedades.
    """
    ahora = datetime.datetime.now(datetime.timezone.utc)
    return ahora.isoformat(timespec="seconds")


def registrar(metricas, resultado, pregunta, marcada_por_seguridad):
    """
    Escribe una fila en el CSV y una linea en el JSON.

    Recibe las metricas tecnicas de la llamada y algunos datos del resultado,
    porque una metrica de costo sin el contexto de si la respuesta sirvio no
    permite tomar ninguna decision.
    """
    os.makedirs(CARPETA_METRICAS, exist_ok=True)

    # De la pregunta guardamos solo una muestra corta Y REDACTADA.
    #
    # Las dos cosas importan. La muestra corta evita que el archivo crezca sin
    # control. La redaccion evita un problema mas serio: los archivos de
    # metricas se copian, se respaldan y los abre mucha mas gente que la base
    # de datos. Un mail o una tarjeta que entra aca queda dando vueltas.
    #
    # Este bug estuvo en la primera version de este archivo: redactabamos los
    # datos antes de mandarlos al modelo, pero los escribiamos en claro en el
    # CSV. Redactar en un solo punto del flujo no alcanza.
    muestra, _ = safety.redactar_datos_personales(pregunta.replace("\n", " ")[:80])

    fila = {
        "timestamp": _timestamp(),
        "provider": metricas.get("proveedor", ""),
        "model": metricas.get("modelo", ""),
        "tokens_prompt": metricas.get("tokens_prompt", 0),
        "tokens_completion": metricas.get("tokens_completion", 0),
        "tokens_reasoning": metricas.get("tokens_reasoning", 0),
        "total_tokens": metricas.get("total_tokens", 0),
        "latency_ms": metricas.get("latency_ms", 0),
        "estimated_cost_usd": metricas.get("estimated_cost_usd", ""),
        "finish_reason": metricas.get("finish_reason", ""),
        "retries": metricas.get("intentos", 1),
        "valid_json": resultado.get("json_valido", False),
        "requires_human": resultado.get("requires_human", True),
        "confidence": resultado.get("confidence", 0.0),
        "flagged_by_safety": marcada_por_seguridad,
        "question_preview": muestra,
    }

    _escribir_csv(fila)
    _escribir_json(fila)

    return fila


def _escribir_csv(fila):
    """Agrega la fila al CSV, creando el encabezado si el archivo es nuevo."""

    archivo_es_nuevo = not os.path.exists(ARCHIVO_CSV)

    # newline="" es necesario en Windows para que el csv no meta lineas vacias.
    with open(ARCHIVO_CSV, "a", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS)

        if archivo_es_nuevo:
            escritor.writeheader()

        escritor.writerow(fila)


def _escribir_json(fila):
    """Agrega una linea JSON al archivo de metricas detalladas."""

    with open(ARCHIVO_JSON, "a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(fila, ensure_ascii=False) + "\n")


def leer_todas():
    """
    Lee el CSV y devuelve una lista de diccionarios.

    Devuelve lista vacia si todavia no se ejecuto nada.
    """
    if not os.path.exists(ARCHIVO_CSV):
        return []

    with open(ARCHIVO_CSV, "r", newline="", encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))


def resumir():
    """
    Calcula metricas agregadas a partir del CSV.

    Es lo que haria un tablero de monitoreo: leer los eventos y agrupar.
    Devuelve None si todavia no hay datos.
    """
    filas = leer_todas()

    if len(filas) == 0:
        return None

    latencias = []
    costo_total = 0.0
    tokens_totales = 0
    con_json_valido = 0
    marcadas_por_seguridad = 0

    for fila in filas:
        latencias.append(int(fila["latency_ms"]))
        tokens_totales = tokens_totales + int(fila["total_tokens"])

        # El costo puede venir vacio si no conociamos el precio del modelo.
        if fila["estimated_cost_usd"] not in ("", "None"):
            costo_total = costo_total + float(fila["estimated_cost_usd"])

        if fila["valid_json"] == "True":
            con_json_valido = con_json_valido + 1

        if fila["flagged_by_safety"] == "True":
            marcadas_por_seguridad = marcadas_por_seguridad + 1

    latencias.sort()

    # El percentil 95 es la latencia que sufre el 5% peor de los usuarios.
    # Se mira junto con la mediana porque el promedio esconde justamente a los
    # casos lentos, que son los que generan las quejas.
    posicion_p95 = int(len(latencias) * 0.95)
    if posicion_p95 >= len(latencias):
        posicion_p95 = len(latencias) - 1

    return {
        "ejecuciones": len(filas),
        "json_valido": con_json_valido,
        "porcentaje_json_valido": round(con_json_valido / len(filas) * 100, 1),
        "marcadas_por_seguridad": marcadas_por_seguridad,
        "latencia_mediana_ms": latencias[len(latencias) // 2],
        "latencia_p95_ms": latencias[posicion_p95],
        "tokens_totales": tokens_totales,
        "costo_total_usd": round(costo_total, 6),
        "costo_promedio_usd": round(costo_total / len(filas), 6),
    }
