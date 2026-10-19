# Tutor Lector NS — evaluation harness, golden sets and prompts

Companion repository for the paper *A Self-Hosted Scaffolded-Dialogue Reading Tutor for Secondary School:
Certainty-Graded Evaluation, Teacher Judgement, and the Gap Between Benchmark and Deployed Fidelity*
(Unidad Educativa Neue Schule, Cuenca, Ecuador; submitted to AIESC 2027).

**Repositorio complementario** del artículo. Contiene todo lo necesario para reproducir las mediciones:
los conjuntos dorados, la rúbrica, los prompts versionados, los scripts del arnés y los resultados crudos.
No contiene datos de estudiantes ni hojas de calificación docente con información identificable.

## Contents / Contenido

| Path | What it is |
|---|---|
| `prompts/system-socratico-es-v1..v4.md` | Versioned system prompts (Spanish); each header records the measured failures that motivated the version. `persona-moodle-v4.txt` is the v4 body as pasted into the Moodle plugin. |
| `prompts/system-generico-es.md` | Naive baseline prompt (55 % fidelity). |
| `eval/golden-set-es.jsonl` | 40 adversarial cases, 8 situations, short texts (the benchmark). |
| `eval/golden-set-es-largo.jsonl` | 8 long-text cases (~330 words). |
| `eval/golden-set-es-retro.jsonl`, `golden-set-es-tungurahua.jsonl`, `golden-set-es-envivo80.jsonl` | The 2 × 40 classroom-text utterances used in the live deployment study and in the isolated-turn re-run. |
| `eval/rubrica.md` | The five-criterion rubric with certainty levels. |
| `eval/baseline-*.md / .json` | Raw outputs of every run reported in the paper (model, prompt, date, per-case response and automatic verdict). |
| `eval/capacidad-*.md` | Server capacity measurements. |
| `eval/Calificacion_Docente_*.xlsx` | Blank teacher scoring sheets (templates). |
| `scripts/evaluar_baseline.py`, `comparar_modelos.py` | The harness: runs a golden set against an Ollama server and scores it. |
| `scripts/prueba_carga.py` | Concurrency test. |
| `docs/` | Annotation guide, teacher instruments (surveys, live-test script), the two classroom texts, aggregated survey results and the deployed-vs-harness comparison. |

## Reproduce a run / Reproducir una corrida

```bash
pip install -r requirements.txt   # only standard library + openpyxl for the sheets
export OLLAMA_HOST=http://<your-ollama-server>:11434
export TUTOR_PROMPT=system-socratico-es-v4.md
export GOLDEN_SET=golden-set-es.jsonl
python scripts/evaluar_baseline.py llama3.1:8b --etiqueta mi-corrida
```

Temperature is fixed at 0.2 and context at 4,096 tokens inside the scripts. The server address in the
raw result files has been replaced by `OLLAMA_HOST`.

## Licence / Licencia

Code (`scripts/`): MIT. Prompts, golden sets, rubric, texts and documents: CC BY 4.0.
Please cite the paper when using the golden sets or the rubric.

## Contact

Departamento de Tecnología, Unidad Educativa Neue Schule, Cuenca, Ecuador — sistemas@neueschule.edu.ec
