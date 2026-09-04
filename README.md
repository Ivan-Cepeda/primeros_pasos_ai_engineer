# M1 — Ejercicios prácticos: integración de LLMs

Ejercicios acompañantes de la lección **L2 — Bases técnicas para la
integración de un LLM**.
Todo el código corre indistintamente con **OpenAI** o con **Google Gemini**,
sin cambiar una sola línea: sólo se cambia una variable de entorno.

---

## Por qué dos proveedores

Las lecciones usan la API de OpenAI. Este repositorio agrega Gemini como
alternativa por dos razones prácticas:

1. **Acceso.** Gemini tiene una capa gratuita generosa; no todos pueden (o
   quieren) cargar una tarjeta para hacer los ejercicios.
2. **Es la lección más importante.** Si tu código está atado a un proveedor,
   cambiar de modelo es un refactor. Si está desacoplado, es una variable de
   entorno. Todo el módulo está construido alrededor de esa idea.

### Cómo funciona técnicamente

El SDK oficial `openai` no es "el SDK de OpenAI la empresa": es un cliente HTTP
que habla el protocolo `/chat/completions`. Google publica un endpoint
compatible con ese mismo protocolo para Gemini. Entonces alcanza con cambiar la
URL base y la API key:

| Proveedor | `base_url`                                            | Variable de entorno |
|-----------|-------------------------------------------------------|---------------------|
| OpenAI    | *(por defecto del SDK)*                               | `OPENAI_API_KEY`    |
| Gemini    | `https://generativelanguage.googleapis.com/v1beta/openai/` | `GEMINI_API_KEY` |

Toda esa lógica vive en un solo archivo: [`common/llm.py`](common/llm.py).
Los ejercicios no saben con qué proveedor están hablando.

---

## Sobre el nivel de Python

El código está escrito para alguien que recién empieza. Usa a propósito sólo
funciones, listas, diccionarios y bucles `for`: nada de clases, decoradores ni
sintaxis avanzada. Es más largo de lo que podría ser, y esa es la intención —
cada paso está a la vista en vez de escondido detrás de una abstracción.

Los comentarios están dirigidos a quien lee el código por primera vez y
explican tanto el concepto de IA como el Python que se está usando.

---

## Puesta en marcha

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

> En Linux o macOS: `source .venv/bin/activate`

```bash
pip install -r requirements.txt
```

Copiá el archivo de ejemplo y completá **al menos una** de las dos claves:

```bash
copy .env.example .env
```

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=tu-clave-aca
```

- Clave de Gemini (con capa gratuita): https://aistudio.google.com/apikey
- Clave de OpenAI: https://platform.openai.com/api-keys

Verificá que todo esté bien:

```bash
python L2_integracion_llm/01_primer_llamado.py
```

---

## Cómo elegir el proveedor

Cada script acepta los mismos dos flags, que sobrescriben lo que diga el `.env`:

```bash
python L2_integracion_llm/02_parametros_de_generacion.py --provider gemini
```

```bash
python L2_integracion_llm/02_parametros_de_generacion.py --provider openai --model gpt-4o
```

Sin flags, se usa lo configurado en `LLM_PROVIDER`.

---

## Estructura del repositorio

```
M1/
├── common/                     Capa compartida (lo único que conoce a los proveedores)
│   ├── config.py               Credenciales, .env, argumentos de la terminal
│   ├── llm.py                  Funciones para hablar con el modelo: chat, streaming, herramientas
│   └── ui.py                   Utilidades de impresión en consola
│
├── L2_integracion_llm/         Bases técnicas de la integración
│   ├── 01_primer_llamado.py
│   ├── 02_parametros_de_generacion.py
│   ├── 03_streaming_y_errores.py
│   ├── 04_salida_estructurada.py
│   ├── 05_tool_calling.py
│   ├── 06_comparar_proveedores.py
│   └── DESAFIOS.md
│
├── .env.example
├── .gitignore
└── requirements.txt
```

La carpeta de la lección tiene su propio `README.md` con el detalle de cada
ejercicio, y un `DESAFIOS.md` con cinco consignas para resolver.

---

## Gestión de credenciales

**Regla que no se negocia: ninguna API key se escribe nunca en el código.**

- Las claves viven en `.env`, que está en `.gitignore` y no se sube al repo.
- Lo que se versiona es `.env.example`, con los nombres de las variables pero
  sin valores.
- En producción las mismas variables las inyecta el servidor o el gestor de
  secretos; el código no cambia.
- Si una clave se filtra alguna vez (un commit, una captura, un log), se
  **revoca y se rota**. No alcanza con borrar el commit.

Toda la lógica está en [`common/config.py`](common/config.py), con este orden de
prioridad: *flag de línea de comandos* → *variable de entorno* → *valor por defecto*.

---

## Diferencias entre proveedores a tener presentes

| Funcionalidad                     | OpenAI | Gemini (endpoint compatible) |
|-----------------------------------|--------|------------------------------|
| Chat completions                  | ✅     | ✅                           |
| Streaming                         | ✅     | ✅                           |
| Tool / function calling           | ✅     | ✅                           |
| `response_format: json_object`    | ✅     | ✅                           |
| Endpoint `/moderations`           | ✅     | ❌ *(sólo OpenAI)*            |
| Conteo local con `tiktoken`       | ✅     | ❌ *(tokenizador propio)*     |

Donde hay una diferencia, el código la detecta y elige una alternativa; está
comentado en cada archivo.

---

## Orden sugerido

Empezá por [`L2_integracion_llm/README.md`](L2_integracion_llm/README.md) y hacé
los ejercicios en orden numérico: cada uno asume el anterior.

Las lecciones siguientes (L3 — ingeniería de prompts, y L4 — seguridad y ética)
se publican más adelante en este mismo repositorio.

---

## Costo

Todos los ejercicios usan modelos económicos (`gpt-4o-mini`, un modelo Flash de Gemini)
y `max_tokens` acotado. Correr el repositorio completo con OpenAI cuesta
centavos; con la capa gratuita de Gemini, cero.

Aun así: configurá un límite de gasto en el panel de tu proveedor antes de
empezar.
