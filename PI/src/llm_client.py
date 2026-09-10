"""
La conexion con el modelo y la medicion de cada llamada.

Este archivo tiene una sola responsabilidad: hacer la llamada y devolver, junto
con el texto, todo lo que hace falta para monitorearla (tokens, latencia y
costo). Quien lo usa no necesita saber con que proveedor esta hablando.
"""

import time

from openai import (APIConnectionError, APIStatusError, APITimeoutError,
                    OpenAI, RateLimitError)

from src import config


# ---------------------------------------------------------------------------
# Precios en dolares por MILLON de tokens.
#
# Verificados en las paginas oficiales de cada proveedor en septiembre de 2026.
#
# AVISO QUE HAY QUE TENER PRESENTE: los modelos Gemini 3.6, 3.7 y 3.8 estan con
# precio promocional de lanzamiento hasta el 31/12/2026. Desde el 1/1/2027 la
# entrada pasa de 0.75 a 1.50 y la salida de 3.75 a 7.50: el doble. Cualquier
# presupuesto anual armado con estos numeros hay que rehacerlo en enero.
# ---------------------------------------------------------------------------
PRECIOS = {
    "gpt-4o-mini":           {"entrada":  0.15, "salida":  0.60},
    "gpt-5.6-luna":          {"entrada":  0.20, "salida":  1.20},
    "gpt-6-astra":           {"entrada": 10.00, "salida": 50.00},
    "gemini-2.5-flash":      {"entrada":  0.30, "salida":  2.50},
    "gemini-2.5-pro":        {"entrada":  1.25, "salida": 10.00},
    "gemini-3.1-flash-lite": {"entrada":  0.25, "salida":  1.50},
    "gemini-3.5-flash-lite": {"entrada":  0.30, "salida":  2.50},
    "gemini-3.5-flash":      {"entrada":  1.50, "salida":  9.00},
    "gemini-3.6-flash":      {"entrada":  0.75, "salida":  3.75},
    "gemini-3.7-flash":      {"entrada":  0.75, "salida":  3.75},
    "gemini-3.8-flash":      {"entrada":  0.75, "salida":  3.75},
}


class ErrorDelModelo(Exception):
    """Se lanza cuando la llamada falla despues de agotar los reintentos."""


def crear_cliente(proveedor=None, modelo=None):
    """
    Prepara la conexion y devuelve un diccionario con lo necesario para usarla.

    Devolvemos un diccionario simple en vez de un objeto elaborado: adentro hay
    solo tres cosas y conviene que se vean.
    """
    datos = config.cargar_configuracion(proveedor, modelo)

    conexion = OpenAI(
        api_key=datos["clave"],
        base_url=datos["base_url"],
        timeout=config.TIMEOUT_SEGUNDOS,
    )

    return {
        "api": conexion,
        "modelo": datos["modelo"],
        "proveedor": datos["proveedor"],
        "clave": datos["clave"],
    }


def calcular_costo(modelo, tokens_entrada, tokens_salida, tokens_de_razonamiento=0):
    """
    Calcula el costo en dolares de una llamada.

    EL DETALLE QUE CASI TODOS SE PIERDEN
    ------------------------------------
    Los modelos de razonamiento generan tokens "pensando" que no aparecen en la
    respuesta pero SI se facturan, y al precio de salida, que es el caro.

    No vienen en un campo propio: se deducen restando entrada y salida visible
    del total. Si no los sumas, tu tablero de costos te miente. Medido en este
    mismo proyecto con gemini-3.7-flash, la diferencia fue de 7 veces.

    Devuelve None si no conocemos el precio de ese modelo, para no inventar un
    numero que despues alguien use para presupuestar.
    """
    if modelo not in PRECIOS:
        return None

    precio = PRECIOS[modelo]

    # Todo lo que el modelo genero se factura como salida: lo que escribio en
    # pantalla mas lo que penso por dentro.
    salida_facturada = tokens_salida + tokens_de_razonamiento

    costo = (tokens_entrada / 1000000 * precio["entrada"] +
             salida_facturada / 1000000 * precio["salida"])

    return round(costo, 8)


def preguntar(cliente, mensajes):
    """
    Hace la llamada al modelo y devuelve el texto junto con sus metricas.

    Reintenta ante errores pasajeros con espera creciente (backoff). NO
    reintenta los errores 4xx que no son 429, porque un pedido mal armado o una
    clave invalida van a fallar igual: reintentarlos solo quema cuota y esconde
    el problema real.

    Devuelve (texto, metricas). Lanza ErrorDelModelo si se agotan los intentos.
    """
    intento = 1
    ultimo_error = ""

    while intento <= config.REINTENTOS:

        momento_inicial = time.time()

        try:
            respuesta = cliente["api"].chat.completions.create(
                model=cliente["modelo"],
                messages=mensajes,
                temperature=config.TEMPERATURA,
                max_tokens=config.MAX_TOKENS,
                response_format={"type": "json_object"},
            )

            latencia_ms = round((time.time() - momento_inicial) * 1000)

            uso = respuesta.usage
            tokens_entrada = uso.prompt_tokens
            tokens_salida = uso.completion_tokens

            # Los tokens de razonamiento se deducen restando.
            razonamiento = uso.total_tokens - tokens_entrada - tokens_salida
            if razonamiento < 0:
                razonamiento = 0

            texto = respuesta.choices[0].message.content
            if texto is None:
                texto = ""

            metricas = {
                "proveedor": cliente["proveedor"],
                "modelo": cliente["modelo"],
                "tokens_prompt": tokens_entrada,
                "tokens_completion": tokens_salida,
                "tokens_reasoning": razonamiento,
                "total_tokens": uso.total_tokens,
                "latency_ms": latencia_ms,
                "estimated_cost_usd": calcular_costo(
                    cliente["modelo"], tokens_entrada, tokens_salida, razonamiento
                ),
                "finish_reason": respuesta.choices[0].finish_reason,
                "intentos": intento,
            }

            # Si la respuesta vino vacia porque se acabo el presupuesto de
            # tokens, avisamos con un mensaje que explica que hacer. Sin esto,
            # el sintoma es una linea en blanco imposible de diagnosticar.
            if texto == "" and metricas["finish_reason"] == "length":
                raise ErrorDelModelo(
                    "El modelo agoto max_tokens (" + str(config.MAX_TOKENS) + ") "
                    "razonando y no alcanzo a escribir la respuesta. "
                    "Subi MAX_TOKENS en src/config.py."
                )

            return texto, metricas

        except (RateLimitError, APITimeoutError, APIConnectionError) as error:
            # Errores que pueden mejorar solos: esperamos y reintentamos.
            ultimo_error = type(error).__name__
            espera = 2 ** intento      # 2, 4, 8 segundos
            print("  [reintento " + str(intento) + "/" + str(config.REINTENTOS) +
                  "] " + ultimo_error + ", espero " + str(espera) + "s")
            time.sleep(espera)

        except APIStatusError as error:
            # 4xx que no sea 429: el pedido esta mal, no tiene sentido insistir.
            if 400 <= error.status_code < 500 and error.status_code != 429:
                raise ErrorDelModelo(
                    "Error " + str(error.status_code) + " del proveedor. "
                    "Revisa la clave o el nombre del modelo."
                )

            ultimo_error = "HTTP " + str(error.status_code)
            espera = 2 ** intento
            print("  [reintento " + str(intento) + "] " + ultimo_error +
                  ", espero " + str(espera) + "s")
            time.sleep(espera)

        intento = intento + 1

    raise ErrorDelModelo(
        "Se agotaron los " + str(config.REINTENTOS) + " intentos. Ultimo error: " + ultimo_error
    )
