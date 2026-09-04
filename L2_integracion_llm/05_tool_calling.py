"""
L2 - Ejercicio 05: darle herramientas al modelo (tool calling).

LA IDEA EN UNA FRASE
  El modelo no puede ejecutar nada. Lo unico que hace es decir:
  "para responder esto, necesito que ejecutes TU la funcion X con estos datos".

POR QUE HACE FALTA
  Un modelo de lenguaje no sabe que dia es hoy, no conoce tu base de datos y
  se equivoca haciendo cuentas. Todo eso lo resuelve Python perfecto. Entonces:
  el modelo entiende lo que pide el usuario, y Python hace el trabajo exacto.

CASO DE USO
  El asistente de una tienda de muebles de oficina: consulta stock, calcula el
  envio y agenda visitas.

COMO CORRERLO
    python 05_tool_calling.py --provider gemini
    python 05_tool_calling.py --pregunta "tienen sillas ergonomicas?"
"""

import datetime   # para saber la fecha de hoy
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import crear_parser
from common.llm import crear_cliente_desde_argumentos, usar_herramientas
from common.ui import mostrar_configuracion, subtitulo, titulo


# ---------------------------------------------------------------------------
# PASO 1: los datos de la tienda.
# En un proyecto real esto saldria de una base de datos. Para el ejercicio lo
# dejamos escrito aca para que se entienda mejor.
# ---------------------------------------------------------------------------
CATALOGO = {
    "SKU-100": {"nombre": "Silla ergonomica Aura",      "precio": 240, "stock": 12, "peso": 14.5},
    "SKU-200": {"nombre": "Escritorio regulable Nordic", "precio": 620, "stock": 3,  "peso": 38.0},
    "SKU-300": {"nombre": "Monitor 27 pulgadas Vista",   "precio": 310, "stock": 0,  "peso": 6.2},
}

PRECIOS_DE_ENVIO = {"CABA": 8, "GBA": 14, "INTERIOR": 26}


# ---------------------------------------------------------------------------
# PASO 2: las funciones de Python. Son funciones normales y corrientes.
# ---------------------------------------------------------------------------

def buscar_producto(consulta):
    """Busca productos cuyo nombre o codigo contenga lo que se pidio."""

    texto_buscado = consulta.lower().strip()
    encontrados = []

    # .items() nos deja recorrer un diccionario obteniendo clave y valor a la vez.
    for codigo, producto in CATALOGO.items():

        if texto_buscado in codigo.lower() or texto_buscado in producto["nombre"].lower():
            # Armamos un diccionario nuevo que incluye el codigo.
            resultado = {
                "codigo": codigo,
                "nombre": producto["nombre"],
                "precio": producto["precio"],
                "stock": producto["stock"],
                "peso": producto["peso"],
            }
            encontrados.append(resultado)

    # Devolver una lista vacia esta bien: el modelo va a poder decir
    # "no encontre nada" en vez de inventar un producto.
    return encontrados


def calcular_envio(peso_total, zona, subtotal):
    """
    Calcula cuanto sale el envio.

    ACA ESTA EL PUNTO DEL EJERCICIO: esta cuenta la hace Python, no el modelo.
    Python nunca se equivoca sumando. El modelo, a veces si.
    """
    if subtotal >= 500:
        return {"costo": 0, "motivo": "envio gratis por compra mayor a 500 dolares"}

    zona = zona.upper()

    if zona in PRECIOS_DE_ENVIO:
        precio_base = PRECIOS_DE_ENVIO[zona]
    else:
        precio_base = PRECIOS_DE_ENVIO["INTERIOR"]

    costo = precio_base + peso_total * 0.35

    return {"costo": round(costo, 2), "motivo": "tarifa de " + zona + " mas 0.35 por kilo"}


def fecha_de_hoy():
    """
    Devuelve la fecha actual.

    Un modelo no sabe que dia es hoy: su conocimiento quedo congelado el dia que
    lo entrenaron. Todo lo que dependa del presente necesita una herramienta.
    """
    hoy = datetime.date.today()

    return {"fecha": str(hoy), "dia_de_la_semana": hoy.strftime("%A")}


def agendar_visita(nombre_cliente, fecha):
    """
    Agenda una visita al showroom.

    OJO CON ESTAS: esta funcion MODIFICA algo del mundo real. Con las funciones
    que solo consultan datos podes ser relajado; con las que escriben, no.
    Siempre hay que validar los datos antes de hacer nada.
    """
    try:
        fecha_pedida = datetime.date.fromisoformat(fecha)
    except ValueError:
        return {"ok": False, "error": "la fecha tiene que estar escrita como AAAA-MM-DD"}

    if fecha_pedida < datetime.date.today():
        return {"ok": False, "error": "no se puede agendar una visita en el pasado"}

    return {"ok": True, "codigo_de_reserva": "VIS-" + fecha.replace("-", "")}


# ---------------------------------------------------------------------------
# PASO 3: describirle las funciones al modelo.
#
# El modelo no puede leer nuestro codigo Python. Necesita una descripcion en un
# formato fijo. Es largo y repetitivo, pero se entiende leyendolo:
#
#   "name"        -> como se llama la funcion
#   "description" -> PARA QUE SIRVE. Esto es lo mas importante de todo: es el
#                    texto con el que el modelo decide si la usa o no.
#   "parameters"  -> que datos necesita
#   "required"    -> cuales de esos datos son obligatorios
# ---------------------------------------------------------------------------
HERRAMIENTAS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_producto",
            "description": (
                "Busca productos en el catalogo por nombre o por codigo. Devuelve "
                "precio, stock y peso. Usala SIEMPRE antes de decir si hay stock "
                "de algo: nunca respondas de memoria."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "consulta": {
                        "type": "string",
                        "description": "Texto a buscar, por ejemplo 'silla' o 'SKU-100'",
                    },
                },
                "required": ["consulta"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calcular_envio",
            "description": (
                "Calcula cuanto cuesta el envio de un pedido. Necesita el peso "
                "total, la zona de entrega y el subtotal del pedido en dolares."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "peso_total": {
                        "type": "number",
                        "description": "Peso total del pedido en kilos",
                    },
                    "zona": {
                        "type": "string",
                        "enum": ["CABA", "GBA", "INTERIOR"],
                        "description": "Zona de entrega",
                    },
                    "subtotal": {
                        "type": "number",
                        "description": "Subtotal del pedido en dolares",
                    },
                },
                "required": ["peso_total", "zona", "subtotal"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fecha_de_hoy",
            "description": "Devuelve la fecha de hoy. Usala si necesitas saber que dia es.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "agendar_visita",
            "description": (
                "Agenda una visita al showroom. Usala solo cuando el cliente ya "
                "dijo su nombre y confirmo el dia."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre_cliente": {"type": "string"},
                    "fecha": {
                        "type": "string",
                        "description": "Fecha de la visita, escrita como AAAA-MM-DD",
                    },
                },
                "required": ["nombre_cliente", "fecha"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# PASO 4: conectar cada nombre con su funcion de Python.
#
# Cuando el modelo diga "quiero usar buscar_producto", este diccionario nos
# dice que funcion tenemos que ejecutar.
# ---------------------------------------------------------------------------
FUNCIONES = {
    "buscar_producto": buscar_producto,
    "calcular_envio": calcular_envio,
    "fecha_de_hoy": fecha_de_hoy,
    "agendar_visita": agendar_visita,
}


INSTRUCCIONES = (
    "Sos el asistente de ventas de una tienda de muebles de oficina. "
    "Usas las herramientas para conseguir datos reales: no inventas precios, "
    "stock ni fechas. Si una busqueda no encuentra nada, lo decis. "
    "Respondes en espanol, corto y concreto."
)

PREGUNTAS_DE_EJEMPLO = [
    "Hola, tienen sillas ergonomicas? Cuanto salen y hay stock?",
    "Quiero 2 sillas ergonomicas y un monitor. Cuanto me sale el envio a GBA?",
    "Que dia es hoy?",
    "Cual es la capital de Francia?",   # esta NO necesita ninguna herramienta
]


def main():
    parser = crear_parser("Darle herramientas al modelo")
    parser.add_argument("--pregunta", default=None, help="Hacer una pregunta puntual")
    args = parser.parse_args()

    try:
        cliente = crear_cliente_desde_argumentos(args)
    except ValueError as error:
        print(error)
        return

    mostrar_configuracion(cliente)
    print("[herramientas] hay " + str(len(HERRAMIENTAS)) + " funciones disponibles.")

    if args.pregunta is not None:
        preguntas = [args.pregunta]
    else:
        preguntas = PREGUNTAS_DE_EJEMPLO

    for pregunta in preguntas:

        titulo("Usuario: " + pregunta)

        mensajes = [
            {"role": "system", "content": INSTRUCCIONES},
            {"role": "user", "content": pregunta},
        ]

        # Esta funcion (esta en common/llm.py) hace todo el ida y vuelta:
        # le pregunta al modelo, ejecuta lo que pida, le devuelve el resultado
        # y repite hasta que conteste con texto.
        respuesta, historial = usar_herramientas(cliente, mensajes, HERRAMIENTAS, FUNCIONES)

        print()
        print("Asistente: " + respuesta)

    subtitulo("QUE MIRAR EN LA SALIDA")
    print("""
  * La ultima pregunta (la capital de Francia) NO usa ninguna herramienta.
    El modelo decide solo cuando las necesita, leyendo las descripciones.

  * En la pregunta del envio suele usar DOS herramientas seguidas: primero
    busca los productos, y con el peso y el precio reales calcula el envio.

  * Todo lo que se ejecuta pasa por tu codigo. El modelo solo propone.
""")


if __name__ == "__main__":
    main()
