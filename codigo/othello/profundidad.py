# profundidad.py
# Desarrollado con asistencia de IA generativa (Claude, Anthropic, 2026). Ver ../README.md.
# Seccion 12.1.3 de la practica: curva de rendimiento vs. profundidad.
#
# El agente V2 juega con distintas alturas (4, 5, 6, 7) contra un rival de
# referencia fijo (por defecto V2 a altura 4). Cada apertura se juega dos veces
# cambiando colores. Para cada altura se reporta el % de victorias (con intervalo
# de Wilson 95 % y test binomial) y el tiempo promedio por jugada.
#
# Uso:
#   python profundidad.py --alturas 4 5 6 7 --aperturas 20
#   python profundidad.py --evaluador V2 --referencia V1:4 --aperturas 30

import argparse
import csv
import time

from torneo import COLUMNAS, generar_aperturas, jugar_partida, intervalo_wilson, test_binomial


def main():
    ap = argparse.ArgumentParser(description="Victorias vs. profundidad de busqueda")
    ap.add_argument("--evaluador", default="V2")
    ap.add_argument("--alturas", type=int, nargs="+", default=[4, 5, 6, 7])
    ap.add_argument("--referencia", default="V2:4", help="rival fijo, formato EVALUADOR:ALTURA")
    ap.add_argument("--aperturas", type=int, default=20)
    ap.add_argument("--plies", type=int, default=6)
    ap.add_argument("--semilla", type=int, default=2026)
    ap.add_argument("--salida", default="victorias_profundidad.csv")
    args = ap.parse_args()

    aperturas = generar_aperturas(args.aperturas, args.plies, args.semilla)
    print(f"{args.evaluador} a alturas {args.alturas} contra {args.referencia} | "
          f"{len(aperturas)} aperturas x 2 colores")

    filas, resumen = [], []
    for altura in args.alturas:
        spec = f"{args.evaluador}:{altura}"
        inicio = time.time()
        v = d = e = 0
        tiempos = []
        for i, apertura in enumerate(aperturas):
            for a_es_negro in (True, False):
                fila = jugar_partida(spec, args.referencia, apertura, a_es_negro, None)
                fila["apertura"], fila["semilla"] = i, args.semilla
                # el ganador se decide por las fichas, no por el nombre: si el agente y la
                # referencia son iguales (ej. V2:4 vs V2:4) tienen el mismo nombre
                fila["agente_b"] = f"{args.referencia} (ref)"
                dif = fila["diferencia_fichas"]
                fila["ganador"] = fila["agente_a"] if dif > 0 else fila["agente_b"] if dif < 0 else "Empate"
                filas.append(fila)
                tiempos.append(fila["tiempo_a"])
                if dif > 0:
                    v += 1
                elif dif == 0:
                    e += 1
                else:
                    d += 1
        n = v + d + e
        lo, hi = intervalo_wilson(v, n)
        p = test_binomial(v, v + d)
        t_prom = sum(tiempos) / len(tiempos)
        resumen.append((altura, v, d, e, 100 * v / n, 100 * lo, 100 * hi, p, t_prom))
        print(f"  altura {altura}: {v}-{d} (empates {e}) | {100 * v / n:.1f}% "
              f"IC95% [{100 * lo:.1f}, {100 * hi:.1f}] | p = {p:.4g} | "
              f"{t_prom:.4f} s/jugada | {time.time() - inicio:.0f}s")

    with open(args.salida, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNAS)
        w.writeheader()
        w.writerows(filas)

    print(f"\n{'altura':>7}{'V':>5}{'D':>5}{'E':>5}{'%Vict':>8}{'IC95% Wilson':>18}{'p binomial':>12}{'s/jugada':>10}")
    for altura, v, d, e, pct, lo, hi, p, t in resumen:
        print(f"{altura:>7}{v:>5}{d:>5}{e:>5}{pct:>7.1f}%{f'[{lo:.1f}, {hi:.1f}]':>18}{p:>12.4g}{t:>10.4f}")
    print(f"\nPartidas guardadas en {args.salida}")


if __name__ == "__main__":
    main()
