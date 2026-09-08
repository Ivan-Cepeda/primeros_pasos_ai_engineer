"""
L3 - Ejercicio 01: zero-shot (pedir sin dar ejemplos).

QUE ES ZERO-SHOT
  Es pedirle al modelo que haga algo explicandoselo con palabras, sin mostrarle
  ni un solo ejemplo resuelto. Es lo mas barato y siempre hay que probarlo
  primero.

LO QUE VAS A DESCUBRIR
  Cuando un zero-shot no funciona, casi nunca es culpa del modelo: es que la
  instruccion estaba mal escrita.

CASO DE USO
  Clasificar resenas de un sitio de compras online.

COMO CORRERLO
    python 01_zero_shot.py --provider gemini
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import crear_parser
from common.llm import crear_cliente_desde_argumentos, preguntar
from common.ui import mostrar_configuracion, subtitulo, titulo


RESENAS = [
    "Llego a los 3 dias, bien embalado. Anda bien aunque el cable es corto.",
    "PESIMO. Pague envio express y tardo 3 semanas. El vendedor no contesta.",
    "Es lo que dice la descripcion.",
]


# ---------------------------------------------------------------------------
# VERSION 1: la instruccion que sale naturalmente cuando escribis rapido.
#
# Que le falta:
#   - no dice cuales son las categorias posibles
#   - no dice como tiene que verse la respuesta
#   - no dice que hacer si la resena es ambigua
#
# Resultado: cada vez contesta algo distinto y tu programa no lo puede usar.
# ---------------------------------------------------------------------------
PROMPT_VAGO = "Analiza esta resena:\n\n{resena}"


# ---------------------------------------------------------------------------
# VERSION 2: la misma tarea, bien escrita.
#
# Son cinco ingredientes. Si te falta alguno, el prompt va a fallar:
#   1. ROL      -> quien es el modelo mientras hace esta tarea
#   2. TAREA    -> un solo verbo, una sola responsabilidad
#   3. OPCIONES -> la lista cerrada de respuestas posibles
#   4. FORMATO  -> exactamente como tiene que verse la respuesta
#   5. BORDES   -> que hacer cuando la entrada es confusa
# ---------------------------------------------------------------------------
PROMPT_ESPECIFICO = """Sos un analista de calidad de un sitio de compras.

Clasifica la resena del cliente.

Responde con exactamente tres lineas, con este formato:
SENTIMIENTO: POSITIVO o NEUTRO o NEGATIVO
MOTIVO: ENVIO o PRODUCTO o ATENCION o PRECIO o SIN_MOTIVO
ACCION: NINGUNA o CONTACTAR_CLIENTE o REVISAR_VENDEDOR

Reglas:
- Si la resena menciona varios motivos, elegi el que mas pesa en la queja.
- Si no hay informacion suficiente, usa NEUTRO / SIN_MOTIVO / NINGUNA.
- Usa REVISAR_VENDEDOR solo si el vendedor incumplio algo, no si al cliente
  simplemente no le gusto el producto.
- No escribas nada mas que esas tres lineas.

Resena: {resena}"""


def separar_en_campos(texto):
    """
    Convierte las tres lineas de la respuesta en un diccionario.

    Esto se puede hacer SOLO porque le pedimos un formato fijo. Con el prompt
    vago seria imposible.
    """
    campos = {}

    # splitlines() parte un texto en una lista, una posicion por cada linea.
    for linea in texto.splitlines():

        if ":" in linea:
            # split(":", 1) parte la linea en dos partes usando el primer ":".
            partes = linea.split(":", 1)
            clave = partes[0].strip().lower()
            valor = partes[1].strip()
            campos[clave] = valor

    return campos


def main():
    parser = crear_parser("Zero-shot: un prompt vago contra uno bien escrito")
    args = parser.parse_args()

    try:
        cliente = crear_cliente_desde_argumentos(args)
    except ValueError as error:
        print(error)
        return

    mostrar_configuracion(cliente)

    # -----------------------------------------------------------------------
    titulo("A) PROMPT VAGO: cada vez contesta cualquier cosa")
    # -----------------------------------------------------------------------
    for resena in RESENAS:
        subtitulo(resena)

        # .format() reemplaza {resena} dentro del texto por el valor real.
        prompt = PROMPT_VAGO.format(resena=resena)

        print(preguntar(cliente, prompt, temperatura=0, max_tokens=150))

    # -----------------------------------------------------------------------
    titulo("B) PROMPT ESPECIFICO: una respuesta que el programa puede usar")
    # -----------------------------------------------------------------------
    for resena in RESENAS:
        subtitulo(resena)

        prompt = PROMPT_ESPECIFICO.format(resena=resena)
        respuesta = preguntar(cliente, prompt, temperatura=0, max_tokens=60)

        print(respuesta)
        print()
        print("  Convertido a diccionario: " + str(separar_en_campos(respuesta)))

    # -----------------------------------------------------------------------
    titulo("C) PRUEBA DE ESTABILIDAD")
    # -----------------------------------------------------------------------
    # Un buen prompt tiene que dar SIEMPRE lo mismo ante la misma entrada.
    # Si da respuestas distintas, es que todavia quedo algo ambiguo.

    resena = RESENAS[0]
    respuestas_obtenidas = []

    for intento in range(3):
        prompt = PROMPT_ESPECIFICO.format(resena=resena)
        respuesta = preguntar(cliente, prompt, temperatura=0, max_tokens=60)

        # Solo la guardamos si no la habiamos visto antes.
        if respuesta not in respuestas_obtenidas:
            respuestas_obtenidas.append(respuesta)

    print("  De 3 corridas salieron " + str(len(respuestas_obtenidas)) + " respuestas distintas.")
    print("  Lo ideal es 1. Si son mas, todavia hay algo ambiguo en el prompt.")

    # -----------------------------------------------------------------------
    titulo("LISTA PARA REVISAR TUS PROMPTS")
    # -----------------------------------------------------------------------
    print("""
  [ ] Le dijiste al modelo quien es? (un rol)
  [ ] La tarea es UN solo verbo? (clasificar Y resumir Y traducir = 3 prompts)
  [ ] Escribiste la lista completa de respuestas posibles?
  [ ] Dijiste exactamente como tiene que verse la respuesta?
  [ ] Explicaste que hacer si la entrada es confusa o esta incompleta?
  [ ] Escribiste las reglas en positivo? ("responde solo X" funciona mejor
      que "no respondas Y")
""")


if __name__ == "__main__":
    main()
