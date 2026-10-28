# Función de Evaluación y Agentes IA — Othello y Cacho

Código de la práctica de laboratorio de Inteligencia Artificial (EC02).

## Estructura de la entrega

```
entrega/
├── codigo/
│   ├── othello/              agente, funciones de evaluación, torneo y experimentos
│   ├── cacho/                IA mejorada del Cacho, torneo y experimentos (ver cacho/README.md)
│   ├── graficos.py           genera todas las figuras del artículo a partir de ../datos
│   ├── correr_experimentos.bat   corre todos los experimentos en orden (Windows)
│   ├── requirements.txt
│   └── README.md
├── articulo/                 articulo.tex, articulo.pdf, referencias.bib, figuras/
└── datos/                    resultados_othello.csv, resultados_cacho.csv y demás CSV
```

## Requisitos

Python 3.10 o superior y:

```
python -m pip install -r requirements.txt     # numpy, pygame, matplotlib
```

## Correr todo

En Windows, doble clic en `correr_experimentos.bat` (o desde la consola). Corre los 9
experimentos en orden, deja los CSV y los registros `log_*.txt` (con las tablas y la
estadística) en `../datos/`, y al final genera las figuras en `../articulo/figuras/`.
Tiempo total: 2 a 3 horas según la computadora. Cada comando se puede correr por
separado; están todos en el `.bat`.

Todas las semillas aleatorias están fijas (por defecto 2026), así que los resultados
son reproducibles en la misma computadora.

---

## Othello (`othello/`)

### Archivos

| Archivo | Qué es |
|---|---|
| `agente.py` | Agente: minimax con poda alfa-beta |
| `evaluador.py` | Las tres funciones de evaluación (V0, V1, V2) |
| `torneo.py` | Torneo round-robin entre agentes + estadística |
| `reglas.py` | Reglas de Othello sobre un tablero de 64 casillas (tupla) |
| `TableroOthello.py` | Entorno (clase `Entorno` del docente) |
| `correlacion.py` | Correlación entre la función y la diferencia final de fichas (sección 14.2) |
| `escalabilidad.py` | Tiempo de decisión vs. profundidad, ajuste log-log (sección 14.3) |
| `profundidad.py` | Victorias vs. profundidad 4–7 (sección 12.1.3) |
| `main.py` | Partida humano (consola) vs. IA |
| `servidor.py`, `cliente_ia.py`, `cliente_humano.py`, `cliente_base.py`, `interfaz_grafica.py` | Juego en red para la competencia entre grupos |
| `AgenteIA/` | Clases base del docente |

### Funciones de evaluación (`evaluador.py`)

Todas devuelven un número desde el punto de vista del jugador que decide (positivo =
bueno para él). Los tableros terminados valen ±1 000 000 + diferencia de fichas.

- **V0 — estática:** suma de la matriz de pesos posicionales (esquinas 100, casillas X −50,
  casillas C −20, etc.). Línea base.
- **V1 — por fases:** `E = Σ wᵢ(fase)·fᵢ` con 5 características: fichas, esquinas, movilidad
  (normalizada a [−100, 100]), estabilidad aproximada por fichas de frontera, y posición
  (matriz de pesos). Los pesos cambian en apertura (< 20 fichas), medio juego (< 45) y final.
- **V2 — mejorada:** las 7 características normalizadas a [−100, 100] para que los pesos sean
  comparables: fichas, esquinas (tomadas + que se pueden tomar ya), movilidad, frontera,
  estabilidad real en bordes, posición con las casillas X/C neutralizadas cuando su esquina
  ya está ocupada, y paridad (quién hace la última jugada, solo en el final).

### Agente (`agente.py`)

Minimax con poda alfa-beta, con: nodo MAX/MIN decidido por quién tiene el turno (maneja bien
los pases), ordenamiento de jugadas, tabla de transposición, profundización iterativa con
límite de tiempo opcional, y métricas (tiempo, nodos y evaluaciones por jugada).

### Comandos

```
python torneo.py --agentes V0:4 V1:4 V2:4 --aperturas 50      # -> resultados_othello.csv
python correlacion.py --evaluador V2 --altura 4 --partidas 100
python escalabilidad.py --alturas 4 5 6 7 --partidas 4
python profundidad.py --alturas 4 5 6 7 --aperturas 20
python main.py                                                 # jugar contra la IA
python cliente_ia.py --host <IP del servidor> --agente V2:6    # competencia
```

Los agentes son deterministas: desde el mismo tablero, dos partidas entre los mismos agentes
salen idénticas. Por eso el torneo arranca cada partida desde una apertura de 6 jugadas al
azar (semilla fija) y juega cada apertura dos veces cambiando colores.

### Formato de `resultados_othello.csv` (sección 22)

`agente_a, agente_b, ganador, diferencia_fichas, profundidad_a, profundidad_b, tiempo_a,
tiempo_b`, y además `color_a, apertura, semilla, nodos_a, nodos_b, nodos_por_seg_a,
nodos_por_seg_b`.

---

## Cacho (`cacho/`)

Ver `cacho/README.md`: función de evaluación nueva, mejoras en la selección de jugadas, torneo,
ajuste de pesos, eficiencia y análisis de decisiones.

### Formato de `resultados_cacho.csv` (sección 22)

`agente_a, agente_b, puntaje_a, puntaje_b, version_funcion, tiempo_decision_promedio`
(`version_funcion` y `tiempo_decision_promedio` corresponden a `agente_b`), y además
`semilla, empieza, tiempo_decision_a, tiempo_decision_b, evaluaciones_a, evaluaciones_b,
decisiones_a, decisiones_b`.

---

## Código base y uso de asistencia de IA

- Código del docente de la asignatura: clases `AgenteIA/` (Agente, AgenteJugador, Entorno),
  el programa base del Cacho (`AgenteCacho.py`, `AgenteCachoIA.py`, `AgenteCachoHumano.py`,
  `EntornoCacho.py`, `VistaCacho.py`) y el juego en red del Othello (`servidor.py`, clientes,
  interfaz).
- Según la política de integridad académica de la práctica, se declara que en el desarrollo
  del código de este proyecto (funciones de evaluación, agentes, torneos, scripts de
  experimentos y gráficos) se utilizó asistencia de IA generativa (Claude, Anthropic, 2026)
  para el diseño, la implementación y la verificación. Los archivos desarrollados con esa
  asistencia lo indican en su encabezado.
- No se usaron implementaciones completas de Othello o Cacho de terceros; solo las librerías
  numpy, pygame y matplotlib.
