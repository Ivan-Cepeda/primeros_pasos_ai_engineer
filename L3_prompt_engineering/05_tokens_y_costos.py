"""
L3 - Ejercicio 05: los tokens y cuanto cuesta todo esto.

QUE ES UN TOKEN
  Es el pedacito en el que el modelo parte el texto. No es una palabra ni una
  letra: esta en el medio. "hola" puede ser 1 token y "antidisestablishment"
  puede ser 5.

POR QUE IMPORTA
  Los tokens son la unidad con la que te cobran. Y tambien son el limite de
  cuanto texto entra en una conversacion.

TRES FORMAS DE CONTARLOS
  1. El campo "usage" de la respuesta -> exacto, pero solo DESPUES de pagar.
  2. La libreria tiktoken            -> exacta y gratis, solo para OpenAI.
  3. Una cuenta aproximada           -> sirve para cualquier proveedor.

OJO CON LOS MODELOS DE RAZONAMIENTO (2026)
  Si al correr esto ves que la suma no cierra (entrada + salida es MENOR que el
  total), no es un error: la diferencia son los tokens que el modelo gasto
  pensando por dentro, sin mostrartelos. Se pagan igual. Mira el punto 2.

COMO CORRERLO
    python 05_tokens_y_costos.py --provider gemini
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import crear_parser
from common.llm import conversar, crear_cliente_desde_argumentos, obtener_texto
from common.ui import mostrar_configuracion, subtitulo, titulo


# ---------------------------------------------------------------------------
# Precios de referencia, en dolares por MILLON de tokens.
#
# Verificados en la pagina oficial de cada proveedor en septiembre de 2026.
#
# DOS AVISOS, Y LOS DOS SON PARTE DE LA LECCION:
#
# 1. Los precios CAMBIAN y los modelos SE DAN DE BAJA. En una version anterior
#    de este archivo figuraba gemini-2.0-flash: hoy la API devuelve error 404
#    porque ese modelo ya no existe. Nunca presupuestes con una tabla que
#    copiaste hace seis meses.
#
# 2. Los modelos Gemini 3.6, 3.7 y 3.8 estan con precio PROMOCIONAL de
#    lanzamiento hasta el 31 de diciembre de 2026. El 1 de enero de 2027 pasan
#    de 0.75 a 1.50 la entrada, y de 3.75 a 7.50 la salida: el DOBLE. Si armas
#    un presupuesto anual con el precio de hoy, en enero te llevas una sorpresa.
#
# Si tu modelo no esta en esta lista, el programa te lo avisa y podes agregarlo
# vos. La tabla sirve igual para ver la RELACION entre el precio de entrada y
# el de salida, que es lo que enseña este ejercicio.
# ---------------------------------------------------------------------------
PRECIOS = {
    # --- OpenAI ---
    "gpt-4o-mini":           {"entrada":  0.15, "salida":  0.60},
    "gpt-5.6-luna":          {"entrada":  0.20, "salida":  1.20},
    "gpt-6-astra":           {"entrada": 10.00, "salida": 50.00},

    # --- Google Gemini ---
    "gemini-2.5-flash":      {"entrada":  0.30, "salida":  2.50},
    "gemini-2.5-pro":        {"entrada":  1.25, "salida": 10.00},
    "gemini-3.1-flash-lite": {"entrada":  0.25, "salida":  1.50},
    "gemini-3.5-flash-lite": {"entrada":  0.30, "salida":  2.50},
    "gemini-3.5-flash":      {"entrada":  1.50, "salida":  9.00},
    "gemini-3.6-flash":      {"entrada":  0.75, "salida":  3.75},
    "gemini-3.7-flash":      {"entrada":  0.75, "salida":  3.75},
    "gemini-3.8-flash":      {"entrada":  0.75, "salida":  3.75},
}


TEXTOS_DE_EJEMPLO = [
    "Hola",
    "La inteligencia artificial transforma la industria.",
    "antidisestablishmentarianism",
    "nandu, ciguena y murcielago",
    "def sumar(a, b):",
    "1234567890",
]


def contar_con_tiktoken(texto, modelo):
    """
    Cuenta los tokens exactos SIN llamar al servidor. Gratis y al instante.

    Solo funciona con modelos de OpenAI: Gemini parte el texto con su propio
    sistema. Cuando no se puede, devolvemos None.
    """
    try:
        import tiktoken
    except ImportError:
        # La libreria no esta instalada.
        return None

    try:
        codificador = tiktoken.encoding_for_model(modelo)
    except KeyError:
        # El modelo no esta en la lista de tiktoken. Probamos con el codificador
        # que usan los modelos GPT-4o.
        try:
            codificador = tiktoken.get_encoding("o200k_base")
        except Exception:
            return None

    return len(codificador.encode(texto))


def estimar_tokens(texto):
    """
    Calculo aproximado que funciona con cualquier proveedor.

    La regla practica es: en espanol, mas o menos 1 token cada 3.3 caracteres.
    No es exacto, pero sirve para decidir cosas ANTES de llamar al servidor,
    por ejemplo rechazar un documento que es obviamente demasiado grande.
    """
    cantidad = round(len(texto) / 3.3)

    if cantidad < 1:
        return 1

    return cantidad


def calcular_costo(modelo, tokens_entrada, tokens_salida, tokens_de_razonamiento=0):
    """
    Calcula cuanto salio una llamada. Devuelve None si no conocemos el precio.

    EL ERROR QUE CASI TODOS COMETEN
    -------------------------------
    Es tentador calcular el costo con dos numeros: entrada y salida. Pero si
    usas un modelo de razonamiento te queda MUY corto, porque los tokens que
    el modelo gasta pensando tambien se facturan, y se facturan al precio de
    SALIDA, que es el caro.

    Ejemplo real medido con gemini-3.7-flash:
        entrada 20 | salida visible 61 | razonamiento 293
    Si contas solo los 61 visibles, el costo te da 5 veces menos de lo que
    realmente vas a pagar.

    Por eso esta funcion suma el razonamiento a la salida antes de multiplicar.
    """
    if modelo not in PRECIOS:
        return None

    precio = PRECIOS[modelo]

    # Lo que se factura como salida es todo lo que el modelo genero: lo que
    # escribio en pantalla MAS lo que penso por dentro.
    salida_facturada = tokens_salida + tokens_de_razonamiento

    costo_entrada = tokens_entrada / 1000000 * precio["entrada"]
    costo_salida = salida_facturada / 1000000 * precio["salida"]

    return costo_entrada + costo_salida


def main():
    parser = crear_parser("Tokens y costos")
    args = parser.parse_args()

    try:
        cliente = crear_cliente_desde_argumentos(args)
    except ValueError as error:
        print(error)
        return

    mostrar_configuracion(cliente)
    modelo = cliente["modelo"]

    # -----------------------------------------------------------------------
    titulo("1) UN TOKEN NO ES UNA PALABRA")
    # -----------------------------------------------------------------------
    print("  Texto                                    Letras  tiktoken  Estimado")
    print("  " + "-" * 68)

    for texto in TEXTOS_DE_EJEMPLO:
        exacto = contar_con_tiktoken(texto, modelo)

        if exacto is None:
            columna_exacto = "-"
        else:
            columna_exacto = str(exacto)

        linea = "  "
        linea = linea + texto.ljust(41)
        linea = linea + str(len(texto)).rjust(6)
        linea = linea + columna_exacto.rjust(10)
        linea = linea + str(estimar_tokens(texto)).rjust(10)
        print(linea)

    print()
    print("  Mira: las palabras comunes suelen ser 1 token. Las palabras largas,")
    print("  los acentos y el codigo se parten en varios pedazos. Por eso el mismo")
    print("  texto en espanol sale mas caro que en ingles.")

    if contar_con_tiktoken("prueba", modelo) is None:
        print()
        print("  [nota] tiktoken no sirve con este modelo (o no esta instalada).")
        print("  Es normal si estas usando Gemini: usa su propio sistema de tokens.")

    # -----------------------------------------------------------------------
    titulo("2) EL NUMERO QUE VALE: el campo 'usage'")
    # -----------------------------------------------------------------------
    # Este es el numero por el que realmente te cobran. Los otros dos metodos
    # son estimaciones previas.

    respuesta = conversar(
        cliente,
        [
            {"role": "system", "content": "Respondes corto."},
            {"role": "user", "content": "Explica en tres oraciones que es la ventana de contexto."},
        ],
        temperatura=0.3,
        max_tokens=600,
    )

    print()
    print(obtener_texto(respuesta))
    print()

    tokens_entrada = respuesta.usage.prompt_tokens
    tokens_salida = respuesta.usage.completion_tokens

    # Los tokens de razonamiento no vienen en un campo propio: se deducen.
    razonamiento = respuesta.usage.total_tokens - tokens_entrada - tokens_salida

    if razonamiento < 0:
        razonamiento = 0

    print("  Tokens de entrada (lo que mandaste):    " + str(tokens_entrada))
    print("  Tokens de salida (lo que el escribio):  " + str(tokens_salida))
    print("  Tokens de razonamiento (no los viste):  " + str(razonamiento))
    print("  Total:                                  " + str(respuesta.usage.total_tokens))

    costo = calcular_costo(modelo, tokens_entrada, tokens_salida, razonamiento)

    if costo is None:
        print()
        print("  No tengo cargado el precio de '" + modelo + "'.")
        print("  Podes agregarlo arriba, en el diccionario PRECIOS.")
    else:
        print()
        print("  Costo de esta llamada: " + str(round(costo, 6)) + " dolares")
        print("  Si la hicieras 100.000 veces: " + str(round(costo * 100000, 2)) + " dolares")

        # Mostramos tambien cuanto habrias calculado MAL si te olvidaras del
        # razonamiento. Es la forma mas clara de que se entienda el punto.
        if razonamiento > 0:
            costo_mal = calcular_costo(modelo, tokens_entrada, tokens_salida)
            cuantas_veces = round(costo / costo_mal, 1)

            print()
            print("  Si hubieras contado solo los tokens visibles habrias")
            print("  calculado " + str(round(costo_mal, 6)) + " dolares: " +
                  str(cuantas_veces) + " veces MENOS de lo que")
            print("  realmente vas a pagar. Ese es el error de presupuesto mas")
            print("  comun con los modelos de razonamiento.")

    # -----------------------------------------------------------------------
    titulo("3) LOS TOKENS DE SALIDA SON LOS CAROS")
    # -----------------------------------------------------------------------
    subtitulo("Precio en dolares por millon de tokens")
    print("  Modelo                Entrada    Salida   La salida cuesta")
    print("  " + "-" * 58)

    for nombre_modelo in PRECIOS:
        precio = PRECIOS[nombre_modelo]
        cuantas_veces = round(precio["salida"] / precio["entrada"], 1)

        linea = "  "
        linea = linea + nombre_modelo.ljust(22)
        linea = linea + str(precio["entrada"]).rjust(7)
        linea = linea + str(precio["salida"]).rjust(10)
        linea = linea + (str(cuantas_veces) + " veces mas").rjust(19)
        print(linea)

    print()
    print("  Por eso pedirle respuestas largas o razonamientos extensos impacta")
    print("  mucho mas en el costo que mandarle mas texto de entrada.")

    # -----------------------------------------------------------------------
    titulo("4) EL COSTO ESCONDIDO DE UNA CONVERSACION")
    # -----------------------------------------------------------------------
    # En un chat le volvemos a mandar TODO el historial en cada turno.
    # Entonces cada pregunta nueva es mas cara que la anterior.

    historial = [{"role": "system", "content": "Sos un asistente breve."}]
    entrada_acumulada = 0
    numero_de_turno = 1

    preguntas = [
        "Que es Python?",
        "Y para que se usa?",
        "Dame un ejemplo simple.",
        "Y uno mas avanzado?",
    ]

    for pregunta in preguntas:
        historial.append({"role": "user", "content": pregunta})

        respuesta = conversar(cliente, historial, temperatura=0.3, max_tokens=500)
        historial.append({"role": "assistant", "content": obtener_texto(respuesta)})

        entrada_acumulada = entrada_acumulada + respuesta.usage.prompt_tokens

        print("  Turno " + str(numero_de_turno) +
              ": esta pregunta costo " + str(respuesta.usage.prompt_tokens) +
              " tokens de entrada | acumulado: " + str(entrada_acumulada))

        numero_de_turno = numero_de_turno + 1

    print()
    print("  Fijate como el numero sube en cada turno, aunque las preguntas sean")
    print("  igual de cortas. Es porque se reenvia toda la conversacion.")
    print()
    print("  Como se controla: cortar el historial a los ultimos N turnos, o")
    print("  resumir lo viejo con una llamada barata.")

    # -----------------------------------------------------------------------
    titulo("PARA NO LLEVARTE UNA SORPRESA EN LA FACTURA")
    # -----------------------------------------------------------------------
    print("""
  [ ] Pone siempre max_tokens: es el unico limite duro del costo.
  [ ] Guarda el 'usage' de cada llamada en un archivo de registro.
  [ ] Calcula el costo por usuario ANTES de lanzar, no despues.
  [ ] Usa el modelo mas chico que pase tus pruebas, no el mas nuevo.
  [ ] En chats largos, corta o resumi el historial.
  [ ] Configura un limite de gasto en el panel de tu proveedor.
""")


if __name__ == "__main__":
    main()
