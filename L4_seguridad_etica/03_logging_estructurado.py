"""
L4 - Ejercicio 03: guardar registro de todo lo que pasa.

EL PROBLEMA
  Un print() sirve mientras programas en tu maquina. Cuando la aplicacion esta
  funcionando para usuarios de verdad, necesitas poder responder preguntas
  como: cuanto gaste ayer? por que se quejo este usuario? esta mas lenta que la
  semana pasada?

  Para eso hay que guardar cada llamada en un archivo, de forma ordenada.

POR QUE EN FORMATO JSON Y NO TEXTO COMUN
  Porque un programa puede leer JSON y sacar cuentas. Con texto suelto solo
  podes buscar palabras a ojo.

COMO CORRERLO
    python 03_logging_estructurado.py --provider gemini

Y despues mira el archivo que se genero:
    type ..\\logs\\llm.jsonl     (Windows)
    cat ../logs/llm.jsonl        (Linux o Mac)
"""

import datetime
import json
import os
import re      # re sirve para buscar patrones dentro de un texto
import sys
import time
import uuid    # uuid genera codigos unicos, sin repetirse nunca

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import crear_parser
from common.llm import conversar, crear_cliente_desde_argumentos, obtener_texto
from common.ui import mostrar_configuracion, subtitulo, titulo


# Armamos la ruta del archivo donde vamos a guardar todo.
CARPETA_DEL_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARPETA_DE_LOGS = os.path.join(CARPETA_DEL_PROYECTO, "logs")
ARCHIVO_DE_LOG = os.path.join(CARPETA_DE_LOGS, "llm.jsonl")

# La extension .jsonl significa "un JSON por linea". Es el formato estandar
# para este tipo de archivos porque se puede ir agregando al final sin tener
# que reescribir todo.


# Precios en dolares por millon de tokens, verificados en septiembre de 2026.
# Ojo: los Gemini 3.6/3.7/3.8 tienen precio promocional hasta el 31/12/2026 y
# despues se duplica. La explicacion completa esta en L3, ejercicio 05.
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


# ---------------------------------------------------------------------------
# Tapar los datos sensibles antes de guardarlos.
#
# POR QUE: los archivos de log se copian, se respaldan y los lee mucha mas
# gente que la base de datos. Nunca deben tener datos personales a la vista.
#
# Cada linea de abajo es un patron y el texto por el que lo reemplazamos.
# ---------------------------------------------------------------------------
PATRONES_A_TAPAR = [
    ["\\b\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}\\b", "[TARJETA]"],
    ["\\b[\\w.+-]+@[\\w-]+\\.[\\w.]+\\b", "[EMAIL]"],
    ["\\b\\d{7,8}\\b", "[DOCUMENTO]"],
]


def tapar_datos_sensibles(texto):
    """Reemplaza tarjetas, mails y documentos por una etiqueta generica."""

    for patron in PATRONES_A_TAPAR:
        expresion = patron[0]
        reemplazo = patron[1]

        # re.sub busca todo lo que coincida con el patron y lo reemplaza.
        texto = re.sub(expresion, reemplazo, texto)

    return texto


def acortar(texto, limite=300):
    """
    Recorta los textos largos.

    Guardar los prompts completos hace que el archivo crezca muchisimo (y en un
    servicio real, que la factura del sistema de logs crezca tambien). Guardamos
    una muestra que alcance para entender que paso.
    """
    if len(texto) <= limite:
        return texto

    cuantos_faltan = len(texto) - limite

    return texto[:limite] + "...[+" + str(cuantos_faltan) + " caracteres mas]"


def guardar_evento(datos):
    """
    Escribe una linea nueva en el archivo de log.

    Cada linea es un JSON completo e independiente.
    """
    # exist_ok=True significa "si la carpeta ya existe, no pasa nada".
    os.makedirs(CARPETA_DE_LOGS, exist_ok=True)

    # Le agregamos la fecha y hora al principio de todo.
    # Usamos hora UTC (la hora universal) para poder comparar registros de
    # servidores que estan en paises distintos.
    ahora = datetime.datetime.now(datetime.timezone.utc)
    evento = {"momento": ahora.isoformat()}

    # update agrega al diccionario todas las claves de "datos".
    evento.update(datos)

    # "a" significa "append": agregar al final sin borrar lo que ya estaba.
    archivo = open(ARCHIVO_DE_LOG, "a", encoding="utf-8")
    archivo.write(json.dumps(evento, ensure_ascii=False) + "\n")
    archivo.close()


def calcular_costo(modelo, tokens_entrada, tokens_salida, tokens_de_razonamiento=0):
    """
    Calcula el costo de una llamada, o None si no conocemos el precio.

    OJO: los tokens que el modelo gasta pensando por dentro tambien se
    facturan, y al precio de SALIDA, que es el caro. Si no los sumas, tu
    tablero de costos te va a mentir por varias veces. Ver L3, ejercicio 05.
    """
    if modelo not in PRECIOS:
        return None

    precio = PRECIOS[modelo]

    salida_facturada = tokens_salida + tokens_de_razonamiento

    return round(
        tokens_entrada / 1000000 * precio["entrada"] +
        salida_facturada / 1000000 * precio["salida"],
        6,
    )


def llamar_y_registrar(cliente, prompt, usuario, funcionalidad, id_de_operacion):
    """
    Hace una llamada al modelo y guarda todo lo que paso.

    LOS IDENTIFICADORES son lo que convierte lineas sueltas en una historia:

      id_de_operacion -> une todas las llamadas de una misma accion del usuario
      usuario         -> te permite investigar una queja concreta
      funcionalidad   -> te permite saber que parte de tu producto gasta mas
    """
    # Datos que van a estar en todos los registros de esta llamada.
    datos_comunes = {
        "id_de_operacion": id_de_operacion,
        "usuario": usuario,
        "funcionalidad": funcionalidad,
        "proveedor": cliente["proveedor"],
        "modelo": cliente["modelo"],
    }

    # Registro 1: estamos por llamar.
    evento_de_pedido = {"evento": "pedido"}
    evento_de_pedido.update(datos_comunes)
    evento_de_pedido["prompt"] = acortar(tapar_datos_sensibles(prompt))
    guardar_evento(evento_de_pedido)

    momento_inicial = time.time()

    try:
        respuesta = conversar(
            cliente,
            [{"role": "user", "content": prompt}],
            temperatura=0.3,
            max_tokens=1000,
        )
    except Exception as error:
        # Registro 2 (version error): tambien se guarda, y en el mismo formato.
        evento_de_error = {"evento": "error"}
        evento_de_error.update(datos_comunes)
        evento_de_error["milisegundos"] = round((time.time() - momento_inicial) * 1000)
        evento_de_error["tipo_de_error"] = type(error).__name__
        evento_de_error["detalle"] = str(error)[:200]
        guardar_evento(evento_de_error)

        # Volvemos a lanzar el error para que quien nos llamo se entere.
        raise

    milisegundos = round((time.time() - momento_inicial) * 1000)
    texto = obtener_texto(respuesta)

    # Registro 2 (version exito): con todas las metricas.
    evento_de_respuesta = {"evento": "respuesta"}
    evento_de_respuesta.update(datos_comunes)
    evento_de_respuesta["milisegundos"] = milisegundos
    # Los tokens de razonamiento no vienen en un campo propio: se deducen
    # restando. Los guardamos aparte porque son informacion valiosa: si un dia
    # se disparan, tu factura sube sin que hayas cambiado nada del codigo.
    razonamiento = (respuesta.usage.total_tokens
                    - respuesta.usage.prompt_tokens
                    - respuesta.usage.completion_tokens)

    if razonamiento < 0:
        razonamiento = 0

    evento_de_respuesta["tokens_entrada"] = respuesta.usage.prompt_tokens
    evento_de_respuesta["tokens_salida"] = respuesta.usage.completion_tokens
    evento_de_respuesta["tokens_razonamiento"] = razonamiento
    evento_de_respuesta["costo_usd"] = calcular_costo(
        cliente["modelo"],
        respuesta.usage.prompt_tokens,
        respuesta.usage.completion_tokens,
        razonamiento,
    )
    evento_de_respuesta["motivo_del_final"] = respuesta.choices[0].finish_reason
    evento_de_respuesta["respuesta"] = acortar(tapar_datos_sensibles(texto))
    guardar_evento(evento_de_respuesta)

    return texto


def mostrar_resumen():
    """
    Lee el archivo de log y saca cuentas.

    Esto es exactamente lo que hace un panel de metricas: leer los eventos
    guardados y agruparlos. Como estan en JSON, se hace con unas pocas lineas.
    """
    if not os.path.exists(ARCHIVO_DE_LOG):
        return

    archivo = open(ARCHIVO_DE_LOG, "r", encoding="utf-8")
    lineas = archivo.readlines()
    archivo.close()

    respuestas = []
    errores = []

    for linea in lineas:
        try:
            evento = json.loads(linea)
        except json.JSONDecodeError:
            continue   # si una linea esta rota, la salteamos

        if evento.get("evento") == "respuesta":
            respuestas.append(evento)
        elif evento.get("evento") == "error":
            errores.append(evento)

    if len(respuestas) == 0:
        return

    # Juntamos los tiempos y los ordenamos de menor a mayor.
    tiempos = []
    tokens_totales = 0
    costo_total = 0

    for evento in respuestas:
        tiempos.append(evento["milisegundos"])
        tokens_totales = (tokens_totales + evento["tokens_entrada"] +
                          evento["tokens_salida"] + evento.get("tokens_razonamiento", 0))

        if evento["costo_usd"] is not None:
            costo_total = costo_total + evento["costo_usd"]

    tiempos.sort()

    # La mediana es el valor del medio. Es mejor que el promedio porque un
    # solo caso muy lento no la distorsiona.
    posicion_del_medio = len(tiempos) // 2

    subtitulo("Metricas sacadas del archivo de log")
    print("  Llamadas exitosas:  " + str(len(respuestas)))
    print("  Errores:            " + str(len(errores)))
    print("  Tiempo mediano:     " + str(tiempos[posicion_del_medio]) + " ms")
    print("  Tiempo del peor:    " + str(tiempos[-1]) + " ms")
    print("  Tokens totales:     " + str(tokens_totales))
    print("  Costo acumulado:    " + str(round(costo_total, 6)) + " dolares")

    # Ahora agrupamos el costo por funcionalidad.
    costo_por_funcionalidad = {}

    for evento in respuestas:
        nombre = evento.get("funcionalidad", "sin_nombre")
        costo = evento["costo_usd"]

        if costo is None:
            costo = 0

        if nombre in costo_por_funcionalidad:
            costo_por_funcionalidad[nombre] = costo_por_funcionalidad[nombre] + costo
        else:
            costo_por_funcionalidad[nombre] = costo

    print()
    print("  Costo por funcionalidad:")
    for nombre in costo_por_funcionalidad:
        print("    " + nombre.ljust(26) + str(round(costo_por_funcionalidad[nombre], 6)) + " dolares")


def main():
    parser = crear_parser("Guardar registro de las llamadas al modelo")
    args = parser.parse_args()

    try:
        cliente = crear_cliente_desde_argumentos(args)
    except ValueError as error:
        print(error)
        return

    mostrar_configuracion(cliente)

    titulo("Haciendo llamadas y registrando todo")

    # Generamos un codigo unico que va a unir todas estas llamadas, como si
    # fueran parte de una misma accion del usuario.
    id_de_operacion = str(uuid.uuid4())[:8]

    # Cada elemento es: usuario, funcionalidad, prompt.
    trabajos = [
        ["usuario_042", "resumen_de_ticket",
         "Resumi en una linea: 'el pedido llego incompleto, falta el cargador'."],

        ["usuario_042", "sugerencia_de_respuesta",
         "Redacta una disculpa breve por un envio incompleto."],

        # Este trae datos personales a proposito, para ver como se tapan.
        ["usuario_099", "resumen_de_ticket",
         "Resumi: 'Soy Ana, mi mail es ana@ejemplo.com y mi tarjeta "
         "4111 1111 1111 1111 fue rechazada'."],
    ]

    for trabajo in trabajos:
        usuario = trabajo[0]
        funcionalidad = trabajo[1]
        prompt = trabajo[2]

        subtitulo(funcionalidad + " / " + usuario)

        try:
            respuesta = llamar_y_registrar(cliente, prompt, usuario, funcionalidad, id_de_operacion)
            print(respuesta)
        except Exception as error:
            print("  La llamada fallo, pero quedo registrada: " + type(error).__name__)

    titulo("COMO QUEDO GUARDADO EN EL ARCHIVO")

    archivo = open(ARCHIVO_DE_LOG, "r", encoding="utf-8")
    lineas = archivo.readlines()
    archivo.close()

    # Mostramos las ultimas 2 lineas, formateadas para que se lean.
    for linea in lineas[-2:]:
        evento = json.loads(linea)
        print()
        print(json.dumps(evento, ensure_ascii=False, indent=2))

    print()
    print("Fijate que en el ultimo registro el mail y la tarjeta aparecen tapados.")

    mostrar_resumen()

    titulo("LISTA DE CONTROL")
    print("""
  Archivo generado: """ + ARCHIVO_DE_LOG + """

  [ ] Un JSON por linea (formato .jsonl)
  [ ] Fecha y hora en formato universal
  [ ] Un identificador para unir las llamadas de una misma operacion
  [ ] El usuario, para poder investigar una queja concreta
  [ ] El proveedor y el modelo: sin esto no podes comparar nada
  [ ] Los tokens de entrada, de salida Y de razonamiento
  [ ] El costo calculado sumando el razonamiento (si no, te miente)
  [ ] El tiempo que tardo, en milisegundos
  [ ] Los datos personales tapados ANTES de escribir
  [ ] Los textos largos recortados
  [ ] La carpeta logs/ dentro del archivo .gitignore
""")


if __name__ == "__main__":
    main()
