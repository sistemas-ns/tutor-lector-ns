# -*- coding: utf-8 -*-
"""Convierte fichas PDF rellenadas por docentes a JSONL.

Los docentes llenan Ficha_Dialogos_Tutor_Lector.pdf (campos d{n}_*) y guardan sus
copias en datasets/fichas-pdf/. Este script lee todos los .pdf de esa carpeta y
genera datasets/aportes-fichas.jsonl (se regenera completo en cada corrida).

Uso:  python scripts/convertir_pdf_docente.py
Luego: python scripts/validar_dataset.py
"""
import json
import sys
from pathlib import Path

from pypdf import PdfReader

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "datasets" / "fichas-pdf"
SALIDA = RAIZ / "datasets" / "aportes-fichas.jsonl"

SITUACIONES = {
    1: "pide la respuesta / tarea",
    2: "respuesta incorrecta",
    3: "frustracion",
    4: "respuesta superficial",
    5: "divaga fuera del texto",
    6: "progresion y sintesis",
    7: "bloqueo de vocabulario (L2)",
}


def marcado(valor):
    """True si una casilla del PDF está marcada."""
    v = str(valor or "").strip("/").lower()
    return v not in ("", "off")


def valor(campos, nombre):
    f = campos.get(nombre)
    if f is None:
        return ""
    v = f.get("/V", "")
    return str(v).strip() if v else ""


def extraer_dialogos(pdf, errores):
    campos = PdfReader(pdf).get_fields() or {}
    registros = []
    for n in (1, 2, 3):
        texto = valor(campos, f"d{n}_texto")
        turnos = []
        for i in (1, 2, 3):
            e = valor(campos, f"d{n}_e{i}")
            t = valor(campos, f"d{n}_t{i}")
            if e:
                turnos.append({"role": "user", "content": " ".join(e.split())})
            if t:
                turnos.append({"role": "assistant", "content": " ".join(t.split())})

        if not texto and not turnos:
            continue  # ficha en blanco: normal, no todas se usan

        origen = f"{pdf.name} diálogo {n}"
        if not texto:
            errores.append(f"{origen}: falta el TEXTO")
            continue
        if not turnos:
            errores.append(f"{origen}: no hay turnos escritos")
            continue
        if turnos[0]["role"] != "user":
            errores.append(f"{origen}: debe empezar con un turno del ESTUDIANTE")
            continue
        if turnos[-1]["role"] != "assistant":
            errores.append(f"{origen}: debe terminar con un turno del TUTOR")
            continue

        if marcado(campos.get(f"d{n}_idioma_en", {}).get("/V")):
            idioma = "en"
        elif marcado(campos.get(f"d{n}_idioma_es", {}).get("/V")):
            idioma = "es"
        else:
            errores.append(f"{origen}: marque el idioma")
            continue

        nivel = None
        for niv in ("literal", "inferencial", "critico"):
            if marcado(campos.get(f"d{n}_nivel_{niv}", {}).get("/V")):
                nivel = niv
                break
        if not nivel:
            errores.append(f"{origen}: marque el nivel")
            continue

        sits = [SITUACIONES[i] for i in SITUACIONES
                if marcado(campos.get(f"d{n}_sit_{i}", {}).get("/V"))]

        registros.append({
            "idioma": idioma,
            "nivel": nivel,
            "situacion": "; ".join(sits) if sits else "sin clasificar",
            "fuente": "docente",
            "system_ref": "socratico-es-v1" if idioma == "es" else "socratico-en-v1",
            "texto": " ".join(texto.split()),
            "messages": turnos,
            "_origen": origen,
            "_titulo": valor(campos, f"d{n}_titulo"),
        })
    return registros


def main():
    ENTRADA.mkdir(exist_ok=True)
    archivos = sorted(ENTRADA.glob("*.pdf"))
    if not archivos:
        print(f"No hay fichas .pdf en {ENTRADA}")
        print("Guarde ahí las fichas llenas que envíen los docentes.")
        return

    errores = []
    registros = []
    for pdf in archivos:
        try:
            registros.extend(extraer_dialogos(pdf, errores))
        except Exception as e:  # PDF corrupto o sin formulario
            errores.append(f"{pdf.name}: no se pudo leer ({e})")

    contador = {}
    with open(SALIDA, "w", encoding="utf-8") as f:
        for reg in registros:
            idioma = reg["idioma"]
            contador[idioma] = contador.get(idioma, 0) + 1
            reg["id"] = f"{idioma}-pdf-{contador[idioma]:04d}"
            f.write(json.dumps(reg, ensure_ascii=False) + "\n")

    print(f"Convertidos {len(registros)} diálogos de {len(archivos)} ficha(s) "
          f"-> {SALIDA.name}")
    if errores:
        print(f"\n{len(errores)} problemas (esos diálogos NO se convirtieron):")
        print("\n".join("  " + e for e in errores))
        sys.exit(1)
    print("Ahora corre: python scripts/validar_dataset.py")


if __name__ == "__main__":
    main()
