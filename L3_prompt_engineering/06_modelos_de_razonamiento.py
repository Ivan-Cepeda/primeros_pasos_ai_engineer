"""
L3 - Ejercicio 06: los modelos que piensan antes de contestar.

POR QUE EXISTE ESTE EJERCICIO
  Los cinco ejercicios anteriores ensenan las tecnicas clasicas de prompting,
  que se desarrollaron entre 2020 y 2024. Funcionan y hay que conocerlas.

  Pero los modelos cambiaron. Los de 2026 (Gemini 3.x, GPT-6, Claude Opus 5)
  razonan solos, por dentro, antes de escribir la respuesta. Eso cambia dos
  cosas importantes:

    1. Aparece un tipo de token que pagas y no ves.
    2. Varias tecnicas clasicas dejaron de servir, o directamente estorban.

  Este ejercicio mide las dos cosas con tu propio modelo y tu propia clave.
  No vas a tener que creerme: los numeros los saca tu computadora.

COMO CORRERLO
    python 06_modelos_de_razonamiento.py --provider gemini
    python 06_modelos_de_razonamiento.py --provider openai
"""

import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import crear_parser
from common.llm import (conversar, crear_cliente_desde_argumentos,
                        obtener_texto, tokens_de_razonamiento)
from common.ui import mostrar_configuracion, subtitulo, titulo


# Una tarea facil: se resuelve de un vistazo.
TAREA_FACIL = (
    "Clasifica este ticket en FACTURACION, TECNICO o CUENTA. "
    "Responde solo la categoria.\n\n"
    "Ticket: Necesito la factura de octubre para contaduria."
)

# Una tarea dificil: hay que combinar varias pistas para resolverla.
TAREA_DIFICIL = """Tres amigas (Ana, Bea y Cora) tienen cada una una mascota
distinta (gato, perro, loro) y viven en pisos distintos (1, 2 y 3).

  - La duena del loro vive justo encima de Bea.
  - Ana no vive en el piso 1.
  - La duena del gato vive en el piso 1.
  - Cora no tiene perro.

Quien tiene cada mascota y en que piso vive? Responde solo con tres lineas
del estilo 'Nombre - mascota - piso'."""


def medir(cliente, prompt, max_tokens=2500, esfuerzo=None):
    """
    Hace una llamada y devuelve un diccionario con todo lo que queremos medir.

    Si "esfuerzo" no es None, se lo pasamos al modelo con el parametro
    reasoning_effort, que es la perilla para decirle cuanto tiene que pensar.

    Devolvemos None si el modelo no acepta ese parametro, asi el ejercicio
    sigue andando igual con modelos que no razonan.
    """
    extras = {}

    if esfuerzo is not None:
        extras["reasoning_effort"] = esfuerzo

    momento_inicial = time.time()

    try:
        respuesta = conversar(
            cliente,
            [{"role": "user", "content": prompt}],
            temperatura=0,
            max_tokens=max_tokens,
            **extras
        )
    except Exception as error:
        print("    [no disponible] " + type(error).__name__ + ": " + str(error)[:90])
        return None

    return {
        "texto": obtener_texto(respuesta),
        "pensamiento": tokens_de_razonamiento(respuesta),
        "visible": respuesta.usage.completion_tokens,
        "segundos": round(time.time() - momento_inicial, 1),
        "motivo_final": respuesta.choices[0].finish_reason,
    }


def main():
    parser = crear_parser("Los modelos que piensan antes de contestar")
    args = parser.parse_args()

    try:
        cliente = crear_cliente_desde_argumentos(args)
    except ValueError as error:
        print(error)
        return

    mostrar_configuracion(cliente)

    # =======================================================================
    titulo("1) EL TOKEN QUE PAGAS Y NO VES")
    # =======================================================================

    resultado = medir(cliente, TAREA_FACIL)

    if resultado is None:
        print("No pude hacer la llamada. Revisa tu configuracion.")
        return

    print("  Le pedimos que clasifique un ticket. Contesto: " + resultado["texto"])
    print()
    print("  Tokens que ESCRIBIO y vos leiste : " + str(resultado["visible"]))
    print("  Tokens que PENSO y no te mostro  : " + str(resultado["pensamiento"]))
    print()

    if resultado["pensamiento"] == 0:
        print("  Tu modelo NO razona por dentro: contesta directo.")
        print("  Es lo que pasaba con los modelos hasta 2024. Este ejercicio")
        print("  te va a resultar menos dramatico, pero segui leyendo: cuando")
        print("  cambies a un modelo de razonamiento, esto te va a pasar.")
    else:
        veces = round(resultado["pensamiento"] / max(resultado["visible"], 1))
        print("  Tu modelo penso " + str(veces) + " veces mas de lo que escribio.")
        print("  Todo eso se paga, aunque no lo veas en pantalla.")
        print()
        print("  De donde sale el numero: el campo 'usage' trae entrada, salida")
        print("  y total. Si sumas entrada + salida y te da MENOS que el total,")
        print("  la diferencia es el pensamiento. No viene en un campo propio.")

    # =======================================================================
    titulo("2) POR QUE max_tokens TE PUEDE DEJAR SIN RESPUESTA")
    # =======================================================================
    # Este es el error mas comun al pasar a un modelo de razonamiento, y el que
    # rompio estos mismos ejercicios cuando se escribieron.

    print("  max_tokens NO limita solo lo que el modelo escribe.")
    print("  Limita el pensamiento MAS la escritura, todo junto.")
    print()
    print("  Probamos la misma tarea con presupuestos cada vez mas chicos:")
    print()
    print("  max_tokens   pensamiento   visible   respuesta")
    print("  " + "-" * 62)

    for presupuesto in [1000, 300, 50]:
        resultado = medir(cliente, TAREA_FACIL, max_tokens=presupuesto)

        if resultado is None:
            continue

        if resultado["texto"] == "":
            respuesta_mostrada = "(VACIA)"
        else:
            respuesta_mostrada = resultado["texto"][:20]

        linea = "  "
        linea = linea + str(presupuesto).ljust(13)
        linea = linea + str(resultado["pensamiento"]).rjust(11)
        linea = linea + str(resultado["visible"]).rjust(10)
        linea = linea + "   " + respuesta_mostrada
        print(linea)

    print()
    print("  Si con el presupuesto chico la respuesta salio VACIA, ya viste el")
    print("  problema: el modelo gasto todo pensando y no le quedo lugar para")
    print("  contestar. No fallo el prompt. Fallo el presupuesto.")
    print()
    print("  REGLA PRACTICA: con un modelo de razonamiento, calcula cuantos")
    print("  tokens necesita la respuesta y multiplica por 10.")

    # =======================================================================
    titulo("3) LA PERILLA DE ESFUERZO")
    # =======================================================================
    # Esto es lo mas nuevo. Antes, para que el modelo razonara mas, le
    # escribias "pensemos paso a paso". Ahora es un parametro.

    print("  Los modelos de razonamiento aceptan un parametro que dice cuanto")
    print("  tienen que pensar: reasoning_effort. Lo probamos en dos tareas de")
    print("  dificultad muy distinta.")

    for nombre_tarea, prompt in [("TAREA FACIL (clasificar un ticket)", TAREA_FACIL),
                                 ("TAREA DIFICIL (un acertijo de logica)", TAREA_DIFICIL)]:

        subtitulo(nombre_tarea)
        print("  esfuerzo   pensamiento   visible   tiempo   respuesta")
        print("  " + "-" * 72)

        for esfuerzo in ["none", "low", "high"]:
            resultado = medir(cliente, prompt, max_tokens=2500, esfuerzo=esfuerzo)

            if resultado is None:
                continue

            # Aplastamos los saltos de linea para que entre en una sola fila.
            texto_en_una_linea = resultado["texto"].replace("\n", " / ")

            linea = "  "
            linea = linea + esfuerzo.ljust(11)
            linea = linea + str(resultado["pensamiento"]).rjust(11)
            linea = linea + str(resultado["visible"]).rjust(10)
            linea = linea + (str(resultado["segundos"]) + "s").rjust(8)
            linea = linea + "   " + texto_en_una_linea[:34]
            print(linea)

    print()
    print("  QUE MIRAR:")
    print()
    print("  * En la tarea facil, subir el esfuerzo gasta mas y no mejora nada.")
    print("    La respuesta correcta ya salia con el esfuerzo mas bajo.")
    print()
    print("  * En la tarea dificil el pensamiento se dispara. Y ojo: a veces el")
    print("    esfuerzo mas alto EMPEORA el resultado, porque el modelo le da")
    print("    tantas vueltas que se queda sin espacio para contestar, o duda")
    print("    de una respuesta que ya tenia bien.")
    print()
    print("  Mas esfuerzo NO es mejor. Es una perilla que se calibra midiendo,")
    print("  igual que la temperature del ejercicio 02 de L2.")

    # =======================================================================
    titulo("4) 'PENSEMOS PASO A PASO' YA NO HACE FALTA")
    # =======================================================================
    # En el ejercicio 03 vimos chain-of-thought: pedirle al modelo que razone
    # en voz alta. Con un modelo que YA razona por dentro, pedirselo de nuevo
    # es pagar dos veces por lo mismo.

    print("  Comparamos la misma tarea dificil de dos formas:")
    print()

    sin_pedirlo = medir(cliente, TAREA_DIFICIL, max_tokens=2500)
    pidiendolo = medir(cliente, TAREA_DIFICIL + "\n\nPensemos paso a paso, "
                                                "explicando cada deduccion.",
                       max_tokens=2500)

    if sin_pedirlo is not None and pidiendolo is not None:
        print("  A) Sin pedirle que razone (el modelo razona solo)")
        print("     pensamiento: " + str(sin_pedirlo["pensamiento"]) +
              " | escrito: " + str(sin_pedirlo["visible"]) +
              " | " + str(sin_pedirlo["segundos"]) + "s")
        print("     " + sin_pedirlo["texto"].replace("\n", " / ")[:70])
        print()
        print("  B) Pidiendole 'pensemos paso a paso'")
        print("     pensamiento: " + str(pidiendolo["pensamiento"]) +
              " | escrito: " + str(pidiendolo["visible"]) +
              " | " + str(pidiendolo["segundos"]) + "s")
        print("     " + pidiendolo["texto"].replace("\n", " / ")[:70])
        print()

        # Los tokens escritos son los caros. Comparamos esa columna.
        if pidiendolo["visible"] > sin_pedirlo["visible"]:
            cuanto_mas = round(pidiendolo["visible"] / max(sin_pedirlo["visible"], 1), 1)
            print("  La version B escribio " + str(cuanto_mas) + " veces mas tokens")
            print("  (que son los caros) para llegar a la misma conclusion.")

    print()
    print("  Los estudios de 2026 le atribuyen a 'pensemos paso a paso' entre")
    print("  2 y 3 por ciento de mejora en el mejor caso, a cambio de entre 20 y")
    print("  80 por ciento mas de tiempo. En modelos que ya razonan, muchas")
    print("  veces empeora el resultado.")

    # =======================================================================
    titulo("QUE CAMBIO Y QUE NO, EN 2026")
    # =======================================================================
    print("""
  LO QUE ENVEJECIO
    * "Pensemos paso a paso": el modelo ya lo hace solo. Ahora se configura
      con una perilla (reasoning_effort), no con una frase.
    * Few-shot con muchos ejemplos: arranca con UNO. Los modelos modernos
      captan el patron enseguida. Agrega mas solo si el resultado no alcanza.
    * Roles muy cargados ("sos un experto que habla en jerga tecnica"):
      mejor decir directamente que perspectiva queres.
    * Pedirle que verifique su trabajo: los modelos nuevos ya se verifican
      solos, y pedirselo los hace verificar de mas y gastar tokens al pedo.

  LO QUE SIGUE VALIENDO IGUAL QUE SIEMPRE
    * Instrucciones claras y sin ambiguedad (ejercicio 01).
    * Pedir un formato de salida concreto (ejercicio 01 y L2 ejercicio 04).
    * Darle permiso explicito para decir "no se" en vez de inventar.
    * MEDIR con casos de prueba (ejercicio 04). Esto es lo unico que no
      caduca nunca, y hoy vale mas que antes: como las tecnicas cambian
      rapido, lo unico que te dice cual usar es tu propia medicion.

  LO QUE HAY QUE APRENDER AHORA
    * Ingenieria de contexto: elegir bien QUE informacion entra en la
      ventana, en lugar de pulir la redaccion de una sola frase.
    * Manejar la perilla de esfuerzo como una decision de costo.
    * Automatizar la evaluacion, para poder cambiar de modelo sin miedo.

  LA IDEA DE FONDO
    Antes le enseñabamos al modelo COMO pensar. Ahora le decimos QUE queremos
    y CUANTO esfuerzo poner, y nos concentramos en darle buen contexto y en
    medir si el resultado sirve.
""")


if __name__ == "__main__":
    main()
