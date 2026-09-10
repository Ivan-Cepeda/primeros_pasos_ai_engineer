"""
Configuracion del proyecto: credenciales, proveedor y modelo.

Decision de diseno: las credenciales NUNCA estan en el codigo. Se leen de
variables de entorno, que en desarrollo cargamos desde un archivo .env que no
se sube al repositorio. En produccion las inyecta el servidor y el codigo no
cambia una linea.

La consigna pide usar la API de OpenAI. Este proyecto la soporta y ademas
permite usar Google Gemini con el mismo codigo, cambiando una sola variable de
entorno. El motivo esta explicado en el README y en el reporte.
"""

import argparse
import os

from dotenv import load_dotenv


# Catalogo de proveedores soportados.
#
# "base_url" es lo que permite que el mismo cliente sirva para los dos: el SDK
# de OpenAI es un cliente del protocolo /chat/completions, y Google publica ese
# mismo protocolo para Gemini en una URL de compatibilidad.
PROVEEDORES = {
    "openai": {
        "variable_clave": "OPENAI_API_KEY",
        "variable_modelo": "OPENAI_MODEL",
        "modelo_por_defecto": "gpt-4o-mini",
        "base_url": None,   # None = la URL de fabrica del SDK (OpenAI)
        "donde_conseguir_clave": "https://platform.openai.com/api-keys",
    },
    "gemini": {
        "variable_clave": "GEMINI_API_KEY",
        "variable_modelo": "GEMINI_MODEL",
        "modelo_por_defecto": "gemini-3.7-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "donde_conseguir_clave": "https://aistudio.google.com/apikey",
    },
}


# ---------------------------------------------------------------------------
# Parametros de la llamada al modelo.
#
# La guia del proyecto pide elegirlos de forma deliberada y dejar registro del
# por que. Aca esta el por que de cada uno:
# ---------------------------------------------------------------------------

# temperature=0: la tarea es clasificar y estructurar, no redactar creativamente.
# Queremos que la misma pregunta devuelva siempre la misma respuesta, porque el
# resultado alimenta a otros sistemas que no toleran variaciones.
TEMPERATURA = 0

# max_tokens generoso a proposito. Los modelos de razonamiento de 2026 gastan
# tokens pensando ANTES de escribir, y este limite cubre pensamiento + respuesta
# juntos. Con un valor chico el modelo se queda sin margen y devuelve texto
# vacio. Medido con gemini-3.7-flash: hasta 400 tokens de pensamiento para una
# respuesta de 60 tokens visibles.
MAX_TOKENS = 1200

# Cortamos la espera para que la aplicacion no se cuelgue si el proveedor tarda.
TIMEOUT_SEGUNDOS = 30

# Cuantas veces reintentamos ante errores pasajeros (429, 5xx, red).
REINTENTOS = 3


class ErrorDeConfiguracion(Exception):
    """Se lanza cuando falta una credencial o el proveedor es invalido."""


def cargar_configuracion(proveedor=None, modelo=None):
    """
    Resuelve con que proveedor y modelo se va a trabajar.

    Prioridad, de mayor a menor:
      1. Lo que se pasa por linea de comandos (--provider / --model)
      2. Lo que dice el archivo .env
      3. El valor por defecto de este archivo

    Devuelve un diccionario con proveedor, clave, modelo y base_url.
    """
    load_dotenv()

    if proveedor is None:
        proveedor = os.getenv("LLM_PROVIDER")
    if proveedor is None:
        proveedor = "openai"

    proveedor = proveedor.strip().lower()

    if proveedor not in PROVEEDORES:
        raise ErrorDeConfiguracion(
            "Proveedor desconocido: '" + proveedor + "'. Opciones: openai, gemini"
        )

    datos = PROVEEDORES[proveedor]
    clave = os.getenv(datos["variable_clave"])

    if not clave:
        raise ErrorDeConfiguracion(
            "\nFalta la variable " + datos["variable_clave"] + " para usar " + proveedor + ".\n"
            "  1) Copia .env.example a .env\n"
            "  2) Pega tu clave en " + datos["variable_clave"] + "=\n"
            "  3) Conseguis una clave en: " + datos["donde_conseguir_clave"] + "\n"
        )

    if modelo is None:
        modelo = os.getenv(datos["variable_modelo"])
    if modelo is None:
        modelo = datos["modelo_por_defecto"]

    return {
        "proveedor": proveedor,
        "clave": clave,
        "modelo": modelo,
        "base_url": datos["base_url"],
    }


def crear_parser():
    """Argumentos de linea de comandos de la aplicacion."""
    parser = argparse.ArgumentParser(
        description="Asistente de soporte: recibe una pregunta y devuelve JSON estructurado."
    )
    parser.add_argument(
        "pregunta",
        nargs="?",
        default=None,
        help="La pregunta del usuario. Si no la escribis, se te va a pedir.",
    )
    parser.add_argument(
        "--provider",
        choices=sorted(PROVEEDORES),
        default=None,
        help="Proveedor de LLM. Por defecto toma LLM_PROVIDER del .env",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Modelo especifico. Por defecto toma el del .env",
    )
    parser.add_argument(
        "--sin-metricas",
        action="store_true",
        help="No guardar esta ejecucion en metrics/",
    )
    parser.add_argument(
        "--sin-seguridad",
        action="store_true",
        help="Saltear la capa de seguridad (solo para comparar en las pruebas)",
    )
    return parser
