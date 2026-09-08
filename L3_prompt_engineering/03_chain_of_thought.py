"""
L3 - Ejercicio 03: chain-of-thought (pedirle que razone paso a paso).

QUE ES
  Es pedirle al modelo que escriba su razonamiento ANTES de dar la respuesta,
  en vez de tirar el resultado de una.

POR QUE FUNCIONA
  El modelo escribe una palabra por vez. Si le pedis el resultado de una, tiene
  que resolver todo "de golpe". Si lo dejas escribir los pasos, cada paso que
  escribe le sirve de apoyo para el siguiente.

CASO DE USO
  Un negocio con varios descuentos encadenados. Si el modelo se equivoca en la
  cuenta, es plata real perdida.

COMO CORRERLO
    python 03_chain_of_thought.py --provider gemini
"""

import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import crear_parser
from common.llm import crear_cliente_desde_argumentos, preguntar
from common.ui import mostrar_configuracion, subtitulo, titulo


PROBLEMA = """Un cliente compra 3 monitores a 180 dolares cada uno y 2 teclados
a 45 dolares cada uno.

Reglas del negocio, en este orden:
  1. Si el subtotal supera los 500 dolares, se descuenta el 10% del subtotal.
  2. Sobre lo que queda se suma 21% de impuesto.
  3. El envio cuesta 30 dolares, pero es gratis si el total con impuesto
     supera los 700 dolares.

Cuanto tiene que pagar el cliente?"""


def main():
    parser = crear_parser("Chain-of-thought: razonar paso a paso")
    args = parser.parse_args()

    try:
        cliente = crear_cliente_desde_argumentos(args)
    except ValueError as error:
        print(error)
        return

    mostrar_configuracion(cliente)

    # -----------------------------------------------------------------------
    titulo("A) SIN razonamiento: le pedimos solo el numero")
    # -----------------------------------------------------------------------
    respuesta = preguntar(
        cliente,
        PROBLEMA + "\n\nResponde unicamente con el numero final, sin explicar nada.",
        temperatura=0,
    )
    print(respuesta)

    # -----------------------------------------------------------------------
    titulo("B) CON razonamiento: le pedimos que muestre los pasos")
    # -----------------------------------------------------------------------
    # El orden es lo mas importante: primero los pasos, DESPUES el resultado.
    # Si pedis "el resultado y despues la explicacion", el modelo ya se
    # comprometio con un numero y la explicacion solo lo justifica.
    respuesta = preguntar(
        cliente,
        PROBLEMA + "\n\nResolve paso a paso, mostrando cada regla en su propia "
                   "linea. Al final escribi 'TOTAL: <numero>'.",
        temperatura=0,
    )
    print(respuesta)

    # -----------------------------------------------------------------------
    titulo("C) LA VERSION QUE SE USA EN PRODUCCION")
    # -----------------------------------------------------------------------
    # Problema del punto B: al usuario le mostramos un muro de texto.
    # Solucion: pedimos el razonamiento y el resultado en campos SEPARADOS.
    # El modelo igual razona (escribe los pasos), pero nosotros elegimos que
    # mostrarle al cliente y que guardar solo para revisar despues.

    instrucciones = """Sos un motor de calculo. Devolves SOLO un JSON con estas claves:

  "razonamiento"  -> una lista de textos, un paso de la cuenta por posicion
  "total"         -> el numero final, sin simbolo de moneda
  "envio_gratis"  -> true o false

No escribas nada fuera del JSON."""

    respuesta = preguntar(
        cliente,
        PROBLEMA,
        sistema=instrucciones,
        temperatura=0,
        response_format={"type": "json_object"},
    )

    try:
        datos = json.loads(respuesta)
    except json.JSONDecodeError:
        print("El modelo no devolvio un JSON valido. Respondio:")
        print(respuesta)
        return

    subtitulo("Lo que guardamos para poder auditar la cuenta")

    numero_de_paso = 1
    for paso in datos["razonamiento"]:
        print("  " + str(numero_de_paso) + ". " + paso)
        numero_de_paso = numero_de_paso + 1

    subtitulo("Lo que ve el cliente en la pantalla")
    print("  Total a pagar: " + str(datos["total"]) + " dolares")

    if datos["envio_gratis"]:
        print("  Envio: gratis")
    else:
        print("  Envio: con costo")

    # -----------------------------------------------------------------------
    titulo("D) EL TRUCO MAS BARATO QUE EXISTE")
    # -----------------------------------------------------------------------
    # Investigadores descubrieron que agregar literalmente la frase
    # "pensemos paso a paso" ya activa el razonamiento, sin dar ejemplos ni
    # escribir instrucciones elaboradas.
    print(preguntar(
        cliente,
        "Si hoy es martes, que dia de la semana va a ser dentro de 100 dias? "
        "Pensemos paso a paso.",
        temperatura=0,
    ))

    # -----------------------------------------------------------------------
    titulo("CUANDO NO USAR CHAIN-OF-THOUGHT")
    # -----------------------------------------------------------------------
    print("""
  * Cuando la tarea es de un solo paso (clasificar, traducir, extraer un dato).
    Ahi solo agrega demora y costo sin mejorar nada.

  * Cuando el usuario espera una respuesta corta e inmediata en un chat.

  Y ojo con el costo: el razonamiento son tokens de SALIDA, que son los mas
  caros de todos. Lo vemos con numeros en el ejercicio 05.
""")


if __name__ == "__main__":
    main()
