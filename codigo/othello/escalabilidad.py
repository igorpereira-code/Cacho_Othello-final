# escalabilidad.py
# Desarrollado con asistencia de IA generativa (Claude, Anthropic, 2026). Ver ../README.md.
# Seccion 14.3 de la practica: evidencia de que tan rapido crece el tiempo
# de decision con la profundidad de busqueda (altura).
#
# Jugamos partidas completas (agente V2 contra si mismo) en cada altura de la
# lista, midiendo el tiempo de CADA jugada que hace el agente (ya lo guarda
# agente.py en self.tiempos). Con el promedio por altura armamos un grafico
# log-log de tiempo vs. altura: si el tiempo creciera como una potencia de la
# altura (t = c * altura^k), en escala log-log se veria como una recta de
# pendiente k. Eso es lo que hay que comprobar (o refutar) con los datos.
#
# Uso:
#   python escalabilidad.py --evaluador V2 --alturas 4 5 6 7 --partidas 5

import argparse
import csv
import math

from agente import AgenteOthello
from evaluador import EVALUADORES
from TableroOthello import TableroOthello
from torneo import generar_aperturas, a_estado


def jugar_una(evaluador, altura, apertura):
    a = AgenteOthello(evaluador, altura=altura, nombre="A")
    b = AgenteOthello(evaluador, altura=altura, nombre="B")
    entorno = TableroOthello(estado_inicial=a_estado(*apertura), verbose=False)
    entorno.insertar(a, color=1)
    entorno.insertar(b, color=2)
    entorno.run()
    return a.tiempos + b.tiempos  # todos los tiempos por jugada de la partida


def regresion_log_log(xs, ys):
    """Ajusta log(y) = k*log(x) + log(c) por minimos cuadrados. Devuelve (k, c, r2)."""
    lx = [math.log(x) for x in xs]
    ly = [math.log(y) for y in ys]
    n = len(lx)
    mx, my = sum(lx) / n, sum(ly) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(lx, ly))
    sxx = sum((x - mx) ** 2 for x in lx)
    k = sxy / sxx
    log_c = my - k * mx
    pred = [k * x + log_c for x in lx]
    ss_res = sum((y - p) ** 2 for y, p in zip(ly, pred))
    ss_tot = sum((y - my) ** 2 for y in ly)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return k, math.exp(log_c), r2


def main():
    ap = argparse.ArgumentParser(description="Escalabilidad: tiempo de decision vs. altura")
    ap.add_argument("--evaluador", default="V2", choices=list(EVALUADORES))
    ap.add_argument("--alturas", type=int, nargs="+", default=[4, 5, 6, 7])
    ap.add_argument("--partidas", type=int, default=5)
    ap.add_argument("--plies", type=int, default=4)
    ap.add_argument("--semilla", type=int, default=2026)
    ap.add_argument("--salida", default="datos_escalabilidad.csv")
    args = ap.parse_args()

    evaluador_cls = EVALUADORES[args.evaluador]
    aperturas = generar_aperturas(args.partidas, args.plies, args.semilla)

    filas = []
    for altura in args.alturas:
        print(f"altura={altura} ...")
        for i, apertura in enumerate(aperturas):
            tiempos = jugar_una(evaluador_cls(), altura, apertura)
            for t in tiempos:
                filas.append({"altura": altura, "partida": i, "tiempo": t})
            print(f"  partida {i + 1}/{len(aperturas)}: "
                  f"{len(tiempos)} jugadas, promedio {sum(tiempos) / len(tiempos):.4f}s")

    with open(args.salida, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["altura", "partida", "tiempo"])
        w.writeheader()
        w.writerows(filas)
    print(f"\nDatos guardados en {args.salida} ({len(filas)} jugadas medidas)")

    print(f"\n{'altura':>7}{'n jugadas':>11}{'t promedio':>13}{'t maximo':>11}")
    promedios = []
    for altura in args.alturas:
        ts = [f["tiempo"] for f in filas if f["altura"] == altura]
        prom, mx = sum(ts) / len(ts), max(ts)
        promedios.append(prom)
        print(f"{altura:>7}{len(ts):>11}{prom:>13.4f}{mx:>11.4f}")

    k, c, r2 = regresion_log_log(args.alturas, promedios)
    print(f"\nAjuste log-log  tiempo ~ {c:.2e} * altura^{k:.2f}   (R^2 = {r2:.3f})")
    if r2 > 0.9:
        print("El ajuste potencia (log-log recta) es bueno: dentro de este rango de "
              "alturas el crecimiento se ve consistente con una ley de potencia.")
    else:
        print("El ajuste potencia NO es muy bueno (R^2 bajo): el crecimiento real se "
              "parece mas a una exponencial que a una potencia, como se espera de un "
              "arbol de busqueda sin cortes mas fuertes.")


if __name__ == "__main__":
    main()
