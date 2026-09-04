"""
Configuracion y gestion de credenciales.

Regla de oro: las API keys NUNCA se escriben dentro del codigo.
Se leen de "variables de entorno", que son valores que viven fuera del programa.
En desarrollo las cargamos desde un archivo llamado .env (que no se sube a
internet). Asi el codigo se puede compartir sin regalar tus claves.
"""

import argparse
import os

from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Catalogo de proveedores.
#
# Esto es un diccionario: una estructura de Python que guarda pares
# "clave: valor". Aca la clave es el nombre del proveedor ("openai" o "gemini")
# y el valor es otro diccionario con los datos de ese proveedor.
#
# El dato importante es "base_url": es la direccion de internet a la que se le
# hacen las preguntas. Cambiando esa direccion, la MISMA libreria de Python
# sirve para hablar con OpenAI o con Gemini.
# ---------------------------------------------------------------------------
PROVEEDORES = {
    "openai": {
        "nombre_variable_clave": "OPENAI_API_KEY",
        "nombre_variable_modelo": "OPENAI_MODEL",
        "modelo_por_defecto": "gpt-4o-mini",
        # None significa "usar la direccion que la libreria trae de fabrica",
        # que es justamente la de OpenAI.
        "base_url": None,
        "donde_conseguir_clave": "https://platform.openai.com/api-keys",
    },
    "gemini": {
        "nombre_variable_clave": "GEMINI_API_KEY",
        "nombre_variable_modelo": "GEMINI_MODEL",
        "modelo_por_defecto": "gemini-3.7-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "donde_conseguir_clave": "https://aistudio.google.com/apikey",
    },
}


def cargar_configuracion(proveedor=None, modelo=None):
    """
    Averigua con que proveedor y con que modelo vamos a trabajar.

    Devuelve un diccionario con cuatro datos: proveedor, clave, modelo y base_url.

    El orden en que se decide es (de mayor a menor prioridad):
      1. Lo que se pasa por linea de comandos (--provider / --model)
      2. Lo que dice el archivo .env
      3. El valor por defecto que esta escrito aca arriba
    """
    # load_dotenv lee el archivo .env y mete sus valores en las variables de
    # entorno del programa. Despues de esta linea, os.getenv puede verlos.
    load_dotenv()

    # El operador "or" en Python devuelve el primer valor que no este vacio.
    # Entonces esta linea significa: "usa el proveedor que me pasaron; si no me
    # pasaron ninguno, usa el del .env; y si tampoco hay, usa 'openai'".
    if proveedor is None:
        proveedor = os.getenv("LLM_PROVIDER")
    if proveedor is None:
        proveedor = "openai"

    proveedor = proveedor.lower().strip()

    if proveedor not in PROVEEDORES:
        raise ValueError(
            "Proveedor desconocido: '" + proveedor + "'. Las opciones son: openai, gemini"
        )

    datos = PROVEEDORES[proveedor]

    # Buscamos la clave en las variables de entorno.
    clave = os.getenv(datos["nombre_variable_clave"])

    if not clave:
        # Cuando algo falta, es mejor un mensaje que explique como arreglarlo
        # que un error tecnico que no le dice nada al que recien empieza.
        raise ValueError(
            "\nFalta la clave " + datos["nombre_variable_clave"] + " para usar " + proveedor + ".\n"
            "Para arreglarlo:\n"
            "  1) Copia el archivo .env.example y llamalo .env\n"
            "  2) Pega tu clave en la linea " + datos["nombre_variable_clave"] + "=\n"
            "  3) Conseguis una clave gratis en: " + datos["donde_conseguir_clave"] + "\n"
        )

    # Si no nos pasaron un modelo, buscamos el del .env; si tampoco hay, el default.
    if modelo is None:
        modelo = os.getenv(datos["nombre_variable_modelo"])
    if modelo is None:
        modelo = datos["modelo_por_defecto"]

    return {
        "proveedor": proveedor,
        "clave": clave,
        "modelo": modelo,
        "base_url": datos["base_url"],
    }


def crear_parser(descripcion):
    """
    Prepara los argumentos que se pueden escribir en la terminal.

    Gracias a esto, cualquier ejercicio se puede correr con cualquier proveedor
    sin editar ni una linea de codigo:

        python 01_primer_llamado.py --provider gemini
        python 01_primer_llamado.py --provider openai --model gpt-4o
    """
    parser = argparse.ArgumentParser(description=descripcion)
    parser.add_argument(
        "--provider",
        choices=["openai", "gemini"],
        default=None,
        help="Que proveedor usar. Si no lo escribis, se usa el del archivo .env",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Que modelo usar. Si no lo escribis, se usa el del archivo .env",
    )
    return parser
