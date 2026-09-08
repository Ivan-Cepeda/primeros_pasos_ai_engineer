"""
L3 - Ejercicio 02: few-shot (ensenar con ejemplos).

QUE ES FEW-SHOT
  Es mostrarle al modelo 2 a 5 ejemplos ya resueltos dentro del prompt, para
  que copie el patron.

CUANDO SIRVE
  Cuando lo que queres es facil de MOSTRAR pero dificil de EXPLICAR: un formato
  propio de tu empresa, un tono de escritura, una regla llena de excepciones.

CASO DE USO
  Ordenar direcciones de envio en un formato interno. Explicar todas las reglas
  con palabras seria larguisimo; con tres ejemplos se entiende solo.

COMO CORRERLO
    python 02_few_shot.py --provider gemini
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import crear_parser
from common.llm import conversar, crear_cliente_desde_argumentos, obtener_texto
from common.ui import mostrar_configuracion, subtitulo, titulo


DIRECCIONES_A_ORDENAR = [
    "av. cabildo 2345 piso 4 depto b, belgrano, caba",
    "San Martin 45, Rosario Santa Fe",
    "calle falsa 123",
]

INSTRUCCION = """Ordenas direcciones en el formato interno de la empresa:
CALLE | NUMERO | UNIDAD | LOCALIDAD | PROVINCIA
Usa un guion cuando un dato no aparezca en la direccion."""


# ---------------------------------------------------------------------------
# Los ejemplos.
#
# Cada ejemplo son DOS mensajes: la pregunta (role "user") y la respuesta
# perfecta (role "assistant"). Al ver eso, el modelo entiende "asi contestaste
# antes" y sigue el mismo patron.
#
# Los guardamos como una lista de listas: cada lista interna tiene dos textos.
# ---------------------------------------------------------------------------
EJEMPLOS = [
    # Ejemplo 1: una direccion completa, con departamento.
    ["Corrientes 1234 4to A, Villa Crespo, Ciudad de Buenos Aires",
     "AV. CORRIENTES | 1234 | 4A | VILLA CRESPO | CABA"],

    # Ejemplo 2: sin departamento. Le muestra cuando usar el guion.
    ["belgrano 890, cordoba capital",
     "BELGRANO | 890 | - | CORDOBA CAPITAL | CORDOBA"],

    # Ejemplo 3: el caso raro. "bv." se escribe completo y "PB" se deja igual.
    # Explicar esto con palabras seria enredado; con un ejemplo, es obvio.
    ["bv. orono 55 pb, rosario",
     "BV. ORONO | 55 | PB | ROSARIO | SANTA FE"],
]


def armar_mensajes(direccion, usar_ejemplos):
    """
    Arma la lista de mensajes para mandarle al modelo.

    Si usar_ejemplos es True, mete los ejemplos en el medio.
    Asi podemos comparar las dos versiones con el mismo codigo.
    """
    mensajes = [{"role": "system", "content": INSTRUCCION}]

    if usar_ejemplos:
        for ejemplo in EJEMPLOS:
            pregunta = ejemplo[0]
            respuesta_ideal = ejemplo[1]

            mensajes.append({"role": "user", "content": pregunta})
            mensajes.append({"role": "assistant", "content": respuesta_ideal})

    mensajes.append({"role": "user", "content": direccion})

    return mensajes


def main():
    parser = crear_parser("Few-shot: ensenar con ejemplos")
    args = parser.parse_args()

    try:
        cliente = crear_cliente_desde_argumentos(args)
    except ValueError as error:
        print(error)
        return

    mostrar_configuracion(cliente)

    # -----------------------------------------------------------------------
    titulo("A) SIN ejemplos: solo la instruccion escrita")
    # -----------------------------------------------------------------------
    for direccion in DIRECCIONES_A_ORDENAR:
        mensajes = armar_mensajes(direccion, usar_ejemplos=False)
        respuesta = conversar(cliente, mensajes, temperatura=0, max_tokens=60)

        print("  " + direccion)
        print("    -> " + obtener_texto(respuesta))
        print()

    # -----------------------------------------------------------------------
    titulo("B) CON 3 ejemplos: la misma instruccion")
    # -----------------------------------------------------------------------
    for direccion in DIRECCIONES_A_ORDENAR:
        mensajes = armar_mensajes(direccion, usar_ejemplos=True)
        respuesta = conversar(cliente, mensajes, temperatura=0, max_tokens=60)

        print("  " + direccion)
        print("    -> " + obtener_texto(respuesta))
        print()

    print("Mira la diferencia: con ejemplos respeta las mayusculas, el separador")
    print("' | ', las abreviaturas y el guion. Nada de eso estaba explicado con")
    print("palabras en la instruccion.")

    # -----------------------------------------------------------------------
    titulo("C) LO QUE CUESTAN LOS EJEMPLOS")
    # -----------------------------------------------------------------------
    # Los ejemplos viajan en CADA pedido. Son tokens de entrada que se pagan
    # todas las veces. Esa es la contra del few-shot.

    direccion = DIRECCIONES_A_ORDENAR[0]

    sin_ejemplos = conversar(cliente, armar_mensajes(direccion, False), temperatura=0, max_tokens=60)
    con_ejemplos = conversar(cliente, armar_mensajes(direccion, True), temperatura=0, max_tokens=60)

    print("  tokens de entrada SIN ejemplos: " + str(sin_ejemplos.usage.prompt_tokens))
    print("  tokens de entrada CON ejemplos: " + str(con_ejemplos.usage.prompt_tokens))
    print()
    print("  Si haces miles de llamadas por dia, esa diferencia se nota en la factura.")

    # -----------------------------------------------------------------------
    titulo("D) CUIDADO: los ejemplos tambien pueden arruinar todo")
    # -----------------------------------------------------------------------
    # Si todos tus ejemplos tienen algo en comun por casualidad, el modelo cree
    # que eso es parte de la regla. Aca los tres son NEGATIVO a proposito.

    mensajes_mal_armados = [
        {"role": "system", "content": "Clasifica el sentimiento en POSITIVO, NEUTRO o NEGATIVO."},
        {"role": "user", "content": "El envio tardo muchisimo."},
        {"role": "assistant", "content": "NEGATIVO"},
        {"role": "user", "content": "Vino roto."},
        {"role": "assistant", "content": "NEGATIVO"},
        {"role": "user", "content": "Nadie me contesto."},
        {"role": "assistant", "content": "NEGATIVO"},
        # Y ahora le preguntamos algo claramente positivo:
        {"role": "user", "content": "Excelente producto, lo recomiendo muchisimo."},
    ]

    respuesta = conversar(cliente, mensajes_mal_armados, temperatura=0, max_tokens=10)

    print("  Le preguntamos por una resena claramente positiva.")
    print("  Contesto: " + obtener_texto(respuesta))
    print()
    print("  REGLA: tus ejemplos tienen que incluir TODAS las respuestas posibles")
    print("  y estar balanceados. Un few-shot mal armado empeora al modelo.")

    # -----------------------------------------------------------------------
    titulo("ZERO-SHOT O FEW-SHOT?")
    # -----------------------------------------------------------------------
    print("""
  Empeza siempre con zero-shot. Pasa a few-shot cuando:
    * el formato de salida es raro o propio de tu empresa
    * necesitas un tono especifico dificil de describir
    * la regla tiene excepciones que quedan enredadas al escribirlas
    * el zero-shot funciona pero cambia la respuesta cada vez

  Cuantos ejemplos: entre 2 y 5. Mas de 8 casi nunca mejora, y siempre cuesta.
""")


if __name__ == "__main__":
    main()
