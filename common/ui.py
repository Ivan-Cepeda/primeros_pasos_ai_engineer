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

    Los tokens son la unidad con la que se cobra. Se dividen en dos:
      prompt_tokens     -> lo que le mandaste (la entrada)
      completion_tokens -> lo que el modelo escribio (la salida)
    """
    uso = respuesta.usage

    print("[tokens] entrada: " + str(uso.prompt_tokens) +
          " | salida: " + str(uso.completion_tokens) +
          " | total: " + str(uso.total_tokens))


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
