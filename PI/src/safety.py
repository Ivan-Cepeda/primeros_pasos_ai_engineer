"""
Capa de seguridad (el bonus de la consigna).

La guia del proyecto pide pensar la seguridad "en capas", porque una sola linea
de defensa es facil de evadir. Este archivo implementa dos capas antes de gastar
una llamada al modelo, y una despues:

  ANTES (baratas, no cuestan ninguna llamada a la API):
    1. Deteccion de patrones de manipulacion conocidos.
    2. Deteccion de datos personales sensibles en la entrada.

  DESPUES:
    3. Revision de que la respuesta no haya filtrado las instrucciones internas.

UNA ACLARACION HONESTA
  Los modelos de 2026 resisten solos la mayoria de estos ataques. Al correr los
  ejemplos adversariales de este proyecto es probable que el modelo los rechace
  aunque saltees esta capa.

  Eso NO la vuelve inutil, por dos razones:
    - Esa resistencia la puso el proveedor, no vos. Puede cambiar en la proxima
      version del modelo o desaparecer si migras a uno mas barato.
    - Aunque el ataque rebote, vos queres ENTERARTE de que te estan atacando.
      Sin esta capa, un intento de manipulacion es indistinguible de una
      consulta normal en tus registros.
"""

import re


# Frases que aparecen en los intentos de manipulacion mas conocidos.
# No cubre a un atacante creativo (hay infinitas formas de escribir lo mismo),
# pero frena el ruido barato y genera la senal para las alertas.
PATRONES_DE_MANIPULACION = [
    "ignora las instrucciones",
    "ignora todas las instrucciones",
    "ignore previous instructions",
    "ignore all previous",
    "system override",
    "olvida tus reglas",
    "olvida tu tarea",
    "tus instrucciones",
    "prompt de sistema",
    "system prompt",
    "modo desarrollador",
    "developer mode",
    "sin restricciones",
    "actua como si no tuvieras",
    "sos ahora",
    "eres ahora",
]


# Datos personales que no deberian entrar al prompt ni quedar en los registros.
# Cada elemento es el patron y la etiqueta con la que lo reemplazamos.
PATRONES_DE_DATOS_PERSONALES = [
    [r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "[TARJETA]"],
    [r"\b[\w.+-]+@[\w-]+\.[\w.]+\b", "[EMAIL]"],
    [r"\b(sk|gsk|AIza)[\w-]{10,}\b", "[API_KEY]"],
]


# Texto que, si aparece en la respuesta, significa que el modelo copio sus
# propias instrucciones internas.
#
# CUIDADO AL ARMAR ESTA LISTA. Si pones algo que tiene una razon legitima para
# aparecer en una respuesta al cliente, vas a bloquear respuestas correctas. A
# eso se le llama falso positivo, y es el error mas caro de las validaciones de
# seguridad: rompe la experiencia de los usuarios honestos, que son casi todos.
TEXTO_QUE_NO_DEBE_SALIR = [
    "REGLAS DE SEGURIDAD",
    "eres el asistente interno",
    "consulta_no_confiable",
]


def detectar_manipulacion(texto):
    """
    Capa 1: busca patrones de manipulacion. Devuelve la lista de coincidencias.

    Lista vacia significa que no encontramos nada sospechoso. No significa que
    la entrada sea segura: significa que no reconocimos el ataque.
    """
    texto_en_minusculas = texto.lower()
    encontrados = []

    for patron in PATRONES_DE_MANIPULACION:
        if patron in texto_en_minusculas:
            encontrados.append(patron)

    return encontrados


def redactar_datos_personales(texto):
    """
    Capa 2: reemplaza los datos sensibles reconocibles por una etiqueta.

    Se usa en dos momentos distintos y por motivos distintos:
      - antes de mandar el texto al modelo, para no enviar datos de mas
      - antes de escribir en los registros, porque los logs se copian,
        se respaldan y los lee mucha mas gente que la base de datos

    Devuelve (texto_limpio, cuantos_reemplazos).
    """
    cantidad = 0

    for par in PATRONES_DE_DATOS_PERSONALES:
        patron = par[0]
        etiqueta = par[1]

        texto, reemplazos = re.subn(patron, etiqueta, texto)
        cantidad = cantidad + reemplazos

    return texto, cantidad


def marcar_como_no_confiable(texto):
    """
    Envuelve la consulta del usuario en etiquetas que la marcan como DATO.

    Tambien borramos las etiquetas que vengan dentro del propio texto, para que
    nadie pueda "cerrar" el bloque y escribir fuera de el.
    """
    texto = texto.replace("<consulta_no_confiable>", "")
    texto = texto.replace("</consulta_no_confiable>", "")

    return "<consulta_no_confiable>\n" + texto + "\n</consulta_no_confiable>"


def revisar_respuesta(texto):
    """
    Capa 3: chequea que la respuesta no haya filtrado las instrucciones.

    Es la capa mas confiable de las tres, porque no depende de anticipar como
    va a ser el ataque: revisa el resultado, sin importar como se llego a el.

    Devuelve (es_segura, motivo).
    """
    for prohibido in TEXTO_QUE_NO_DEBE_SALIR:
        if prohibido.lower() in texto.lower():
            return False, "la respuesta contenia texto interno: '" + prohibido + "'"

    return True, ""


def analizar_entrada(texto):
    """
    Corre las dos capas de entrada y devuelve un informe de lo encontrado.

    NO bloquea por si sola. Devuelve la informacion para que quien llama decida,
    porque la decision de bloquear es de producto, no de esta funcion.

    Nota de diseno: detectar una frase sospechosa no alcanza para bloquear. Un
    usuario legitimo puede preguntar "cuales son tus instrucciones?" por simple
    curiosidad. Lo que si hacemos siempre es registrarlo.
    """
    manipulacion = detectar_manipulacion(texto)
    texto_limpio, datos_redactados = redactar_datos_personales(texto)

    return {
        "patrones_de_manipulacion": manipulacion,
        "datos_personales_redactados": datos_redactados,
        "texto_limpio": texto_limpio,
        "sospechosa": len(manipulacion) > 0 or datos_redactados > 0,
    }
