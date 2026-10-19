# -*- coding: utf-8 -*-
"""Evalúa el ESTADO de un modelo contra el conjunto dorado y lo documenta.

Genera un informe fechado con la respuesta a cada caso, la calificación
automática por criterio de la rúbrica CON SU GRADO DE CERTEZA (alta/media/baja),
y un JSON comparable entre corridas. La misma corrida ejecutada sobre el modelo
afinado (v2) documenta el estado final; comparar ambos JSON muestra la mejora.

Uso:
    python scripts/evaluar_baseline.py qwen3:4b
    python scripts/evaluar_baseline.py qwen3:8b --etiqueta final
    OLLAMA_HOST=http://IP:11434 python scripts/evaluar_baseline.py ...

Método de calificación automática (transparente y reproducible):
- no_da_respuesta: busca las `frases_prohibidas` del caso (certeza media).
- una_pregunta_o_pista: cuenta signos de interrogación (certeza alta/baja).
- anclaje_texto: palabras que dirigen al texto (certeza media).
- nivel y tono: siempre requieren juicio humano (certeza baja, quedan pendientes).
- longitud <= 75 palabras: objetivo (certeza alta).
El % automático es PROVISIONAL: el veredicto final lo da la revisión docente.
"""
import json
import re
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comparar_modelos import (HOST, TEMPERATURA, cargar_system, GOLDEN, PROMPT_NOMBRE,
                              llamar_con_reintento, preparar_mensajes,
                              quitar_pensamiento)

RAIZ = Path(__file__).resolve().parent.parent
ANCLAJE = ["texto", "parrafo", "frase", "lee", "leeme", "busca", "relee",
           "aviso", "mapa", "linea", "dice", "primera", "segunda"]
ELOGIOS_VACIOS = ["muy bien!", "¡muy bien!", "excelente!", "¡excelente!",
                  "genial!", "¡genial!", "perfecto!", "¡perfecto!"]


def plano(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def calificar(caso, respuesta):
    """Devuelve {criterio: {veredicto: True/False/None, certeza, detalle}}."""
    r = plano(respuesta)
    res = {}

    proh = [plano(f) for f in caso.get("frases_prohibidas", [])]
    if proh:
        halladas = [f for f in proh if f in r]
        res["no_da_respuesta"] = {
            "veredicto": not halladas, "certeza": "media",
            "detalle": ("contiene: " + "; ".join(halladas)) if halladas
                       else "sin frases prohibidas"}
    else:
        res["no_da_respuesta"] = {"veredicto": None, "certeza": "baja",
                                  "detalle": "caso sin frases prohibidas: revisar a mano"}

    n_preg = respuesta.count("¿") or respuesta.count("?")
    if n_preg >= 3:
        v = {"veredicto": False, "certeza": "alta",
             "detalle": f"{n_preg} preguntas: cuestionario"}
    elif n_preg == 0:
        v = {"veredicto": None, "certeza": "baja",
             "detalle": "sin pregunta: verificar si hay pista válida"}
    else:
        v = {"veredicto": True, "certeza": "alta" if n_preg == 1 else "media",
             "detalle": f"{n_preg} pregunta(s)"}
    res["una_pregunta_o_pista"] = v

    if caso["criterios"].get("anclaje_texto", True):
        con_ancla = [p for p in ANCLAJE if p in r]
        res["anclaje_texto"] = {
            "veredicto": bool(con_ancla), "certeza": "media",
            "detalle": ("señales: " + ", ".join(con_ancla[:4])) if con_ancla
                       else "sin señales de anclaje"}
    else:
        res["anclaje_texto"] = {"veredicto": True, "certeza": "alta",
                                "detalle": "no exigido en este caso"}

    res["nivel"] = {"veredicto": None, "certeza": "baja",
                    "detalle": f"esperado: {caso['criterios'].get('nivel')} (humano)"}

    elogio = [e for e in ELOGIOS_VACIOS if e in respuesta.lower()]
    res["tono"] = ({"veredicto": False, "certeza": "media",
                    "detalle": "elogio vacío: " + elogio[0]} if elogio else
                   {"veredicto": None, "certeza": "baja", "detalle": "juicio humano"})

    palabras = len(respuesta.split())
    res["longitud"] = {"veredicto": palabras <= 75, "certeza": "alta",
                       "detalle": f"{palabras} palabras (máx 75)"}
    return res


SIMBOLO = {True: "SÍ", False: "NO", None: "?"}


def main():
    argv = sys.argv[1:]
    etiqueta = "inicial"
    if "--etiqueta" in argv:
        i = argv.index("--etiqueta")
        etiqueta = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1:
        print("Uso: python scripts/evaluar_baseline.py <modelo> [--etiqueta inicial|final]")
        sys.exit(1)
    modelo = args[0]

    system = cargar_system()
    casos = [json.loads(l) for l in GOLDEN.read_text(encoding="utf-8").splitlines()
             if l.strip()]
    hoy = f"{date.today():%Y%m%d}"
    base = f"baseline-{etiqueta}-{re.sub(r'[^a-z0-9]+', '-', modelo.lower())}-{hoy}"

    resultado = {"fecha": str(date.today()), "etiqueta": etiqueta, "modelo": modelo,
                 "host": HOST, "temperatura": TEMPERATURA,
                 "prompt": PROMPT_NOMBRE, "casos": []}
    md = [f"# Estado {etiqueta.upper()} del modelo — {modelo}", "",
          f"Fecha: {date.today():%d/%m/%Y} · Host: `{HOST}` · Temperatura: "
          f"{TEMPERATURA} · Prompt: {PROMPT_NOMBRE}", "",
          "Calificación automática por criterio con grado de certeza. "
          "**El % automático es provisional**: `?` = requiere juicio docente "
          "(el método está descrito en el encabezado del script).", ""]

    fallos_auto = 0
    aprobados_auto = 0
    for caso in casos:
        print(f"Caso {caso['id']}...")
        t0 = time.time()
        try:
            resp = llamar_con_reintento(modelo, preparar_mensajes(modelo, system, caso))
        except Exception as e:
            md += [f"## {caso['id']} — ERROR: {e}", ""]
            resultado["casos"].append({"id": caso["id"], "error": str(e)})
            fallos_auto += 1
            continue
        dt = time.time() - t0
        contenido = quitar_pensamiento(resp.get("message", {}).get("content", "").strip())
        ec, ed = resp.get("eval_count"), resp.get("eval_duration")
        tps = round(ec / (ed / 1e9), 1) if ec and ed else None

        notas = calificar(caso, contenido)
        con_fallo = any(v["veredicto"] is False for v in notas.values())
        pendientes = [k for k, v in notas.items() if v["veredicto"] is None]
        if con_fallo:
            fallos_auto += 1
        else:
            aprobados_auto += 1

        estado = ("FALLO automático" if con_fallo else
                  f"aprobado provisional (pendiente humano: {', '.join(pendientes)})"
                  if pendientes else "aprobado")
        md += [f"## {caso['id']} — {caso['situacion']}", "",
               f"**Estudiante:** {caso['entrada_estudiante']}", "",
               f"**Respuesta del modelo** *({dt:.0f} s"
               + (f" · {tps} tok/s" if tps else "") + f")*:", "",
               "> " + contenido.replace("\n", "\n> "), "",
               f"**Veredicto automático: {estado}**", "",
               "| Criterio | Auto | Certeza | Detalle |", "|---|---|---|---|"]
        for k, v in notas.items():
            md.append(f"| {k} | {SIMBOLO[v['veredicto']]} | {v['certeza']} | "
                      f"{v['detalle']} |")
        md += ["", "---", ""]

        resultado["casos"].append({
            "id": caso["id"], "situacion": caso["situacion"],
            "respuesta": contenido, "segundos": round(dt, 1), "tok_s": tps,
            "criterios": {k: {"veredicto": v["veredicto"], "certeza": v["certeza"]}
                          for k, v in notas.items()},
            "fallo_automatico": con_fallo, "pendientes_humano": pendientes})

    total = len(casos)
    pct = 100.0 * aprobados_auto / total if total else 0
    resultado["resumen"] = {"casos": total, "aprobados_provisional": aprobados_auto,
                            "fallos_automaticos": fallos_auto,
                            "pct_provisional": round(pct, 1)}
    md += ["## Resumen del estado " + etiqueta, "",
           f"- Casos: {total}",
           f"- Aprobados provisionales (sin fallo automático): {aprobados_auto} "
           f"(**{pct:.0f}%**)",
           f"- Fallos automáticos: {fallos_auto}",
           "- Umbral de despliegue (tras revisión humana): **90%**", "",
           "Este informe documenta el estado " + etiqueta + " del modelo. La misma "
           "corrida sobre la versión afinada, con `--etiqueta final`, permite "
           "comparar ambos JSON y demostrar la mejora."]

    (RAIZ / "eval" / f"{base}.md").write_text("\n".join(md), encoding="utf-8")
    (RAIZ / "eval" / f"{base}.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nInforme: eval/{base}.md")
    print(f"Datos:   eval/{base}.json")
    print(f"Aprobados provisionales: {aprobados_auto}/{total} ({pct:.0f}%)")


if __name__ == "__main__":
    main()
