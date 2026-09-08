"""
Funciones para que la salida en la terminal se lea ordenada.

No tienen nada que ver con la inteligencia artificial: son solo ayudas para
imprimir titulos y separadores sin repetir el mismo codigo en cada ejercicio.
"""


def titulo(texto):
    """Imprime un titulo grande, con lineas de = arriba y abajo."""
    print()
    print("=" * 78)   # el * repite un texto: "=" * 5 da "====="
    print(texto)
    print("=" * 78)


def subtitulo(texto):
    """Imprime un titulo mas chico, con lineas de guiones."""
    print()
    print("-" * 78)
    print(texto)
    print("-" * 78)


def mostrar_uso(respuesta):
    """
    Muestra cuantos tokens consumio una respuesta.

    Los tokens son la unidad con la que se cobra. Se dividen en tres:
      prompt_tokens     -> lo que le mandaste (la entrada)
      completion_tokens -> lo que el modelo escribio y vos leiste (la salida)
      razonamiento      -> lo que el modelo penso por dentro y NO te mostro

    Los de razonamiento no vienen en un campo propio: se deducen restando.
    Si esta linea muestra un numero grande ahi, estas usando un modelo de
    razonamiento y tenes que darle mas espacio en max_tokens.
    """
    uso = respuesta.usage

    ocultos = uso.total_tokens - uso.prompt_tokens - uso.completion_tokens

    if ocultos < 0:
        ocultos = 0

    linea = ("[tokens] entrada: " + str(uso.prompt_tokens) +
             " | salida visible: " + str(uso.completion_tokens))

    if ocultos > 0:
        linea = linea + " | razonamiento oculto: " + str(ocultos)

    linea = linea + " | total: " + str(uso.total_tokens)

    print(linea)


def mostrar_configuracion(cliente):
    """
    Avisa con que proveedor y modelo se esta corriendo el ejercicio.

    De la clave mostramos solo los ultimos 4 caracteres: alcanza para saber cual
    estas usando y no queda la clave completa escrita en la pantalla.
    """
    ultimos_4 = cliente["clave"][-4:]

    print("[config] proveedor: " + cliente["proveedor"] +
          " | modelo: " + cliente["modelo"] +
          " | clave: ..." + ultimos_4)
