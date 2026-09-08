"""
L2 - Ejercicio 02: los parametros que cambian como responde el modelo.

QUE VAMOS A VER
  - temperature: cuanta variedad tiene la respuesta.
  - max_tokens: cuanto puede escribir como maximo (y cuanto cuesta).

CASO DE USO
  Somos el equipo de una app de finanzas y necesitamos dos cosas distintas:
    a) nombres creativos para una campana -> queremos variedad
    b) clasificar reclamos de clientes    -> queremos SIEMPRE lo mismo

COMO CORRERLO
    python 02_parametros_de_generacion.py --provider gemini
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import crear_parser
from common.llm import crear_cliente_desde_argumentos, conversar, obtener_texto, preguntar
from common.ui import mostrar_configuracion, mostrar_uso, subtitulo, titulo


# Guardamos los textos largos en variables, arriba de todo, para que el codigo
# de abajo se lea mas facil.
PEDIDO_CREATIVO = "Inventa un nombre para una app de ahorro automatico. Responde solo el nombre."

PEDIDO_CLASIFICACION = (
    "Clasifica este reclamo en una sola categoria: FACTURACION, TECNICO o CUENTA.\n"
    "Responde unicamente con la categoria.\n\n"
    "Reclamo: 'Me cobraron dos veces la suscripcion y ademas no puedo entrar a la app.'"
)


def main():
    parser = crear_parser("Como afectan los parametros a la respuesta")
    args = parser.parse_args()

    try:
        cliente = crear_cliente_desde_argumentos(args)
    except ValueError as error:
        print(error)
        return

    mostrar_configuracion(cliente)

    # -----------------------------------------------------------------------
    titulo("TEMPERATURE: cuanto se arriesga el modelo al elegir cada palabra")
    # -----------------------------------------------------------------------
    # Va de 0 a 2 aproximadamente.
    #   Cerca de 0  -> elige siempre la palabra mas probable. Muy repetitivo.
    #   Cerca de 1  -> mezcla mas opciones. Mas variado.
    #   Arriba de 1 -> se vuelve impredecible y puede decir cosas raras.

    lista_de_temperaturas = [0.0, 0.7, 1.3]

    for temperatura in lista_de_temperaturas:
        subtitulo("temperature = " + str(temperatura))

        # range(3) genera los numeros 0, 1, 2. O sea, repetimos 3 veces.
        for numero_de_intento in range(3):
            nombre = preguntar(cliente, PEDIDO_CREATIVO, temperatura=temperatura, max_tokens=1000)
            print("  intento " + str(numero_de_intento + 1) + ": " + nombre)

    print()
    print("Fijate: con 0.0 los tres intentos son casi iguales.")
    print("Con 1.3 son bien distintos entre si.")

    # -----------------------------------------------------------------------
    titulo("MAX_TOKENS: el limite de largo de la respuesta")
    # -----------------------------------------------------------------------
    # Es tambien el limite del costo: nunca vas a pagar mas salida que esta.

    for limite in [250, 900]:
        subtitulo("max_tokens = " + str(limite))

        respuesta = conversar(
            cliente,
            [{"role": "user", "content": "Explica que es el interes compuesto."}],
            temperatura=0.3,
            max_tokens=limite,
        )

        print(obtener_texto(respuesta))
        print()
        mostrar_uso(respuesta)
        print("[motivo del final] " + respuesta.choices[0].finish_reason)

    print()
    print("OJO: con el limite chico la respuesta se CORTA a la mitad de una frase.")
    print("No se resume: se trunca. Mira el [motivo del final]: dice 'length'.")
    print("Si queres respuestas cortas, hay que pedirlo en el texto del prompt.")
    print()
    print("Y si en la linea de tokens aparece 'razonamiento oculto', tu modelo")
    print("piensa antes de contestar: ese pensamiento tambien se come el limite.")

    # -----------------------------------------------------------------------
    titulo("UN CASO REAL: clasificar reclamos")
    # -----------------------------------------------------------------------
    # Cuando la tarea es clasificar, la creatividad es un problema: queremos
    # que el mismo reclamo de siempre la misma categoria.

    subtitulo("temperature = 0  (asi se hace)")
    for numero_de_intento in range(3):
        categoria = preguntar(cliente, PEDIDO_CLASIFICACION, temperatura=0, max_tokens=1000)
        print("  intento " + str(numero_de_intento + 1) + ": " + categoria)

    subtitulo("temperature = 1.5  (asi NO se hace)")
    for numero_de_intento in range(3):
        categoria = preguntar(cliente, PEDIDO_CLASIFICACION, temperatura=1.5, max_tokens=1000)
        print("  intento " + str(numero_de_intento + 1) + ": " + categoria)

    # -----------------------------------------------------------------------
    titulo("RESUMEN PARA GUARDARSE")
    # -----------------------------------------------------------------------
    print("""
  Que estas haciendo               temperature recomendada
  -------------------------------  -----------------------
  Clasificar o extraer datos       0.0 a 0.2
  Responder sobre documentacion    0.2 a 0.4
  Redactar textos                  0.5 a 0.8
  Buscar ideas o nombres           0.9 a 1.3
""")


if __name__ == "__main__":
    main()
