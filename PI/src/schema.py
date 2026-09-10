"""
El contrato de salida: que forma tiene el JSON y como se valida.

POR QUE ESTE ARCHIVO EXISTE
  La guia del proyecto insiste en trabajar "con la idea de contrato": definir
  como va a ser la salida ANTES de pedirsela al modelo, y mantenerla estable.

  Ese contrato vive aca, en un solo lugar, y no repartido por el codigo. Si
  manana hay que agregar un campo, se agrega aca y todo lo demas se entera.

POR QUE VALIDAMOS EN PYTHON Y NO CONFIAMOS EN EL MODELO
  Que el modelo devuelva un JSON con la forma correcta no significa que el
  contenido tenga sentido. Un "confidence" de 3.7 es JSON perfectamente valido
  y a la vez imposible. La forma la garantiza el modelo; la coherencia la
  garantiza este archivo.
"""

import json


# Valores permitidos para los campos cerrados.
# Usar listas cerradas convierte texto libre en algo que el codigo puede
# comparar con "==", que es la diferencia entre un dato y una frase.
CATEGORIAS = ["facturacion", "tecnico", "cuenta", "producto", "otro"]

ACCIONES = [
    "responder_directo",
    "escalar_a_humano",
    "pedir_mas_informacion",
    "derivar_a_facturacion",
    "abrir_ticket_tecnico",
]

# Debajo de esta confianza, la respuesta no se le muestra sola al agente:
# se marca para que la revise una persona. Es una decision de producto, no
# de programacion, y por eso esta arriba y con nombre, no perdida en un if.
UMBRAL_DE_CONFIANZA = 0.60


# Descripcion del contrato en palabras. Se inserta en el prompt para que el
# modelo sepa exactamente que tiene que devolver.
DESCRIPCION_DEL_CONTRATO = """{
  "answer": "string - la respuesta para el agente de soporte, maximo 3 oraciones",
  "confidence": "number - entre 0.0 y 1.0, que tan seguro estas de la respuesta",
  "actions": ["string - una o mas de: responder_directo, escalar_a_humano, pedir_mas_informacion, derivar_a_facturacion, abrir_ticket_tecnico"],
  "category": "string - una de: facturacion, tecnico, cuenta, producto, otro",
  "requires_human": "boolean - true si un humano tiene que revisar antes de responder"
}"""


def parsear(texto):
    """
    Convierte el texto que devolvio el modelo en un diccionario de Python.

    Aunque le pidamos JSON limpio, a veces viene envuelto en ```json ... ```.
    Lo limpiamos antes de parsear en vez de fallar por un detalle de formato.

    Lanza ValueError si el texto no es JSON de ninguna manera.
    """
    texto = texto.strip()

    if texto.startswith("```"):
        partes = texto.split("```")

        if len(partes) > 1:
            texto = partes[1]

            if texto.startswith("json"):
                texto = texto[4:]

            texto = texto.strip()

    try:
        return json.loads(texto)
    except json.JSONDecodeError as error:
        raise ValueError("El modelo no devolvio JSON valido: " + str(error))


def validar(datos):
    """
    Revisa que el diccionario cumpla el contrato.

    Devuelve una lista de problemas. Lista vacia significa "esta todo bien".

    Devolvemos la lista completa en vez de cortar en el primer error, porque
    para depurar sirve mucho mas ver todos los problemas juntos.
    """
    problemas = []

    # --- answer ---
    if "answer" not in datos:
        problemas.append("falta el campo 'answer'")
    elif not isinstance(datos["answer"], str):
        problemas.append("'answer' tiene que ser texto")
    elif len(datos["answer"].strip()) == 0:
        problemas.append("'answer' esta vacio")

    # --- confidence ---
    if "confidence" not in datos:
        problemas.append("falta el campo 'confidence'")
    elif not isinstance(datos["confidence"], (int, float)):
        problemas.append("'confidence' tiene que ser un numero")
    elif datos["confidence"] < 0 or datos["confidence"] > 1:
        problemas.append("'confidence' tiene que estar entre 0.0 y 1.0")

    # --- actions ---
    if "actions" not in datos:
        problemas.append("falta el campo 'actions'")
    elif not isinstance(datos["actions"], list):
        problemas.append("'actions' tiene que ser una lista")
    elif len(datos["actions"]) == 0:
        problemas.append("'actions' no puede estar vacia")
    else:
        for accion in datos["actions"]:
            if accion not in ACCIONES:
                problemas.append("accion desconocida: '" + str(accion) + "'")

    # --- category ---
    if "category" not in datos:
        problemas.append("falta el campo 'category'")
    elif datos["category"] not in CATEGORIAS:
        problemas.append("categoria desconocida: '" + str(datos["category"]) + "'")

    # --- requires_human ---
    if "requires_human" not in datos:
        problemas.append("falta el campo 'requires_human'")
    elif not isinstance(datos["requires_human"], bool):
        problemas.append("'requires_human' tiene que ser true o false")

    return problemas


def aplicar_reglas_de_negocio(datos):
    """
    Ajusta la respuesta segun reglas nuestras, no del modelo.

    Estas reglas son deterministas: dado el mismo JSON, siempre hacen lo mismo.
    Eso es exactamente lo que queremos para las decisiones que importan.

    Devuelve el diccionario ajustado y la lista de reglas que se aplicaron.
    """
    reglas_aplicadas = []

    # Regla 1: poca confianza obliga a revision humana, diga lo que diga el
    # modelo. Un modelo puede estar seguro de algo incorrecto; el umbral es
    # nuestra red de contencion.
    if datos["confidence"] < UMBRAL_DE_CONFIANZA and not datos["requires_human"]:
        datos["requires_human"] = True
        reglas_aplicadas.append(
            "confianza " + str(datos["confidence"]) + " por debajo del umbral " +
            str(UMBRAL_DE_CONFIANZA) + ": se marca para revision humana"
        )

    # Regla 2: si requiere humano, la accion tiene que incluir escalarlo.
    # Sin esto podriamos marcar "requires_human" y aun asi decirle al sistema
    # downstream "responder_directo", que es contradictorio.
    if datos["requires_human"] and "escalar_a_humano" not in datos["actions"]:
        datos["actions"].append("escalar_a_humano")
        reglas_aplicadas.append("requiere humano: se agrega la accion escalar_a_humano")

    return datos, reglas_aplicadas


def respuesta_de_emergencia(motivo):
    """
    JSON valido para devolver cuando algo falla.

    La aplicacion NUNCA debe romper el contrato, ni siquiera cuando falla. Si
    el sistema que nos consume espera estos cinco campos, se los damos siempre;
    lo que cambia es el contenido, no la forma.
    """
    return {
        "answer": "No pude generar una respuesta confiable para esta consulta.",
        "confidence": 0.0,
        "actions": ["escalar_a_humano"],
        "category": "otro",
        "requires_human": True,
        "error": motivo,
    }
