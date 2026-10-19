# -*- coding: utf-8 -*-
"""Prueba de capacidad del servidor Ollama: latencia, throughput y concurrencia.

Fase A — Perfil de latencia vs. tamaño de prompt (sin caché: prefijos únicos).
Fase B — Concurrencia realista de aula: mismo prompt de sistema (caché compartido,
         como estudiantes de una misma sección) + preguntas distintas, con
         1, 2, 4 y 8 peticiones simultáneas.

Salida: eval/capacidad-AAAAMMDD.md y .json con percentiles y análisis de aforo.

Uso:  OLLAMA_HOST=http://IP:11434 python scripts/prueba_carga.py [modelo]
"""
import json
import os
import statistics
import sys
import threading
import time
import urllib.request
import uuid
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
MODELO = sys.argv[1] if len(sys.argv) > 1 else "llama3.1:8b"

RELLENO = ("El cacao fino de aroma se cultiva en la Costa y se fermenta durante "
           "varios días antes del secado, proceso del que dependen sus sabores "
           "florales característicos apreciados por los chocolateros. ")
SYSTEM_AULA = ("Eres un tutor socrático de lectura para estudiantes de 12 a 14 años. "
               "Nunca des la respuesta; haz una sola pregunta por turno, máximo 60 "
               "palabras, anclada al texto de la sesión.\n\nTEXTO DE LA SESIÓN:\n"
               + RELLENO * 6)
PREGUNTAS = ["¿de qué trata el texto?", "no entiendo la fermentación",
             "¿por qué es especial este cacao?", "dime la respuesta rápido",
             "¿qué pasa si se seca mal?", "esto está aburrido",
             "¿dónde se cultiva?", "¿me das un ejemplo?"]


def llamar(system, user, num_predict=80, timeout=900):
    payload = {"model": MODELO, "stream": False, "keep_alive": "30m",
               "messages": [{"role": "system", "content": system},
                            {"role": "user", "content": user}],
               "options": {"temperature": 0.2, "num_ctx": 8192,
                           "num_predict": num_predict}}
    req = urllib.request.Request(HOST + "/api/chat",
                                 data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    dt = time.time() - t0
    return {"total_s": round(dt, 2),
            "prompt_tokens": d.get("prompt_eval_count"),
            "prefill_s": round((d.get("prompt_eval_duration") or 0) / 1e9, 2),
            "gen_tokens": d.get("eval_count"),
            "decode_tok_s": round(d.get("eval_count", 0) /
                                  ((d.get("eval_duration") or 1) / 1e9), 1)}


def fase_a():
    print("== FASE A: latencia vs tamaño de prompt (prefijos únicos, sin caché) ==")
    resultados = []
    for mult in (1, 4, 10, 20):   # ~150 / ~600 / ~1500 / ~3000 tokens aprox
        system = f"[{uuid.uuid4()}] " + SYSTEM_AULA.replace(RELLENO * 6, RELLENO * mult)
        r = llamar(system, "¿de qué trata el texto?")
        r["mult"] = mult
        resultados.append(r)
        print(f"  ~{r['prompt_tokens']} tokens prompt -> total {r['total_s']} s "
              f"(prefill {r['prefill_s']} s, decode {r['decode_tok_s']} tok/s)")
    return resultados


def fase_b():
    print("\n== FASE B: concurrencia de aula (sistema compartido en caché) ==")
    llamar(SYSTEM_AULA, "hola")   # calienta el caché del prompt compartido
    resultados = []
    for n in (1, 2, 4, 8):
        tiempos, errores = [], []
        hilos = []

        def worker(i):
            try:
                r = llamar(SYSTEM_AULA, PREGUNTAS[i % len(PREGUNTAS)] +
                           f" (sesión {uuid.uuid4().hex[:6]})")
                tiempos.append(r["total_s"])
            except Exception as e:
                errores.append(str(e)[:80])

        t0 = time.time()
        for i in range(n):
            h = threading.Thread(target=worker, args=(i,))
            h.start()
            hilos.append(h)
        for h in hilos:
            h.join()
        pared = round(time.time() - t0, 2)
        if tiempos:
            fila = {"concurrencia": n, "ok": len(tiempos), "errores": len(errores),
                    "p50_s": round(statistics.median(tiempos), 1),
                    "max_s": round(max(tiempos), 1),
                    "pared_s": pared,
                    "throughput_rpm": round(60 * len(tiempos) / pared, 1)}
        else:
            fila = {"concurrencia": n, "ok": 0, "errores": len(errores),
                    "detalle": errores[:2]}
        resultados.append(fila)
        print(f"  n={n}: {fila}")
    return resultados


def main():
    print(f"Servidor: {HOST} · Modelo: {MODELO}\n")
    a = fase_a()
    b = fase_b()
    hoy = f"{date.today():%Y%m%d}"
    datos = {"fecha": str(date.today()), "host": HOST, "modelo": MODELO,
             "fase_a_latencia": a, "fase_b_concurrencia": b}
    (RAIZ / "eval" / f"capacidad-{hoy}.json").write_text(
        json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [f"# Capacidad del servidor — {MODELO} — {date.today():%d/%m/%Y}",
          f"\nHost: `{HOST}` · 8 vCPU / 16 GB RAM, sin GPU\n",
          "## Fase A — Latencia según tamaño de prompt (sin caché)\n",
          "| Tokens de prompt | Prefill (s) | Total (s) | Decode (tok/s) |",
          "|---|---|---|---|"]
    for r in a:
        md.append(f"| {r['prompt_tokens']} | {r['prefill_s']} | {r['total_s']} "
                  f"| {r['decode_tok_s']} |")
    md += ["\n## Fase B — Concurrencia (prompt de sección compartido en caché)\n",
           "| Simultáneas | OK | Errores | Mediana (s) | Máx (s) | Throughput (resp/min) |",
           "|---|---|---|---|---|---|"]
    for r in b:
        md.append(f"| {r['concurrencia']} | {r['ok']} | {r['errores']} "
                  f"| {r.get('p50_s','-')} | {r.get('max_s','-')} "
                  f"| {r.get('throughput_rpm','-')} |")
    ultimo = [r for r in b if r.get("ok")]
    if ultimo:
        rpm = max(r["throughput_rpm"] for r in ultimo)
        md += [f"\n## Lectura de aforo",
               f"\nThroughput sostenido máximo observado: **{rpm} respuestas/minuto**.",
               "Con un turno de estudiante cada ~90 s (lectura + escritura entre "
               "preguntas), el servidor sostiene aproximadamente "
               f"**{int(rpm * 1.5)} estudiantes activos simultáneos** antes de "
               "encolar de forma perceptible."]
    (RAIZ / "eval" / f"capacidad-{hoy}.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nInforme: eval/capacidad-{hoy}.md")


if __name__ == "__main__":
    main()
