"""
L2 - Ejercicio 01: el primer llamado a un modelo.

QUE VAMOS A VER
  - Como se conecta un programa de Python con un modelo de lenguaje.
  - Que son los "roles" de los mensajes.
  - Por que el modelo no se acuerda de nada entre una pregunta y la otra.

COMO CORRERLO (desde la terminal, parado en esta carpeta)
    python 01_primer_llamado.py
    python 01_primer_llamado.py --provider gemini
    python 01_primer_llamado.py --provider openai --model gpt-4o
"""

# --- Preparacion para poder importar la carpeta common ---------------------
# Estas tres lineas le dicen a Python: "ademas de donde buscas siempre, mira
# tambien en la carpeta de arriba". Sin esto no encontraria la carpeta common.
# Se repiten en todos los ejercicios; no hace falta entenderlas en detalle.
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# ---------------------------------------------------------------------------

from common.config import crear_parser
from common.llm import crear_cliente_desde_argumentos, conversar, obtener_texto, preguntar
from common.ui import mostrar_configuracion, mostrar_uso, titulo


def main():
    # 1) Leemos lo que se escribio en la terminal (--provider, --model)
    parser = crear_parser("Primer llamado a un modelo de lenguaje")
    args = parser.parse_args()

    # 2) Creamos la conexion. Si falta la clave, avisamos y cortamos el programa.
    try:
        cliente = crear_cliente_desde_argumentos(args)
    except ValueError as error:
        print(error)
        return   # "return" dentro de main() termina la funcion y el programa

    mostrar_configuracion(cliente)

    # -----------------------------------------------------------------------
    titulo("PARTE 1: el llamado mas simple posible")
    # -----------------------------------------------------------------------

    # Los mensajes se escriben como una LISTA de DICCIONARIOS.
    # Cada diccionario tiene dos claves:
    #   "role"    -> quien habla
    #   "content" -> que dice
    #
    # Hay tres roles posibles:
    #   system    -> instrucciones para el modelo (el usuario no las ve)
    #   user      -> lo que escribe la persona
    #   assistant -> lo que contesto el modelo
    mensajes = [
        {
            "role": "system",
            "content": "Sos un asistente tecnico. Responde en espanol y en un solo parrafo.",
        },
        {
            "role": "user",
            "content": "Explica que es un token en un modelo de lenguaje, para alguien que recien empieza.",
        },
    ]

    respuesta = conversar(cliente, mensajes, temperatura=0.3)

    print()
    print(obtener_texto(respuesta))
    print()
    mostrar_uso(respuesta)

    # finish_reason explica POR QUE el modelo dejo de escribir:
    #   "stop"   -> termino solo, todo bien
    #   "length" -> se corto porque llego al limite de max_tokens
    print("[motivo del final] " + respuesta.choices[0].finish_reason)

    # -----------------------------------------------------------------------
    titulo("PARTE 2: el atajo para cuando solo queres el texto")
    # -----------------------------------------------------------------------

    # La funcion preguntar() hace lo mismo que arriba pero en una sola linea.
    # Sirve cuando no necesitas mirar los tokens ni el motivo del final.
    texto = preguntar(
        cliente,
        "Dame tres ejemplos de usos de la inteligencia artificial en una empresa de logistica.",
        sistema="Respondes con una lista numerada, sin introduccion.",
        temperatura=0.5,
    )

    print()
    print(texto)

    # -----------------------------------------------------------------------
    titulo("PARTE 3: una conversacion con memoria")
    # -----------------------------------------------------------------------

    # ESTO ES IMPORTANTE: el modelo NO se acuerda de nada.
    # Cada llamado empieza de cero. La "memoria" de un chat existe porque
    # nosotros le volvemos a mandar toda la conversacion cada vez.

    historial = [
        {"role": "system", "content": "Sos un profesor de Python paciente y breve."}
    ]

    preguntas = [
        "Que es una lista en Python?",
        "Y como le agrego un elemento?",   # esta pregunta solo se entiende con la anterior
    ]

    for pregunta in preguntas:
        # Agregamos la pregunta del usuario al historial.
        historial.append({"role": "user", "content": pregunta})

        respuesta = conversar(cliente, historial, temperatura=0.2, max_tokens=200)
        contenido = obtener_texto(respuesta)

        # Agregamos tambien la respuesta del modelo.
        # Si nos olvidaramos de esta linea, la segunda pregunta
        # ("y como le agrego un elemento?") no tendria a que referirse.
        historial.append({"role": "assistant", "content": contenido})

        print()
        print("Usuario:    " + pregunta)
        print("Asistente:  " + contenido)

    print()
    print("[historial] quedaron " + str(len(historial)) + " mensajes guardados.")
    print("Todos ellos se vuelven a mandar en cada pregunta nueva.")


# Esta linea significa: "si este archivo se ejecuta directamente, corre main()".
# Sirve para que el codigo no se ejecute solo si otro archivo lo importa.
if __name__ == "__main__":
    main()
