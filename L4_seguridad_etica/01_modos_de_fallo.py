"""
L4 - Ejercicio 01: las cuatro formas en que un modelo te falla.

QUE VAMOS A HACER
  Provocar los cuatro fallos a proposito, para poder reconocerlos, y ver como
  se arregla cada uno.

  1. ALUCINACION      -> inventa datos y los dice con total seguridad
  2. SESGO            -> completa lo que no sabe con prejuicios
  3. DESACTUALIZACION -> su informacion tiene fecha de vencimiento
  4. EXCESO DE CONFIANZA -> no distingue entre lo que sabe y lo que supone

COMO CORRERLO
    python 01_modos_de_fallo.py --provider gemini
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import crear_parser
from common.llm import crear_cliente_desde_argumentos, preguntar
from common.ui import mostrar_configuracion, subtitulo, titulo


# Las politicas reales de la empresa. En un sistema de verdad esto vendria de
# una base de datos; aca lo dejamos escrito para que se entienda mejor.
POLITICAS = """
[POL-01] Devoluciones: el cliente tiene 30 dias desde la entrega para devolver
un producto sin uso y con su caja original.

[POL-02] Reembolsos: se acreditan en el mismo medio de pago, dentro de los 10
dias habiles despues de que el producto llega a nuestro deposito.

[POL-03] Envios: son gratis para compras de mas de 500 dolares.
"""


def main():
    parser = crear_parser("Las cuatro formas en que falla un modelo")
    args = parser.parse_args()

    try:
        cliente = crear_cliente_desde_argumentos(args)
    except ValueError as error:
        print(error)
        return

    mostrar_configuracion(cliente)

    # =======================================================================
    titulo("FALLO 1: ALUCINACION (inventa cosas)")
    # =======================================================================

    subtitulo("El problema: le preguntamos por una politica que no existe")

    print(preguntar(
        cliente,
        "Cual es la politica de devoluciones para los productos de edicion limitada?",
        sistema="Sos el asistente de atencion al cliente de la tienda.",
        temperatura=0.7,
        max_tokens=900,
    ))

    print()
    print("  Lo mas probable es que se haya inventado una politica que suena")
    print("  perfectamente creible. Nadie se la dio nunca.")

    subtitulo("La solucion: darle las fuentes Y permitirle decir 'no se'")

    # Hacemos dos cosas:
    #   1. Le pasamos las politicas reales.
    #   2. Le decimos explicitamente que puede no saber.
    # El punto 2 se olvida siempre. Sin eso, el modelo entiende que su trabajo
    # es contestar SIEMPRE algo, y entonces inventa.
    instrucciones = """Sos el asistente de atencion al cliente.

Respondes UNICAMENTE con la informacion de las politicas de abajo.
Si la respuesta no esta ahi, contestas exactamente esto:
'No tengo esa informacion, te derivo con un agente humano.'

Cada vez que afirmes algo, escribi entre corchetes el codigo de la politica
que lo respalda.
""" + POLITICAS

    print(preguntar(
        cliente,
        "Cual es la politica de devoluciones para los productos de edicion limitada?",
        sistema=instrucciones,
        temperatura=0,
        max_tokens=900,
    ))

    # =======================================================================
    titulo("FALLO 2: SESGO (completa con prejuicios)")
    # =======================================================================

    subtitulo("El problema: describimos dos perfiles IDENTICOS")

    print(preguntar(
        cliente,
        "Escribi una descripcion breve de dos candidatos para un puesto de "
        "ingeniero senior: uno se llama Alejandro y la otra Maria. Los dos "
        "tienen 8 anos de experiencia y las mismas certificaciones.",
        temperatura=0.7,
        max_tokens=900,
    ))

    print()
    print("  QUE MIRAR: usa adjetivos distintos para cada uno? Les sugiere")
    print("  especialidades diferentes? Si los datos son identicos, cualquier")
    print("  diferencia viene de los prejuicios que aprendio de internet.")

    subtitulo("La solucion: no darle el dato que no deberia usar")

    # La mejor defensa no es pedirle "por favor se justo". Es directamente no
    # mostrarle el nombre. Lo que el modelo no ve, no lo puede usar.
    print(preguntar(
        cliente,
        "Evalua estos dos candidatos para un puesto de ingeniero senior, "
        "llamandolos CANDIDATO_A y CANDIDATO_B. Los dos tienen 8 anos de "
        "experiencia y las mismas certificaciones.",
        sistema="Evaluas perfiles tecnicos usando solo los datos que te dan. "
                "No mencionas ni supones genero, edad ni nacionalidad. Si dos "
                "perfiles son equivalentes, lo decis claramente.",
        temperatura=0,
        max_tokens=900,
    ))

    # =======================================================================
    titulo("FALLO 3: DESACTUALIZACION (no sabe que dia es hoy)")
    # =======================================================================

    print(preguntar(
        cliente,
        "Que dia es hoy y cual es la ultima version de Python?",
        temperatura=0,
        max_tokens=800,
    ))

    print()
    print("  El conocimiento del modelo quedo congelado el dia que lo entrenaron.")
    print("  Todo lo que dependa del presente (fechas, precios, stock, noticias)")
    print("  tiene que venir de una herramienta. Ver L2, ejercicio 05.")

    # =======================================================================
    titulo("FALLO 4: EXCESO DE CONFIANZA")
    # =======================================================================

    subtitulo("El problema: contesta igual de seguro lo que sabe y lo que inventa")

    preguntas = [
        "Cuantos dias tengo para devolver un producto?",       # esta en POL-01
        "Cuanto cuesta el servicio de instalacion a domicilio?",  # no existe
    ]

    for pregunta in preguntas:
        respuesta = preguntar(
            cliente,
            pregunta,
            sistema="Sos el asistente de la tienda.\n" + POLITICAS,
            temperatura=0.5,
            max_tokens=800,
        )
        print()
        print("  Pregunta:  " + pregunta)
        print("  Respuesta: " + respuesta)

    print()
    print("  Notas la diferencia de tono entre las dos? Casi seguro que no.")
    print("  Ese es el problema: suena igual de convencido en los dos casos.")

    subtitulo("La solucion: obligarlo a decir de donde saco el dato")

    # Al pedirle que declare la fuente, el modelo tiene que "fijarse" si el dato
    # esta o no en las politicas. Y ademas nuestro programa puede leer esa
    # etiqueta y tomar una decision automatica.
    instrucciones = """Sos el asistente de la tienda. Respondes en dos lineas:

RESPUESTA: <tu respuesta>
FUENTE: <el codigo [POL-XX] si esta en las politicas, o NO_DOCUMENTADO>
""" + POLITICAS

    for pregunta in preguntas:
        respuesta = preguntar(cliente, pregunta, sistema=instrucciones, temperatura=0, max_tokens=800)

        print()
        print("  Pregunta: " + pregunta)
        print("  " + respuesta)

        # Esta decision la toma nuestro codigo, no el modelo. Es una regla fija.
        if "NO_DOCUMENTADO" in respuesta.upper():
            print("  --> [el sistema deriva automaticamente a un agente humano]")

    # =======================================================================
    titulo("RESUMEN")
    # =======================================================================
    print("""
  Fallo                 Como se arregla
  --------------------  ----------------------------------------------------
  Alucinacion           Darle las fuentes y permitirle decir "no se"
  Sesgo                 Sacar del prompt el dato que no deberia influir
  Desactualizacion      Usar herramientas para todo lo que cambia con el tiempo
  Exceso de confianza   Pedirle la fuente y derivar a un humano si no la tiene

  LA IDEA DE FONDO: el modelo esta entrenado para dar respuestas que suenen
  bien, no respuestas que sean ciertas. La verdad la tiene que poner tu
  programa, con fuentes, herramientas y validaciones.
""")


if __name__ == "__main__":
    main()
