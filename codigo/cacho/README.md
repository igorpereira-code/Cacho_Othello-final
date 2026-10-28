# Cacho — IA con función de evaluación mejorada

Agente de Cacho (Generala) con Expectiminimax, construido sobre el programa base del docente.

## Requisitos

```
pip install pygame
```

Solo usa la librería estándar de Python + pygame (para la ventana del juego).

## Cómo correr todo

```
python main.py                  # jugar contra la IA (elegís base o mejorada)
python pruebas_funcion.py       # 17 comprobaciones de la función y la IA (~10 s)
```

### Torneo (sección 12.2: base vs mejorada, ≥ 100 partidas)

```
python torneo_cacho.py torneo --agentes base mejorada --semillas 100
```

Cada semilla se juega 2 veces cambiando quién empieza → 200 partidas (~4 min).
Guarda `resultados_cacho.csv` y muestra: victorias, % de victorias con intervalo de
Wilson 95 %, test binomial, diferencia de puntaje promedio con intervalo bootstrap,
tiempo y evaluaciones por decisión.

### Ajuste experimental de pesos (punto 10)

```
python torneo_cacho.py torneo --agentes w2_06 w2_08 mejorada w2_12 --semillas 400 --sin-adaptativa --salida ajuste_w2.csv
python torneo_cacho.py torneo --agentes sin_varianza mejorada varianza_alta --semillas 1000 --sin-adaptativa --salida ajuste_w3.csv
python torneo_cacho.py torneo --agentes mejorada sin_adaptativa --semillas 300 --salida ajuste_adaptativa.csv
```

El primero compara el peso del futuro `w2` (0.6 es el α de la función base, 1 es el
de la mejorada) en un torneo todos contra todos (4800 partidas, ~25 min). El segundo compara tres valores del peso de riesgo `w3` (6000 partidas, ~30 min; con
`--sin-adaptativa` se busca solo a altura 1 para que sea rápido). Los torneos con más de
dos agentes muestran además el test chi-cuadrado. El tercero mide si la profundidad adaptativa
mejora el juego (600 partidas, ~30 min).

Si una variante resulta significativamente mejor, se cambia el valor por defecto en
`funcion_evaluacion.py` (`W2`, `W3_POR_ETAPA`) o en `agente_ia.py` (`umbral_critico`). Si
ninguna diferencia es significativa, se mantiene la más simple — también es un resultado
válido para el artículo.

### Eficiencia (sección 12.2: antes/después de optimizaciones)

```
python torneo_cacho.py eficiencia --estados 200 --estados-prof2 20
```

Toma 200 situaciones reales de partidas y mide tiempo, evaluaciones y si se elige la
misma jugada con / sin poda y memoización, a altura 1 y 2. Guarda `eficiencia_cacho.csv`.

### Análisis de decisiones (sección 12.2)

```
python torneo_cacho.py decisiones --estados 300
```

Casos donde la IA mejorada decide distinto que la base, con ejemplos. Guarda
`decisiones_cacho.csv`.

### Recalcular la estadística sin volver a jugar

```
python torneo_cacho.py analizar resultados_cacho.csv
```

## Archivos

| Archivo | Qué es |
|---|---|
| `funcion_evaluacion.py` | Función de evaluación mejorada y tablas de probabilidades |
| `agente_ia.py` | IA mejorada (`AgenteCachoIAMejorada`), hereda de la IA del docente |
| `torneo_cacho.py` | Torneo IA vs IA, estadística, eficiencia y análisis de decisiones |
| `pruebas_funcion.py` | Pruebas contra valores calculables a mano |
| `main.py` | Deja elegir IA base o mejorada |
| `EntornoCacho.py` | Una corrección (ver abajo) |
| `AgenteCacho.py`, `AgenteCachoIA.py`, `AgenteCachoHumano.py`, `VistaCacho.py`, `AgenteIA/` | Código del docente, sin cambios |

## Formato de `resultados_cacho.csv`

Columnas de la sección 22: `agente_a, agente_b, puntaje_a, puntaje_b, version_funcion,
tiempo_decision_promedio` (`version_funcion` y `tiempo_decision_promedio` corresponden a
`agente_b`). Columnas adicionales para el análisis: `semilla, empieza, tiempo_decision_a,
tiempo_decision_b, evaluaciones_a, evaluaciones_b, decisiones_a, decisiones_b`.

## La función nueva

```
E_nueva(s) = w1·f1(s) + w2·f2(s) + w3(etapa)·f3(s)
```

- **f1** = puntaje propio − puntaje del rival
- **f2** = puntos que cada jugador espera sumar hasta el final (propio − rival). Para quien
  está en su turno usa los dados actuales y las tiradas que le quedan; solo cuenta los turnos
  que le quedan a cada uno, eligiendo las mejores categorías libres.
- **f3** = riesgo: −σ · tanh(μ / σ), donde μ = f1 + f2 es la diferencia final esperada y σ
  su desviación estándar. Si va ganando claro conviene jugar seguro (f3 ≈ −σ); si va
  perdiendo claro, arriesgar (f3 ≈ +σ); si está parejo, f3 ≈ 0.

Todos los términos están en puntos. Rango de los pesos: `w1 = 1` (fija la escala),
`w2 > 0`, `0 ≤ w3 < 1`. Con `w3 < 1` la evaluación siempre sube cuando sube μ (la derivada
es 1 − w3 / cosh²(μ/σ) > 0), así que la IA nunca prefiere sumar menos puntos solo para
cambiar el riesgo. (Una primera versión usaba un cambio brusco de signo en μ = 0, y eso
hacía que en algunos casos la IA anotara menos puntos de los posibles; la prueba
"no regala puntos" de `pruebas_funcion.py` controla ese caso.)

Pesos por defecto: `w1 = 1`, `w2 = 1`, `w3` = 0 / 0.1 / 0.3 en inicio / medio / final
(valores iniciales; se ajustan con el torneo de arriba).

## Limitaciones de la base y cómo se resuelven

| Limitación de la función base | Solución |
|---|---|
| α = 0.6 arbitrario | `f2` está en puntos igual que `f1`, por eso `w2 = 1`; los pesos se ajustan experimentalmente |
| Valores esperados estáticos | Dinámicos: dependen de los dados y las tiradas que quedan |
| Probabilidades mal calculadas (252 combinaciones como si fueran igual de probables: la "grande" valía 1.19 en vez de 0.04) | Probabilidades reales de los dados |
| No considera la varianza | Término `f3`, con peso distinto por etapa |
| No modela la interacción entre categorías | Solo se cuentan los turnos que quedan y las mejores categorías libres |
| Evaluaba desde el jugador equivocado después de anotar | Siempre se evalúa desde el jugador que decide |

## Mejoras en la selección de jugadas (marcadas como `CAMBIO` en `agente_ia.py`)

- **Poda:** solo se consideran las formas de tirar que son la mejor opción para alguna
  categoría libre, sin repetir las que guardan los mismos dados.
- **Memoización:** las tablas se calculan una vez al importar; además, un estado ya
  calculado del árbol no se vuelve a calcular.
- **Profundidad adaptativa:** si las dos mejores acciones difieren en menos de 1 punto, se
  vuelve a buscar con un nivel más.

## Corrección al entorno del docente

En `EntornoCacho._estado_inicial` el primer turno empezaba con los dados en (1,1,1,1,1) sin
tirar, que ya es una "grande": el primer jugador se llevaba 50 puntos gratis (las dos IAs lo
aprovechaban). Ahora el primer turno empieza con una tirada real, como todos los demás.

## Nota sobre las reglas

El programa base termina el juego con 10 anotaciones **en total** (5 categorías por
jugador). La función nueva usa la misma regla (`RONDAS_TOTALES` en `funcion_evaluacion.py`);
si la regla correcta fuera 10 por jugador, se cambia ese valor y el de `testTerminal` /
`EntornoCacho`.

## Uso de asistencia de IA

Según la política de integridad académica de la práctica, se declara que en el desarrollo
de `funcion_evaluacion.py`, `agente_ia.py`, `torneo_cacho.py` y `pruebas_funcion.py` se
utilizó asistencia de IA generativa (Claude, Anthropic, 2026) para el diseño, la
implementación y la verificación del código. El código base del juego es del docente de
la asignatura.
