# -*- coding: utf-8 -*-
"""Compara modelos de Ollama contra el conjunto dorado y genera un informe.

Corre cada caso de eval/golden-set-es.jsonl contra cada modelo indicado, con el
prompt de sistema socrático v1, temperatura fija y medición de velocidad.
El informe (eval/comparacion-AAAAMMDD.md) presenta las respuestas lado a lado con
la checklist de la rúbrica para calificación humana.

Uso:
    python scripts/comparar_modelos.py qwen3:8b llama3.1:8b gemma3:12b
    OLLAMA_HOST=http://IP_DEL_DROPLET:11434 python scripts/comparar_modelos.py ...

Requiere: Ollama corriendo y los modelos ya descargados (ollama pull <modelo>).
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
GOLDEN = RAIZ / "eval" / os.environ.get("GOLDEN_SET", "golden-set-es.jsonl")
# Versión del prompt seleccionable: TUTOR_PROMPT=system-socratico-es-v2.md
PROMPT_NOMBRE = os.environ.get("TUTOR_PROMPT", "system-socratico-es-v1.md")
PROMPT = RAIZ / "prompts" / PROMPT_NOMBRE
HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
TEMPERATURA = 0.2
REPETICIONES = int(os.environ.get("REPETICIONES", "1"))

CRITERIOS = ["no_da_respuesta", "una_pregunta_o_pista", "anclaje_texto",
             "nivel", "tono"]


def cargar_system():
    texto = PROMPT.read_text(encoding="utf-8")
    # El prompt real va después del separador '---' (antes hay metadatos del archivo).
    partes = texto.split("---", 1)
    return (partes[1] if len(partes) == 2 else texto).strip()


def esperar_servidor(segundos=60):
    """Espera a que el servidor de Ollama responda (se reinicia solo tras caerse)."""
    fin = time.time() + segundos
    while time.time() < fin:
        try:
            with urllib.request.urlopen(HOST + "/api/version", timeout=5):
                return True
        except Exception:
            time.sleep(3)
    return False


def quitar_pensamiento(texto):
    """Elimina el razonamiento interno filtrado de modelos híbridos (<think>...</think>)."""
    import re
    if "</think>" in texto:
        texto = texto.split("</think>", 1)[1]
    return re.sub(r"(?s)<think>.*?(</think>|$)", "", texto).strip()


def llamar_gemini(modelo, mensajes):
    """Adaptador para la API de Gemini: misma firma de salida que Ollama.
    La clave se lee de tutor-lector/.gemini_key (una sola línea)."""
    clave = (RAIZ / ".gemini_key").read_text(encoding="utf-8").strip()
    system = ""
    contents = []
    for m in mensajes:
        if m["role"] == "system":
            system = m["content"]
            continue
        rol = "model" if m["role"] == "assistant" else "user"
        contents.append({"role": rol, "parts": [{"text": m["content"]}]})
    payload = {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": system}]},
        "generationConfig": {"temperature": TEMPERATURA, "maxOutputTokens": 2048},
    }
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           + modelo + ":generateContent")
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json",
                                          "x-goog-api-key": clave})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read())
    partes = d.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    texto = "".join(p.get("text", "") for p in partes)
    uso = d.get("usageMetadata", {})
    return {"message": {"content": texto},
            "eval_count": uso.get("candidatesTokenCount"),
            "eval_duration": None}


def llamar(modelo, mensajes, con_think=False):
    if modelo.lower().startswith("gemini"):
        return llamar_gemini(modelo, mensajes)

    payload = {
        "model": modelo,
        "messages": mensajes,
        "stream": False,
        "options": {
            "temperature": TEMPERATURA,
            "num_ctx": 4096,       # contexto acotado: menos RAM en máquinas justas
            "num_predict": 256,    # un turno de tutor jamás necesita más
        },
    }
    if not con_think:
        payload["think"] = False   # apaga el razonamiento en modelos híbridos (qwen3)
    req = urllib.request.Request(
        HOST + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if not con_think:
            return llamar(modelo, mensajes, con_think=True)  # versión sin 'think'
        raise RuntimeError(f"{modelo}: HTTP {e.code}: {e.read()[:300]}")


def preparar_mensajes(modelo, system, caso):
    """Arma la conversación del caso. Para Qwen3 usa el interruptor nativo
    /no_think (el parámetro 'think' de la API no siempre es aceptado)."""
    m = modelo.lower()
    sys_txt = system + ("\n/no_think" if "qwen3" in m and "instruct" not in m else "")
    return ([{"role": "system", "content": sys_txt},
             {"role": "user", "content": "TEXTO DE LA SESIÓN:\n" + caso["texto"]},
             {"role": "assistant", "content": "Entendido, trabajaré con ese texto."}]
            + caso.get("historial", [])
            + [{"role": "user", "content": caso["entrada_estudiante"]}])


def llamar_con_reintento(modelo, mensajes):
    """Una caída del servidor no debe tumbar toda la corrida: espera y reintenta."""
    for intento in (1, 2):
        try:
            return llamar(modelo, mensajes)
        except Exception:
            if intento == 2 or not esperar_servidor():
                raise
    raise RuntimeError("sin respuesta")


def main():
    modelos = sys.argv[1:]
    if not modelos:
        print("Uso: python scripts/comparar_modelos.py <modelo1> <modelo2> ...")
        print("Ej.:  python scripts/comparar_modelos.py qwen3:8b llama3.1:8b")
        sys.exit(1)

    system = cargar_system()
    casos = [json.loads(l) for l in GOLDEN.read_text(encoding="utf-8").splitlines()
             if l.strip()]
    salida = RAIZ / "eval" / f"comparacion-{date.today():%Y%m%d}.md"

    velocidad = {m: [] for m in modelos}
    lineas = [f"# Comparación de modelos — {date.today():%d/%m/%Y}", "",
              f"Host: `{HOST}` · Temperatura: {TEMPERATURA} · "
              f"Repeticiones: {REPETICIONES} · Prompt: {PROMPT_NOMBRE}", "",
              "Califique cada respuesta con la rúbrica (`eval/rubrica.md`): "
              "marque ✔ o ✘ en cada criterio. Un caso aprueba solo con todo ✔.", ""]

    for caso in casos:
        print(f"Caso {caso['id']} ({caso['situacion']})...")
        lineas += [f"## {caso['id']} — {caso['situacion']}", "",
                   f"**Texto:** {caso['texto']}", "",
                   f"**Estudiante:** {caso['entrada_estudiante']}", "",
                   f"**Comportamiento esperado:** {caso['comportamiento_esperado']}",
                   ""]
        for modelo in modelos:
            mensajes_base = preparar_mensajes(modelo, system, caso)
            for rep in range(REPETICIONES):
                t0 = time.time()
                try:
                    resp = llamar_con_reintento(modelo, mensajes_base)
                except Exception as e:
                    lineas += [f"### {modelo}", "", f"ERROR: {e}", ""]
                    continue
                dt = time.time() - t0
                contenido = quitar_pensamiento(
                    resp.get("message", {}).get("content", "").strip())
                ec, ed = resp.get("eval_count"), resp.get("eval_duration")
                tps = (ec / (ed / 1e9)) if ec and ed else None
                if tps:
                    velocidad[modelo].append(tps)
                etiqueta = f"### {modelo}" + (f" (rep {rep+1})" if REPETICIONES > 1 else "")
                vel = f" · {tps:.1f} tok/s" if tps else ""
                palabras = len(contenido.split())
                lineas += [etiqueta, "",
                           f"*({dt:.1f} s{vel} · {palabras} palabras)*", "",
                           "> " + contenido.replace("\n", "\n> "), "",
                           "| " + " | ".join(CRITERIOS) + " |",
                           "|" + "---|" * len(CRITERIOS),
                           "| " + " | ".join("    " for _ in CRITERIOS) + " |", ""]
        lineas.append("---")
        lineas.append("")

    lineas += ["## Resumen de velocidad", "",
               "| Modelo | tok/s promedio | Muestras |", "|---|---|---|"]
    for m in modelos:
        v = velocidad[m]
        prom = f"{sum(v)/len(v):.1f}" if v else "-"
        lineas.append(f"| {m} | {prom} | {len(v)} |")
    lineas += ["", "## Veredicto", "",
               "| Modelo | Casos aprobados | % | ¿Pasa umbral 90%? |",
               "|---|---|---|---|"] + [f"| {m} |  |  |  |" for m in modelos]

    salida.write_text("\n".join(lineas), encoding="utf-8")
    print(f"\nInforme generado: {salida}")
    print("Califíquelo con la rúbrica y complete la tabla Veredicto.")


if __name__ == "__main__":
    main()
