
"""
L2 - Ejercicio 04: pedirle al modelo que responda en formato JSON.

QUE VAMOS A VER
  Como pasar de "el modelo me contesta un parrafo" a "el modelo me devuelve
  datos ordenados que mi programa puede usar".

POR QUE IMPORTA
  Un parrafo es lindo para leer pero inservible para un programa. Si queres
  guardar la respuesta en una base de datos, necesitas campos separados.

QUE ES JSON
  Es una forma de escribir datos que se parece muchisimo a un diccionario de
  Python. Por ejemplo:
      {"nombre": "Lucia", "ambientes": 2, "presupuesto": 900}

CASO DE USO
  Una inmobiliaria recibe consultas por WhatsApp escritas de cualquier manera y
  necesita cargarlas ordenadas en su sistema.

COMO CORRERLO
    python 04_salida_estructurada.py --provider gemini
"""

import json   # esta libreria convierte texto JSON en diccionarios de Python
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import crear_parser
from common.llm import crear_cliente_desde_argumentos, preguntar
from common.ui import mostrar_configuracion, subtitulo, titulo


# Mensajes de ejemplo, escritos como los escribiria una persona real.
MENSAJES_DE_CLIENTES = [
    "Hola! Vi el depto de Palermo. Somos 2, buscamos 2 ambientes hasta 900 dolares. "
    "Me llamo Lucia, mi telefono es 11-5555-1234.",

    "buenas necesito algo en cordoba capital, casa, 3 dormitorios, hasta 150000 usd "
    "para comprar. soy martin, mi mail martin@ejemplo.com",

    "Che, cuanto sale el alquiler de la oficina de microcentro? nada mas eso",
]


# Le explicamos al modelo, en palabras, exactamente que campos queremos.
# Esta descripcion ES el prompt: el modelo la lee para saber que poner.
INSTRUCCIONES = """Sos un asistente de una inmobiliaria. Tu tarea es leer el
mensaje de un cliente y devolver sus datos ordenados.

Devolves SOLAMENTE un JSON con estas claves exactas:

  "nombre"           -> el nombre del cliente, o null si no lo dice
  "contacto"         -> telefono o mail, o null si no lo dice
  "operacion"        -> una de estas tres: "alquiler", "compra", "consulta"
  "tipo_propiedad"   -> "departamento", "casa", "oficina", "local" o null
  "zona"             -> el barrio o la ciudad, o null
  "ambientes"        -> un numero entero, o null
  "presupuesto_usd"  -> un numero, o null
  "resumen"          -> una sola linea para que lea el vendedor

Reglas importantes:
- Si un dato no aparece en el mensaje, pone null. NO lo inventes.
- Usa "consulta" cuando la persona solo pide informacion.
- No escribas nada fuera del JSON. Ni explicaciones, ni ```json.
"""


def convertir_a_diccionario(texto):
    """
    Convierte el texto que devolvio el modelo en un diccionario de Python.

    A veces el modelo envuelve el JSON entre ```json y ```, aunque le hayamos
    pedido que no lo haga. Aca lo limpiamos antes de convertirlo.
    """
    texto = texto.strip()

    if texto.startswith("```"):
        # Partimos el texto por las comillas y nos quedamos con el pedazo del medio.
        partes = texto.split("```")
        texto = partes[1]

        if texto.startswith("json"):
            texto = texto[4:]   # sacamos las primeras 4 letras: "json"

    # json.loads lee un texto en formato JSON y devuelve un diccionario.
    return json.loads(texto)


def revisar_datos(datos):
    """
    Revisa que los datos tengan sentido y devuelve una lista de problemas.

    ESTO ES CLAVE: que el modelo haya devuelto un numero no significa que sea
    el numero correcto. La revision se hace en Python, que no se equivoca ni
    inventa. La lista vacia significa "esta todo bien".
    """
    problemas = []

    operaciones_validas = ["alquiler", "compra", "consulta"]

    if datos["operacion"] not in operaciones_validas:
        problemas.append("la operacion no es una de las tres permitidas")

    presupuesto = datos["presupuesto_usd"]

    if presupuesto is not None:
        if presupuesto <= 0 or presupuesto > 10000000:
            problemas.append("el presupuesto es un numero raro")

    ambientes = datos["ambientes"]

    if ambientes is not None:
        if ambientes <= 0 or ambientes > 20:
            problemas.append("la cantidad de ambientes es rara")

    # Si quiere alquilar o comprar pero no dejo contacto, no podemos llamarlo.
    if datos["operacion"] != "consulta" and datos["contacto"] is None:
        problemas.append("falta el contacto del cliente")

    return problemas


def main():
    parser = crear_parser("Pedirle al modelo datos ordenados en formato JSON")
    args = parser.parse_args()

    try:
        cliente = crear_cliente_desde_argumentos(args)
    except ValueError as error:
        print(error)
        return

    mostrar_configuracion(cliente)
    titulo("Convertir mensajes de WhatsApp en datos ordenados")

    numero = 1

    for mensaje in MENSAJES_DE_CLIENTES:

        subtitulo("Mensaje " + str(numero))
        print("Lo que escribio el cliente:")
        print("  " + mensaje)
        print()

        # response_format le pide al servidor que la respuesta sea JSON valido.
        # Funciona tanto en OpenAI como en Gemini.
        respuesta = preguntar(
            cliente,
            mensaje,
            sistema=INSTRUCCIONES,
            temperatura=0,
            response_format={"type": "json_object"},
        )

        try:
            datos = convertir_a_diccionario(respuesta)
        except json.JSONDecodeError:
            print("  [ERROR] el modelo no devolvio un JSON valido. Respondio esto:")
            print("  " + respuesta)
            numero = numero + 1
            continue   # "continue" salta al siguiente mensaje del for

        print("Lo que entendio el modelo:")

        # Recorremos el diccionario mostrando cada clave con su valor.
        for clave in datos:
            print("  " + clave + ": " + str(datos[clave]))

        print()

        problemas = revisar_datos(datos)

        if len(problemas) == 0:
            print("  [revision] Todo bien. Se puede guardar en la base de datos.")
        else:
            print("  [revision] Necesita que lo mire una persona porque:")
            for problema in problemas:
                print("     - " + problema)

        numero = numero + 1

    titulo("LO IMPORTANTE DE ESTE EJERCICIO")
    print("""
  1. Describir bien cada campo es parte del prompt: el modelo lee esa
     descripcion para saber que poner.

  2. Deja siempre la opcion de null. Si obligas a llenar todos los campos,
     el modelo va a inventar datos para no dejarlos vacios.

  3. Revisa SIEMPRE los datos en Python. El formato correcto no garantiza
     que el contenido sea correcto.
""")


if __name__ == "__main__":
    main()
