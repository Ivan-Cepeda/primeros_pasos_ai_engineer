"""
L2 - Ejercicio 03: streaming y que hacer cuando algo falla.

QUE VAMOS A VER
  - Streaming: mostrar el texto de a poco, mientras se genera.
  - Que hacer cuando internet falla o el servidor esta ocupado.

POR QUE IMPORTA
  Cuando llamas a un modelo estas llamando a una computadora que esta lejos.
  Eso puede fallar: puede tardar, puede estar saturada, puede cortarse la
  conexion. Un programa que no preve eso se rompe delante del usuario.

COMO CORRERLO
    python 03_streaming_y_errores.py --provider gemini
"""

import os
import sys
import time   # time nos deja medir cuanto tarda algo y hacer pausas

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Estos son los tipos de error que puede devolver la libreria.
# Importarlos nos permite reaccionar distinto segun cual haya ocurrido.
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

from common.config import crear_parser
from common.llm import conversar_en_streaming, crear_cliente_desde_argumentos, preguntar
from common.ui import mostrar_configuracion, subtitulo, titulo


PREGUNTA = "Explica en 5 pasos como se publica una aplicacion de Python en un servidor."


def probar_sin_streaming(cliente):
    """Forma clasica: esperamos a que el modelo termine TODO y recien ahi mostramos."""

    momento_inicial = time.time()

    texto = preguntar(cliente, PREGUNTA, temperatura=0.3, max_tokens=300)

    print(texto)

    # Restamos los dos momentos para saber cuantos segundos pasaron.
    return time.time() - momento_inicial


def probar_con_streaming(cliente):
    """Forma con streaming: mostramos cada pedacito apenas llega."""

    momento_inicial = time.time()
    momento_del_primer_pedacito = None

    mensajes = [{"role": "user", "content": PREGUNTA}]

    for pedacito in conversar_en_streaming(cliente, mensajes, temperatura=0.3, max_tokens=300):

        # Anotamos cuando llego el primer pedacito: ese es el momento en que el
        # usuario deja de ver la pantalla vacia.
        if momento_del_primer_pedacito is None:
            momento_del_primer_pedacito = time.time() - momento_inicial

        # end="" evita que Python agregue un salto de linea despues de cada
        # pedacito. flush=True lo obliga a mostrarlo ya mismo.
        print(pedacito, end="", flush=True)

    print()   # un salto de linea al final

    tiempo_total = time.time() - momento_inicial

    return momento_del_primer_pedacito, tiempo_total


def preguntar_con_reintentos(cliente, pregunta, cantidad_de_intentos=3):
    """
    Vuelve a intentar si el error es de los que se pueden solucionar esperando.

    REGLA IMPORTANTE: no todos los errores se reintentan.
      SI se reintenta  -> servidor ocupado (429), problema de red, servidor caido (5xx)
      NO se reintenta  -> clave equivocada (401), pedido mal armado (400)

    Reintentar un error que no se va a arreglar solo hace perder tiempo y
    esconde el problema real.
    """
    numero_de_intento = 1

    while numero_de_intento <= cantidad_de_intentos:

        try:
            return preguntar(cliente, pregunta, temperatura=0.2, max_tokens=120)

        except RateLimitError:
            # 429 = hiciste demasiados pedidos muy rapido. Hay que esperar.
            segundos = 2 ** numero_de_intento   # 2, 4, 8... esto se llama "backoff"
            print("  [429] servidor ocupado. Espero " + str(segundos) + "s y reintento.")
            time.sleep(segundos)

        except APITimeoutError:
            segundos = 2 ** numero_de_intento
            print("  [timeout] tardo demasiado. Espero " + str(segundos) + "s y reintento.")
            time.sleep(segundos)

        except APIConnectionError:
            segundos = 2 ** numero_de_intento
            print("  [red] no me pude conectar. Espero " + str(segundos) + "s y reintento.")
            time.sleep(segundos)

        except APIStatusError as error:
            # Cualquier otro error del servidor. Los de la familia 400 son
            # culpa nuestra y no se arreglan reintentando.
            if error.status_code >= 400 and error.status_code < 500:
                return "[error " + str(error.status_code) + "] revisa tu clave o tu pedido."

            segundos = 2 ** numero_de_intento
            print("  [" + str(error.status_code) + "] error del servidor. Reintento en " + str(segundos) + "s.")
            time.sleep(segundos)

        numero_de_intento = numero_de_intento + 1

    # Si se acabaron los intentos, devolvemos un mensaje amable.
    # La aplicacion NO se rompe: avisa y sigue viva.
    return "[No pudimos generar la respuesta. Intenta de nuevo en unos minutos.]"


def main():
    parser = crear_parser("Streaming y manejo de errores")
    args = parser.parse_args()

    try:
        cliente = crear_cliente_desde_argumentos(args)
    except ValueError as error:
        print(error)
        return

    mostrar_configuracion(cliente)

    # -----------------------------------------------------------------------
    titulo("1) SIN streaming: la pantalla queda vacia hasta el final")
    # -----------------------------------------------------------------------
    tiempo = probar_sin_streaming(cliente)
    print()
    print("El usuario espero " + str(round(tiempo, 2)) + " segundos mirando la nada.")

    # -----------------------------------------------------------------------
    titulo("2) CON streaming: el texto aparece mientras se escribe")
    # -----------------------------------------------------------------------
    primer_pedacito, tiempo_total = probar_con_streaming(cliente)
    print()
    print("Primer texto en pantalla: " + str(round(primer_pedacito, 2)) + " segundos.")
    print("Respuesta completa en:    " + str(round(tiempo_total, 2)) + " segundos.")
    print()
    print("El tiempo TOTAL es parecido. Lo que cambia muchisimo es la espera")
    print("que SIENTE el usuario.")

    # -----------------------------------------------------------------------
    titulo("3) Una llamada que sabe reintentar")
    # -----------------------------------------------------------------------
    subtitulo("Caso normal (deberia funcionar a la primera)")
    print(preguntar_con_reintentos(cliente, "Resumi en dos lineas que es una API."))

    subtitulo("Caso con error: pedimos un modelo que no existe")
    # Provocamos un error a proposito para ver que el programa NO se rompe.
    try:
        cliente_roto = dict(cliente)          # copiamos el diccionario
        cliente_roto["modelo"] = "modelo-inventado-123"
        preguntar(cliente_roto, "hola")
    except Exception as error:
        # "Exception" atrapa cualquier error. Lo usamos aca porque el objetivo
        # es demostrar que el programa sigue funcionando.
        print("  Error atrapado correctamente: " + type(error).__name__)
        print("  El programa sigue andando, que es justamente lo que queriamos.")

    # -----------------------------------------------------------------------
    titulo("LISTA DE CONTROL")
    # -----------------------------------------------------------------------
    print("""
  [ ] Usa streaming siempre que haya una persona esperando la respuesta.
  [ ] Reintenta solo los errores 429, 5xx y de red.
  [ ] Nunca reintentes un error 401 o 400: se va a repetir igual.
  [ ] Ten siempre una respuesta de emergencia por si todo falla.
  [ ] Pone max_tokens para que el costo no se dispare.
""")


if __name__ == "__main__":
    main()
