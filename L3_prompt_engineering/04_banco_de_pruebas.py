"""
L3 - Ejercicio 04: medir cual estrategia funciona mejor.

EL PROBLEMA QUE RESUELVE
  Hasta aca elegimos prompts "porque parecen mejores". Eso es una opinion.
  Este ejercicio los MIDE: corre las tres estrategias sobre casos de los que ya
  sabemos la respuesta correcta, y cuenta cuantas veces acerto cada una.

COMO CORRERLO
    python 04_banco_de_pruebas.py --provider gemini
    python 04_banco_de_pruebas.py --repeticiones 3
"""

import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import crear_parser
from common.llm import conversar, crear_cliente_desde_argumentos, obtener_texto
from common.ui import mostrar_configuracion, subtitulo, titulo


# ---------------------------------------------------------------------------
# Los casos de prueba.
#
# Cada uno es una lista de dos elementos: el ticket, y la categoria correcta
# segun una persona. Sin esa segunda columna no hay nada que medir.
#
# A proposito metimos dos casos dificiles (el 4 y el 5): son los que hacen
# fallar a los prompts flojos.
# ---------------------------------------------------------------------------
CASOS = [
    ["Necesito la factura de octubre para contaduria.", "FACTURACION"],
    ["La app se cierra sola cada vez que abro el escaner.", "TECNICO"],
    ["Quiero cambiar el mail asociado a mi usuario.", "CUENTA"],

    # Dificil: habla de un cobro, pero el problema de verdad es tecnico.
    ["Me cobraron el plan y la app me sigue mostrando la version gratis.", "TECNICO"],

    # Dificil: parece tecnico por el "no puedo entrar", pero es de cuenta.
    ["No puedo entrar, dice que mi contrasena esta mal y no me llega el mail.", "CUENTA"],

    ["Cancelen mi suscripcion, no quiero que me sigan cobrando.", "FACTURACION"],
]


# --- Estrategia 1: zero-shot -----------------------------------------------
PROMPT_ZERO_SHOT = """Clasifica el ticket en una de estas categorias:
FACTURACION, TECNICO o CUENTA.
Responde solo con la categoria, en mayusculas.

Ticket: {ticket}"""


# --- Estrategia 2: few-shot ------------------------------------------------
EJEMPLOS_FEW_SHOT = [
    ["No me llego el comprobante de pago de marzo.", "FACTURACION"],
    ["El boton de exportar no hace nada en Chrome.", "TECNICO"],
    ["Quiero borrar mi cuenta y mis datos.", "CUENTA"],
    # Este ejemplo esta puesto para ensenarle el criterio de los casos dificiles.
    ["Pague pero la funcion premium no se activa.", "TECNICO"],
]


# --- Estrategia 3: chain-of-thought ----------------------------------------
PROMPT_CHAIN_OF_THOUGHT = """Clasifica el ticket en una de estas categorias:
FACTURACION, TECNICO o CUENTA.

Primero escribi una linea que empiece con 'ANALISIS:' donde identifiques cual es
el problema que el cliente necesita resolver (no el tema que menciona de paso).
Despues escribi una linea que empiece con 'CATEGORIA:' con la categoria.

Ticket: {ticket}"""


def armar_mensajes(estrategia, ticket):
    """Arma los mensajes segun cual de las tres estrategias estemos probando."""

    if estrategia == "zero-shot":
        return [{"role": "user", "content": PROMPT_ZERO_SHOT.format(ticket=ticket)}]

    if estrategia == "few-shot":
        mensajes = [{
            "role": "system",
            "content": "Clasificas tickets en FACTURACION, TECNICO o CUENTA. "
                       "Respondes solo con la categoria.",
        }]

        for ejemplo in EJEMPLOS_FEW_SHOT:
            mensajes.append({"role": "user", "content": ejemplo[0]})
            mensajes.append({"role": "assistant", "content": ejemplo[1]})

        mensajes.append({"role": "user", "content": ticket})
        return mensajes

    # Si no era ninguna de las dos, es chain-of-thought.
    return [{"role": "user", "content": PROMPT_CHAIN_OF_THOUGHT.format(ticket=ticket)}]


def buscar_categoria(texto):
    """
    Busca la categoria dentro de lo que respondio el modelo.

    Somos flexibles a proposito: si el modelo agrego un punto, comillas o toda
    una linea de analisis, igual queremos encontrar la etiqueta. Si fueramos
    demasiado estrictos, contariamos como error de calidad algo que en realidad
    es solo un detalle de formato.
    """
    texto = texto.upper()

    # En la version chain-of-thought nos quedamos con lo que viene despues de
    # "CATEGORIA:", para no confundirnos con lo que diga el analisis.
    if "CATEGORIA:" in texto:
        texto = texto.split("CATEGORIA:")[1]

    for categoria in ["FACTURACION", "TECNICO", "CUENTA"]:
        if categoria in texto:
            return categoria

    return "NO_SE_ENTIENDE"


def evaluar_estrategia(cliente, estrategia, repeticiones):
    """
    Corre todos los casos con una estrategia y devuelve los resultados.

    Devolvemos un diccionario con los numeros y la lista de los casos fallados.
    """
    aciertos = 0
    total = 0
    segundos = 0
    tokens_entrada = 0
    tokens_salida = 0
    fallos = []

    for caso in CASOS:
        ticket = caso[0]
        categoria_correcta = caso[1]

        for repeticion in range(repeticiones):

            # Le damos mas espacio de respuesta al chain-of-thought porque
            # necesita escribir el analisis antes de la categoria.
            if estrategia == "chain-of-thought":
                limite = 200
            else:
                limite = 15

            momento_inicial = time.time()

            respuesta = conversar(
                cliente,
                armar_mensajes(estrategia, ticket),
                temperatura=0,
                max_tokens=limite,
            )

            segundos = segundos + (time.time() - momento_inicial)
            tokens_entrada = tokens_entrada + respuesta.usage.prompt_tokens
            tokens_salida = tokens_salida + respuesta.usage.completion_tokens

            categoria_obtenida = buscar_categoria(obtener_texto(respuesta))
            total = total + 1

            if categoria_obtenida == categoria_correcta:
                aciertos = aciertos + 1
            else:
                fallos.append(
                    ticket[:45] + "... | correcta: " + categoria_correcta +
                    " | dijo: " + categoria_obtenida
                )

    return {
        "estrategia": estrategia,
        "aciertos": aciertos,
        "total": total,
        "porcentaje": round(aciertos / total * 100, 1),
        "segundos": round(segundos, 1),
        "tokens_entrada": tokens_entrada,
        "tokens_salida": tokens_salida,
        "fallos": fallos,
    }


def main():
    parser = crear_parser("Medir cual estrategia de prompting funciona mejor")
    parser.add_argument(
        "--repeticiones",
        type=int,
        default=1,
        help="Cuantas veces correr cada caso. Mas repeticiones, medicion mas confiable.",
    )
    args = parser.parse_args()

    try:
        cliente = crear_cliente_desde_argumentos(args)
    except ValueError as error:
        print(error)
        return

    mostrar_configuracion(cliente)

    titulo("Probando " + str(len(CASOS)) + " casos, " +
           str(args.repeticiones) + " vez/veces cada uno, con 3 estrategias")

    resultados = []

    for estrategia in ["zero-shot", "few-shot", "chain-of-thought"]:
        print()
        print("  Probando " + estrategia + "...")
        resultados.append(evaluar_estrategia(cliente, estrategia, args.repeticiones))

    # -----------------------------------------------------------------------
    titulo("RESULTADOS")
    # -----------------------------------------------------------------------
    print("  Estrategia         Aciertos   Tiempo   Tok.entrada  Tok.salida")
    print("  " + "-" * 62)

    for resultado in resultados:
        linea = "  "
        linea = linea + resultado["estrategia"].ljust(19)
        linea = linea + (str(resultado["porcentaje"]) + "%").rjust(8)
        linea = linea + (str(resultado["segundos"]) + "s").rjust(9)
        linea = linea + str(resultado["tokens_entrada"]).rjust(13)
        linea = linea + str(resultado["tokens_salida"]).rjust(12)
        print(linea)

    # Mostramos que fallo en cada una: eso es lo mas util del ejercicio.
    for resultado in resultados:
        if len(resultado["fallos"]) > 0:
            subtitulo("Casos que fallo " + resultado["estrategia"])
            for fallo in resultado["fallos"]:
                print("  - " + fallo)

    # -----------------------------------------------------------------------
    titulo("COMO LEER ESTA TABLA")
    # -----------------------------------------------------------------------
    print("""
  * No existe "la mejor estrategia". Existe la mejor para TU tarea, medida con
    TUS casos. Por eso la lista de casos de prueba es lo mas valioso que vas a
    construir en un proyecto.

  * Mira las tres columnas juntas. Ganar 3% de aciertos gastando 5 veces mas
    tokens y tardando el triple puede no convenirte.

  * Los casos que fallan no son un problema: son informacion. Mira que
    criterio le falto al prompt y agregalo (o convertilo en un ejemplo).

  * Con 6 casos, una diferencia chica no significa nada. En un proyecto real
    se usan entre 50 y 200 casos.
""")


if __name__ == "__main__":
    main()
