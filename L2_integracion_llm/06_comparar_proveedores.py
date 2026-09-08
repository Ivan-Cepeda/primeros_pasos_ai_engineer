"""
L2 - Ejercicio 06: la misma tarea con OpenAI y con Gemini.

QUE VAMOS A VER
  Correr exactamente el mismo codigo contra los dos proveedores y comparar
  la respuesta, cuanto tardo y cuantos tokens gasto.

POR QUE ESTE EJERCICIO ES EL MAS IMPORTANTE DE L2
  Si tu codigo esta atado a un proveedor, cambiar de modelo significa
  reescribir medio programa. Si esta bien separado, es cambiar una palabra en
  un archivo de configuracion. Eso es todo lo que estuvimos construyendo.

NOTA
  Si solo tenes una de las dos claves, el ejercicio igual funciona: avisa cual
  falta y compara la que si esta configurada.

COMO CORRERLO
    python 06_comparar_proveedores.py
"""

import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import crear_parser
from common.llm import conversar, crear_cliente, obtener_texto
from common.ui import subtitulo, titulo


TAREA = """Un cliente escribe: 'Compre el plan anual hace 3 dias, no lo uso y
quiero que me devuelvan la plata. Ya escribi dos veces y nadie me contesta.'

Redacta la respuesta del equipo de soporte: maximo 4 lineas, con tono
comprensivo pero sin prometer el reembolso, y proponiendo un paso siguiente."""


def probar_proveedor(nombre_del_proveedor):
    """
    Corre la tarea con un proveedor y devuelve un diccionario con los resultados.

    Si algo falla (por ejemplo falta la clave), devuelve None para que el
    programa siga con el otro proveedor en vez de romperse.
    """
    try:
        cliente = crear_cliente(nombre_del_proveedor)
    except ValueError:
        print("  [salteado] " + nombre_del_proveedor + ": falta la clave en el archivo .env")
        return None

    momento_inicial = time.time()

    try:
        respuesta = conversar(
            cliente,
            [{"role": "user", "content": TAREA}],
            temperatura=0.4,
            max_tokens=700,
        )
    except Exception as error:
        print("  [error] " + nombre_del_proveedor + ": " + type(error).__name__)
        return None

    tiempo = time.time() - momento_inicial

    return {
        "proveedor": nombre_del_proveedor,
        "modelo": cliente["modelo"],
        "tiempo": round(tiempo, 2),
        "tokens_entrada": respuesta.usage.prompt_tokens,
        "tokens_salida": respuesta.usage.completion_tokens,
        "texto": obtener_texto(respuesta),
    }


def main():
    parser = crear_parser("Comparar los dos proveedores")
    args = parser.parse_args()

    titulo("La misma tarea, el mismo codigo, dos proveedores distintos")
    print(TAREA)
    print()

    resultados = []

    for nombre in ["openai", "gemini"]:
        resultado = probar_proveedor(nombre)

        # Solo guardamos los que funcionaron.
        if resultado is not None:
            resultados.append(resultado)

    if len(resultados) == 0:
        print()
        print("No hay ningun proveedor configurado.")
        print("Completa el archivo .env con al menos una clave y volve a intentar.")
        return

    # Mostramos la respuesta de cada uno.
    for resultado in resultados:
        subtitulo(resultado["proveedor"].upper() + "  (" + resultado["modelo"] + ")")
        print(resultado["texto"])

    # Y despues una tabla para compararlos de un vistazo.
    titulo("TABLA COMPARATIVA")
    print("  Proveedor    Modelo                  Tiempo   Tok.entrada  Tok.salida")
    print("  " + "-" * 68)

    for resultado in resultados:
        # ljust y rjust rellenan con espacios para que las columnas queden
        # alineadas. ljust rellena a la derecha, rjust a la izquierda.
        linea = "  "
        linea = linea + resultado["proveedor"].ljust(13)
        linea = linea + resultado["modelo"].ljust(24)
        linea = linea + (str(resultado["tiempo"]) + "s").rjust(7)
        linea = linea + str(resultado["tokens_entrada"]).rjust(13)
        linea = linea + str(resultado["tokens_salida"]).rjust(12)
        print(linea)

    titulo("COMO LEER ESTA COMPARACION")
    print("""
  * Los tokens NO se pueden comparar directamente entre proveedores: cada uno
    parte el texto de forma distinta. Para comparar costos hay que mirar el
    precio por millon de tokens de cada uno.

  * Una sola prueba no alcanza para decidir nada. Para elegir en serio hace
    falta probar con muchos casos (eso lo vemos en L3, ejercicio 04).

  * Ademas de la calidad, en un proyecto real pesan: cuanto tarda, cuanto
    cuesta, si tiene capa gratuita y donde quedan guardados los datos.
""")


if __name__ == "__main__":
    main()
