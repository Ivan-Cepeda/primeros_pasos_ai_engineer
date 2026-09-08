"""
Funciones para hablar con el modelo, sirvan para OpenAI o para Gemini.

POR QUE EL MISMO CODIGO FUNCIONA CON LOS DOS
--------------------------------------------
La libreria que instalamos se llama "openai", pero en realidad no esta atada a
la empresa OpenAI: es un programa que sabe hablar un idioma tecnico concreto.
Google hizo que Gemini entienda ese mismo idioma en una direccion de internet
especial. Entonces alcanza con cambiar dos cosas:

    - la direccion (base_url)
    - la clave (api_key)

...y todo lo demas (mensajes, streaming, herramientas) se escribe igual.

Lo unico que cambia de verdad entre proveedores esta anotado donde aparece:
  * Solo OpenAI tiene el servicio de moderacion (lo vemos en L4).
  * La libreria tiktoken para contar tokens solo sirve con modelos de OpenAI.
"""

import json

from openai import OpenAI

from common.config import cargar_configuracion


def crear_cliente(proveedor=None, modelo=None):
    """
    Prepara la conexion con el proveedor y devuelve un diccionario con todo lo
    que hace falta para trabajar.

    Devolvemos un diccionario (y no un objeto complicado) para que se vea claro
    que adentro hay solo tres cosas:
        cliente["api"]       -> la conexion con el servidor
        cliente["modelo"]    -> el nombre del modelo que vamos a usar
        cliente["proveedor"] -> "openai" o "gemini"
    """
    config = cargar_configuracion(proveedor, modelo)

    # Aca esta toda la magia de la compatibilidad: le pasamos la clave y la
    # direccion. Si base_url es None, la libreria usa la de OpenAI.
    conexion = OpenAI(api_key=config["clave"], base_url=config["base_url"])

    return {
        "api": conexion,
        "modelo": config["modelo"],
        "proveedor": config["proveedor"],
        "clave": config["clave"],
    }


def crear_cliente_desde_argumentos(args):
    """Version que toma los datos de lo que se escribio en la terminal."""
    return crear_cliente(args.provider, args.model)


def conversar(cliente, mensajes, temperatura=None, max_tokens=None, **extras):
    """
    Manda una lista de mensajes al modelo y devuelve la respuesta COMPLETA.

    "Respuesta completa" quiere decir el objeto que manda el servidor, que
    ademas del texto trae cuantos tokens se usaron y por que se detuvo.

    Los **extras permiten pasar cualquier otra opcion (por ejemplo tools= o
    stream=) sin tener que modificar esta funcion cada vez.
    """
    # Armamos un diccionario con las opciones del pedido.
    opciones = {
        "model": cliente["modelo"],
        "messages": mensajes,
    }

    # Solo agregamos temperatura y max_tokens si nos los pidieron.
    # (Mandar un valor vacio puede hacer que el servidor rechace el pedido.)
    if temperatura is not None:
        opciones["temperature"] = temperatura
    if max_tokens is not None:
        opciones["max_tokens"] = max_tokens

    # update() agrega al diccionario todo lo que vino en **extras.
    opciones.update(extras)

    # Los ** delante de opciones significan "pasa cada clave del diccionario
    # como si fuera un parametro con ese nombre".
    return cliente["api"].chat.completions.create(**opciones)


def preguntar(cliente, pregunta, sistema=None, temperatura=None, max_tokens=None, **extras):
    """
    Atajo para el caso mas comun: una pregunta, un texto de respuesta.

    Si le pasas "sistema", ese texto son las instrucciones permanentes que
    definen como se tiene que comportar el modelo.
    """
    mensajes = []

    if sistema is not None:
        mensajes.append({"role": "system", "content": sistema})

    mensajes.append({"role": "user", "content": pregunta})

    respuesta = conversar(cliente, mensajes, temperatura, max_tokens, **extras)

    return obtener_texto(respuesta)


def obtener_texto(respuesta):
    """
    Saca el texto de una respuesta.

    El servidor puede devolver varias alternativas, guardadas en una lista
    llamada "choices". Nosotros siempre pedimos una sola, asi que agarramos la
    primera, que en Python es la posicion 0.
    """
    texto = respuesta.choices[0].message.content

    # A veces el modelo no devuelve texto (por ejemplo cuando pide usar una
    # herramienta). En ese caso content vale None y lo convertimos a "".
    if texto is None:
        texto = ""

    # AVISO IMPORTANTE para los modelos de razonamiento (ver mas abajo).
    # Si la respuesta vino vacia PORQUE se acabo el limite de tokens, avisamos.
    # Sin este aviso, el ejercicio imprime una linea en blanco y parece que el
    # modelo "no contesto nada", cuando en realidad si trabajo: gasto todo el
    # presupuesto de tokens razonando por dentro y no le quedo lugar para
    # escribir la respuesta.
    if texto == "" and respuesta.choices[0].finish_reason == "length":
        print("  [AVISO] respuesta vacia: se acabo el max_tokens.")
        print("          Si usas un modelo de razonamiento, subi max_tokens.")

    return texto.strip()


def tokens_de_razonamiento(respuesta):
    """
    Calcula los tokens que el modelo gasto PENSANDO, sin mostrartelos.

    LOS MODELOS DE RAZONAMIENTO (lo nuevo de 2026)
    ----------------------------------------------
    Los modelos modernos (Gemini 3.x, GPT-6, Claude Opus 5) no contestan de
    inmediato: primero "piensan" por dentro, escribiendo un borrador que vos
    nunca ves. Ese borrador consume tokens y se paga.

    Por eso las cuentas del campo `usage` no cierran:

        tokens de entrada  +  tokens visibles  <  total

    La diferencia son los tokens de razonamiento. Y lo mas importante para
    programar: max_tokens limita TODO junto, pensamiento incluido. Si le pones
    un limite chico, el modelo lo gasta pensando y te devuelve texto vacio.
    """
    uso = respuesta.usage

    ocultos = uso.total_tokens - uso.prompt_tokens - uso.completion_tokens

    # Con un modelo que no razona, esta cuenta da 0 (o algo muy chico).
    if ocultos < 0:
        return 0

    return ocultos


def conversar_en_streaming(cliente, mensajes, temperatura=None, max_tokens=None):
    """
    Version que va entregando el texto de a pedacitos, a medida que se genera.

    Es lo que hace que en un chat las palabras vayan apareciendo de a poco en
    vez de esperar en blanco a que termine todo.

    Esta funcion usa "yield" en lugar de "return": eso la convierte en un
    generador, algo que se puede recorrer con un for y que va entregando
    valores de a uno.
    """
    respuesta = conversar(cliente, mensajes, temperatura, max_tokens, stream=True)

    for pedacito in respuesta:
        # Algunos pedacitos vienen vacios (traen datos de control, no texto).
        if len(pedacito.choices) == 0:
            continue

        contenido = pedacito.choices[0].delta.content

        if contenido is not None:
            yield contenido


def usar_herramientas(cliente, mensajes, herramientas, funciones, max_vueltas=5, mostrar=True):
    """
    Hace funcionar el "tool calling": el modelo pide ejecutar funciones nuestras.

    COMO FUNCIONA, PASO A PASO:
      1. Le mandamos los mensajes y la lista de herramientas disponibles.
      2. El modelo puede contestar dos cosas distintas:
            a) un texto normal  -> terminamos
            b) "quiero que ejecutes la funcion X con estos datos"
      3. Si pide (b), nosotros ejecutamos esa funcion en Python y le mandamos
         el resultado de vuelta.
      4. Volvemos al paso 1 hasta que conteste con texto.

    IMPORTANTE: el modelo NUNCA ejecuta nada. Solo pide. Quien ejecuta sos vos.

    Parametros:
      herramientas -> la lista de descripciones que ve el modelo
      funciones    -> un diccionario que dice: nombre -> funcion de Python real
    """
    # Hacemos una copia de la lista para no modificar la original.
    historial = list(mensajes)

    for numero_de_vuelta in range(max_vueltas):

        respuesta = conversar(cliente, historial, temperatura=0, tools=herramientas)
        mensaje = respuesta.choices[0].message

        # Guardamos lo que dijo el modelo en el historial.
        historial.append(mensaje.model_dump(exclude_none=True))

        # Si no pidio ninguna herramienta, ya tenemos la respuesta final.
        if not mensaje.tool_calls:
            return obtener_texto(respuesta), historial

        # Si llegamos aca, el modelo pidio una o mas herramientas.
        for pedido in mensaje.tool_calls:

            nombre = pedido.function.name

            # Los datos llegan como texto en formato JSON, hay que convertirlos
            # a un diccionario de Python con json.loads.
            datos = json.loads(pedido.function.arguments)

            if mostrar:
                print("  [herramienta] vuelta " + str(numero_de_vuelta + 1) + ": " + nombre + "(" + str(datos) + ")")

            if nombre in funciones:
                # Los ** convierten el diccionario en parametros con nombre.
                # Si datos es {"ciudad": "Rosario"}, esto llama a la funcion
                # como funcion(ciudad="Rosario").
                resultado = funciones[nombre](**datos)
            else:
                resultado = {"error": "no existe una herramienta llamada " + nombre}

            # Le devolvemos el resultado al modelo. El "tool_call_id" es lo que
            # le permite saber a cual de sus pedidos corresponde esta respuesta.
            historial.append({
                "role": "tool",
                "tool_call_id": pedido.id,
                "name": nombre,
                "content": json.dumps(resultado, ensure_ascii=False),
            })

    return "[Se llego al limite de vueltas sin una respuesta final]", historial
