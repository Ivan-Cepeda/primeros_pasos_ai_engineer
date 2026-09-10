"""
Punto de entrada de la aplicacion.

FLUJO COMPLETO
    pregunta del usuario
      -> 1. capa de seguridad de entrada  (patrones y datos personales)
      -> 2. armado del prompt             (plantilla + few-shot + contrato)
      -> 3. llamada al modelo             (con reintentos y timeout)
      -> 4. parseo y validacion del JSON  (nunca confiamos en la forma)
      -> 5. reglas de negocio             (umbral de confianza)
      -> 6. capa de seguridad de salida   (no filtrar instrucciones)
      -> 7. registro de metricas
    JSON valido por stdout

Cualquiera de los pasos puede cortar el flujo, pero la salida SIEMPRE respeta
el contrato: quien nos consume recibe los mismos campos pase lo que pase.

COMO CORRERLO
    python -m src.run_query "mi pregunta"
    python -m src.run_query "mi pregunta" --provider gemini
    python -m src.run_query --resumen
"""

import json
import os
import sys

# Permite ejecutar el archivo directamente ademas de con "python -m".
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import config, llm_client, metrics, safety, schema


CARPETA_DEL_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVO_DE_PROMPT = os.path.join(CARPETA_DEL_PROYECTO, "prompts", "main_prompt.txt")


def cargar_prompt():
    """
    Lee la plantilla del prompt desde prompts/main_prompt.txt.

    POR QUE EL PROMPT VIVE EN UN ARCHIVO Y NO EN EL CODIGO
      Un prompt se itera: se prueba, se ajusta, se vuelve a probar. Tenerlo
      afuera permite cambiarlo sin tocar Python, verlo entero de un vistazo y
      ver su historial de cambios en git como cualquier otro archivo.

    El marcador {SCHEMA} se reemplaza por la descripcion del contrato, que vive
    en schema.py. Asi el contrato se define en UN solo lugar: si manana se
    agrega un campo, el prompt se entera solo.
    """
    with open(ARCHIVO_DE_PROMPT, "r", encoding="utf-8") as archivo:
        plantilla = archivo.read()

    return plantilla.replace("{SCHEMA}", schema.DESCRIPCION_DEL_CONTRATO)


def procesar(cliente, pregunta, aplicar_seguridad=True):
    """
    Hace pasar una pregunta por todo el flujo.

    Devuelve (resultado, metricas, informe_de_seguridad).
    El resultado SIEMPRE cumple el contrato, incluso cuando algo falla.
    """
    # --- PASO 1: seguridad de entrada -------------------------------------
    if aplicar_seguridad:
        informe = safety.analizar_entrada(pregunta)
        pregunta_para_el_modelo = informe["texto_limpio"]

        if len(informe["patrones_de_manipulacion"]) > 0:
            print("  [seguridad] patrones de manipulacion detectados: " +
                  str(informe["patrones_de_manipulacion"]), file=sys.stderr)

        if informe["datos_personales_redactados"] > 0:
            print("  [seguridad] " + str(informe["datos_personales_redactados"]) +
                  " dato(s) personal(es) redactado(s) antes de enviar", file=sys.stderr)
    else:
        informe = {"patrones_de_manipulacion": [], "datos_personales_redactados": 0,
                   "sospechosa": False}
        pregunta_para_el_modelo = pregunta

    # --- PASO 2: armado del prompt ----------------------------------------
    # La consulta va delimitada para que el modelo sepa donde empieza y termina
    # el texto que no controlamos.
    mensajes = [
        {"role": "system", "content": cargar_prompt()},
        {"role": "user", "content": safety.marcar_como_no_confiable(pregunta_para_el_modelo)},
    ]

    # --- PASO 3: llamada al modelo ----------------------------------------
    try:
        texto, metricas_de_la_llamada = llm_client.preguntar(cliente, mensajes)
    except llm_client.ErrorDelModelo as error:
        return schema.respuesta_de_emergencia(str(error)), {}, informe

    # --- PASO 4: parseo y validacion --------------------------------------
    try:
        datos = schema.parsear(texto)
    except ValueError as error:
        metricas_de_la_llamada["json_valido"] = False
        return schema.respuesta_de_emergencia(str(error)), metricas_de_la_llamada, informe

    problemas = schema.validar(datos)

    if len(problemas) > 0:
        # El modelo devolvio JSON pero no cumple el contrato. No lo dejamos
        # pasar: el sistema que nos consume espera estos campos exactos.
        metricas_de_la_llamada["json_valido"] = False
        resultado = schema.respuesta_de_emergencia(
            "el JSON no cumple el contrato: " + "; ".join(problemas)
        )
        return resultado, metricas_de_la_llamada, informe

    metricas_de_la_llamada["json_valido"] = True

    # --- PASO 5: reglas de negocio ----------------------------------------
    datos, reglas = schema.aplicar_reglas_de_negocio(datos)

    for regla in reglas:
        print("  [regla] " + regla, file=sys.stderr)

    # --- PASO 6: seguridad de salida --------------------------------------
    if aplicar_seguridad:
        es_segura, motivo = safety.revisar_respuesta(datos["answer"])

        if not es_segura:
            print("  [seguridad] " + motivo, file=sys.stderr)
            return schema.respuesta_de_emergencia(motivo), metricas_de_la_llamada, informe

    return datos, metricas_de_la_llamada, informe


def mostrar_resumen():
    """Imprime las metricas acumuladas de todas las ejecuciones."""
    resumen = metrics.resumir()

    if resumen is None:
        print("Todavia no hay metricas registradas. Corre una consulta primero.")
        return

    print()
    print("RESUMEN DE METRICAS")
    print("-" * 54)
    print("  Ejecuciones registradas : " + str(resumen["ejecuciones"]))
    print("  Con JSON valido         : " + str(resumen["json_valido"]) +
          " (" + str(resumen["porcentaje_json_valido"]) + "%)")
    print("  Marcadas por seguridad  : " + str(resumen["marcadas_por_seguridad"]))
    print("  Latencia mediana        : " + str(resumen["latencia_mediana_ms"]) + " ms")
    print("  Latencia p95            : " + str(resumen["latencia_p95_ms"]) + " ms")
    print("  Tokens totales          : " + str(resumen["tokens_totales"]))
    print("  Costo acumulado         : " + str(resumen["costo_total_usd"]) + " USD")
    print("  Costo promedio          : " + str(resumen["costo_promedio_usd"]) + " USD")
    print()
    print("  Archivo: " + metrics.ARCHIVO_CSV)


def main():
    parser = config.crear_parser()
    parser.add_argument(
        "--resumen",
        action="store_true",
        help="Mostrar las metricas acumuladas y salir",
    )
    args = parser.parse_args()

    if args.resumen:
        mostrar_resumen()
        return 0

    pregunta = args.pregunta

    if pregunta is None:
        pregunta = input("Consulta del cliente: ").strip()

    if len(pregunta) == 0:
        print("No escribiste ninguna consulta.", file=sys.stderr)
        return 1

    try:
        cliente = llm_client.crear_cliente(args.provider, args.model)
    except config.ErrorDeConfiguracion as error:
        print(error, file=sys.stderr)
        return 1

    # stderr para todo lo informativo, stdout SOLO para el JSON. Asi la salida
    # se puede redirigir a un archivo o encadenar con otro programa sin que se
    # mezcle con los mensajes de diagnostico.
    print("  [config] " + cliente["proveedor"] + " / " + cliente["modelo"], file=sys.stderr)

    resultado, metricas_de_la_llamada, informe = procesar(
        cliente, pregunta, aplicar_seguridad=not args.sin_seguridad
    )

    # --- PASO 7: registro de metricas -------------------------------------
    if not args.sin_metricas and len(metricas_de_la_llamada) > 0:
        fila = metrics.registrar(
            metricas_de_la_llamada,
            {
                "json_valido": metricas_de_la_llamada.get("json_valido", False),
                "requires_human": resultado.get("requires_human", True),
                "confidence": resultado.get("confidence", 0.0),
            },
            pregunta,
            informe["sospechosa"],
        )

        costo = fila["estimated_cost_usd"]
        if costo == "" or costo is None:
            costo_texto = "sin precio cargado para este modelo"
        else:
            costo_texto = str(costo) + " USD"

        print("  [metricas] " +
              str(metricas_de_la_llamada["total_tokens"]) + " tokens | " +
              str(metricas_de_la_llamada["latency_ms"]) + " ms | " +
              costo_texto, file=sys.stderr)

        if metricas_de_la_llamada.get("tokens_reasoning", 0) > 0:
            print("  [metricas] de esos, " +
                  str(metricas_de_la_llamada["tokens_reasoning"]) +
                  " fueron razonamiento interno que no ves pero se factura",
                  file=sys.stderr)

    # La salida del programa: JSON y nada mas.
    print(json.dumps(resultado, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
