# Capacidad del servidor — llama3.1:8b — 07/10/2026

Host: `http://OLLAMA_HOST:11434` · 8 vCPU / 16 GB RAM, sin GPU

## Fase A — Latencia según tamaño de prompt (sin caché)

| Tokens de prompt | Prefill (s) | Total (s) | Decode (tok/s) |
|---|---|---|---|
| 145 | 6.22 | 18.99 | 7.8 |
| 288 | 10.74 | 13.58 | 8.0 |
| 570 | 20.44 | 23.33 | 7.9 |
| 1043 | 34.56 | 38.54 | 7.6 |

## Fase B — Concurrencia (prompt de sección compartido en caché)

| Simultáneas | OK | Errores | Mediana (s) | Máx (s) | Throughput (resp/min) |
|---|---|---|---|---|---|
| 1 | 1 | 0 | 3.3 | 3.3 | 18.0 |
| 2 | 2 | 0 | 7.3 | 8.9 | 13.5 |
| 4 | 4 | 0 | 12.9 | 17.8 | 13.5 |
| 8 | 8 | 0 | 18.2 | 35.0 | 13.7 |

## Lectura de aforo

Throughput sostenido máximo observado: **18.0 respuestas/minuto**.
Con un turno de estudiante cada ~90 s (lectura + escritura entre preguntas), el servidor sostiene aproximadamente **27 estudiantes activos simultáneos** antes de encolar de forma perceptible.