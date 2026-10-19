# -*- coding: utf-8 -*-
"""Convierte los diálogos escritos por docentes (formato simple .txt) a JSONL.

Formato de entrada (ver docs/guia-anotacion.md): archivos en
datasets/aportes-docentes/*.txt, con diálogos separados por una línea `===`:

    idioma: es
    nivel: inferencial
    titulo: El sueño y las pantallas
    situacion: respuesta superficial
    ---
    TEXTO: fragmento...
    ESTUDIANTE: ...
    TUTOR: ...
    ===

Salida: datasets/aportes-docentes.jsonl (se regenera completo en cada corrida).
Luego correr validar_dataset.py.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "datasets" / "aportes-docentes"
SALIDA = RAIZ / "datasets" / "aportes-docentes.jsonl"


def sin_tildes(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def parsear_bloque(bloque, origen, num, errores):
    partes = bloque.split("---", 1)
    if len(partes) != 2:
        errores.append(f"{origen} diálogo {num}: falta la línea '---' entre cabecera y turnos")
        return None
    cab, cuerpo = partes
    meta = {}
    for linea in cab.strip().splitlines():
        m = re.match(r"^(\w+)\s*:\s*(.+)$", linea.strip())
        if m:
            meta[sin_tildes(m.group(1).lower())] = m.group(2).strip()

    for campo in ("idioma", "nivel"):
        if campo not in meta:
            errores.append(f"{origen} diálogo {num}: falta '{campo}:' en la cabecera")
            return None
    meta["nivel"] = sin_tildes(meta["nivel"].lower())

    # Turnos: etiquetas TEXTO / ESTUDIANTE / TUTOR, cada una puede ocupar varias líneas.
    trozos = re.split(r"^(TEXTO|ESTUDIANTE|TUTOR)\s*:\s*", cuerpo.strip(),
                      flags=re.MULTILINE)
    texto = ""
    messages = []
    for etiqueta, contenido in zip(trozos[1::2], trozos[2::2]):
        contenido = " ".join(contenido.split())
        if not contenido:
            continue
        if etiqueta == "TEXTO":
            texto = contenido
        elif etiqueta == "ESTUDIANTE":
            messages.append({"role": "user", "content": contenido})
        else:
            messages.append({"role": "assistant", "content": contenido})

    if not texto:
        errores.append(f"{origen} diálogo {num}: falta el bloque TEXTO:")
        return None
    if not messages:
        errores.append(f"{origen} diálogo {num}: no hay turnos ESTUDIANTE/TUTOR")
        return None

    return {
        "idioma": meta["idioma"],
        "nivel": meta["nivel"],
        "situacion": meta.get("situacion", "sin clasificar"),
        "fuente": "docente",
        "system_ref": "socratico-es-v1" if meta["idioma"] == "es" else "socratico-en-v1",
        "texto": texto,
        "messages": messages,
        "_origen": f"{origen} #{num}",
        "_titulo": meta.get("titulo", ""),
    }


def main():
    ENTRADA.mkdir(exist_ok=True)
    archivos = sorted(ENTRADA.glob("*.txt"))
    if not archivos:
        print(f"No hay archivos .txt en {ENTRADA}")
        print("Los docentes deben guardar ahí sus diálogos (ver docs/guia-anotacion.md).")
        return

    errores = []
    registros = []
    for archivo in archivos:
        contenido = archivo.read_text(encoding="utf-8-sig")
        for num, bloque in enumerate(re.split(r"^===\s*$", contenido,
                                              flags=re.MULTILINE), 1):
            if not bloque.strip():
                continue
            reg = parsear_bloque(bloque, archivo.name, num, errores)
            if reg:
                registros.append(reg)

    contador = {"es": 0, "en": 0}
    with open(SALIDA, "w", encoding="utf-8") as f:
        for reg in registros:
            idioma = reg["idioma"]
            contador[idioma] = contador.get(idioma, 0) + 1
            reg["id"] = f"{idioma}-doc-{contador[idioma]:04d}"
            f.write(json.dumps(reg, ensure_ascii=False) + "\n")

    print(f"Convertidos {len(registros)} diálogos de {len(archivos)} archivo(s) "
          f"-> {SALIDA.name}")
    if errores:
        print(f"\n{len(errores)} problemas (esos diálogos NO se convirtieron):")
        print("\n".join("  " + e for e in errores))
        sys.exit(1)
    print("Ahora corre: python scripts/validar_dataset.py")


if __name__ == "__main__":
    main()
