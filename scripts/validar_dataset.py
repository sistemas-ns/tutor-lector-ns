# -*- coding: utf-8 -*-
"""Valida los archivos JSONL del dataset y reporta estadísticas.

Uso:  python validar_dataset.py            (valida datasets/*.jsonl y eval/*.jsonl)
      python validar_dataset.py ruta.jsonl (valida un archivo puntual)
"""
import json
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
IDIOMAS = {"es", "en"}
NIVELES = {"literal", "inferencial", "critico"}
FUENTES = {"docente", "sintetico", "real"}
MAX_PALABRAS_TUTOR = 75

CAMPOS_DIALOGO = {"id", "idioma", "nivel", "situacion", "fuente", "system_ref",
                  "texto", "messages"}
CAMPOS_GOLDEN = {"id", "idioma", "situacion", "texto", "historial",
                 "entrada_estudiante", "comportamiento_esperado", "criterios"}


def error(archivo, linea, msg, errores):
    errores.append(f"  {archivo.name}:{linea}: {msg}")


def validar_dialogo(obj, archivo, n, errores, stats):
    faltan = CAMPOS_DIALOGO - obj.keys()
    if faltan:
        return error(archivo, n, f"faltan campos: {sorted(faltan)}", errores)
    if obj["idioma"] not in IDIOMAS:
        error(archivo, n, f"idioma inválido: {obj['idioma']}", errores)
    if obj["nivel"] not in NIVELES:
        error(archivo, n, f"nivel inválido: {obj['nivel']}", errores)
    if obj["fuente"] not in FUENTES:
        error(archivo, n, f"fuente inválida: {obj['fuente']}", errores)
    msgs = obj["messages"]
    if not msgs:
        return error(archivo, n, "messages vacío", errores)
    for i, m in enumerate(msgs):
        rol_esperado = "user" if i % 2 == 0 else "assistant"
        if m.get("role") != rol_esperado:
            error(archivo, n, f"messages[{i}]: se esperaba rol {rol_esperado}", errores)
        if not str(m.get("content", "")).strip():
            error(archivo, n, f"messages[{i}]: contenido vacío", errores)
        if m.get("role") == "assistant":
            palabras = len(str(m.get("content", "")).split())
            stats["palabras_tutor"].append(palabras)
            if palabras > MAX_PALABRAS_TUTOR:
                error(archivo, n,
                      f"messages[{i}]: turno del tutor de {palabras} palabras "
                      f"(máx {MAX_PALABRAS_TUTOR})", errores)
    if msgs[-1].get("role") != "assistant":
        error(archivo, n, "el diálogo debe terminar en un turno del tutor", errores)
    stats["por_idioma"][obj["idioma"]] += 1
    stats["por_nivel"][obj["nivel"]] += 1
    stats["por_situacion"][obj["situacion"]] += 1
    stats["por_fuente"][obj["fuente"]] += 1
    stats["turnos"] += sum(1 for m in msgs if m.get("role") == "assistant")


def validar_golden(obj, archivo, n, errores, stats):
    faltan = CAMPOS_GOLDEN - obj.keys()
    if faltan:
        return error(archivo, n, f"faltan campos: {sorted(faltan)}", errores)
    if obj["idioma"] not in IDIOMAS:
        error(archivo, n, f"idioma inválido: {obj['idioma']}", errores)
    crit = obj["criterios"]
    if "nivel" in crit and crit["nivel"] not in NIVELES:
        error(archivo, n, f"criterios.nivel inválido: {crit['nivel']}", errores)
    stats["golden"] += 1


def main():
    if len(sys.argv) > 1:
        archivos = [Path(a) for a in sys.argv[1:]]
    else:
        archivos = sorted((RAIZ / "datasets").glob("*.jsonl")) + \
                   sorted((RAIZ / "eval").glob("*.jsonl"))

    errores = []
    ids = set()
    stats = {"por_idioma": Counter(), "por_nivel": Counter(),
             "por_situacion": Counter(), "por_fuente": Counter(),
             "palabras_tutor": [], "turnos": 0, "golden": 0, "dialogos": 0}

    for archivo in archivos:
        es_golden = "golden" in archivo.name
        with open(archivo, encoding="utf-8") as f:
            for n, linea in enumerate(f, 1):
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    obj = json.loads(linea)
                except json.JSONDecodeError as e:
                    error(archivo, n, f"JSON inválido: {e}", errores)
                    continue
                if obj.get("id") in ids:
                    error(archivo, n, f"id duplicado: {obj.get('id')}", errores)
                ids.add(obj.get("id"))
                if es_golden:
                    validar_golden(obj, archivo, n, errores, stats)
                else:
                    stats["dialogos"] += 1
                    validar_dialogo(obj, archivo, n, errores, stats)

    print("=== Estadísticas ===")
    print(f"Diálogos de entrenamiento: {stats['dialogos']} "
          f"({stats['turnos']} turnos del tutor)")
    print(f"Casos del conjunto dorado: {stats['golden']}")
    for titulo, c in [("Por idioma", stats["por_idioma"]),
                      ("Por nivel", stats["por_nivel"]),
                      ("Por fuente", stats["por_fuente"]),
                      ("Por situación", stats["por_situacion"])]:
        if c:
            print(f"{titulo}: " + ", ".join(f"{k}={v}" for k, v in sorted(c.items())))
    if stats["palabras_tutor"]:
        p = stats["palabras_tutor"]
        print(f"Palabras por turno del tutor: promedio {sum(p)/len(p):.0f}, máx {max(p)}")

    if errores:
        print(f"\n=== {len(errores)} ERRORES ===")
        print("\n".join(errores))
        sys.exit(1)
    print("\nTodo válido.")


if __name__ == "__main__":
    main()
