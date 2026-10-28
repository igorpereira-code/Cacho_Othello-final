# correlacion.py
# Desarrollado con asistencia de IA generativa (Claude, Anthropic, 2026). Ver ../README.md.
# Seccion 14.2 de la practica: correlacion entre el valor de la funcion de
# evaluacion en posiciones intermedias y la diferencia final de fichas.
#
# Idea: jugamos partidas completas (el mismo agente contra si mismo, desde
# aperturas aleatorias distintas para que las partidas no sean todas iguales).
# Cada vez que el tablero pasa por una cantidad de fichas "de corte" (mv = 20,
# 30, 40, 50), guardamos cuanto vale la funcion de evaluacion en ese momento
# (desde el punto de vista de Negro). Al final de la partida ya sabemos la
# diferencia real de fichas (Negro - Blanco). Juntando todas las partidas,
# para cada mv calculamos la correlacion de Pearson entre esos dos numeros:
# si la funcion predice bien el resultado final, la correlacion deberia ser
# alta y positiva, y subir a medida que mv crece (porque faltan menos jugadas
# para el final y es mas facil adivinar quien va a ganar).
#
# Uso:
#   python correlacion.py --evaluador V2 --altura 4 --partidas 80

import argparse
import csv
import math

from agente import AgenteOthello
from evaluador import EVALUADORES
from TableroOthello import TableroOthello
from torneo import generar_aperturas, a_estado

MV_CORTE = (20, 30, 40, 50)


def pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return None
    return cov / math.sqrt(vx * vy)


def spearman(xs, ys):
    def rangos(vs):
        orden = sorted(range(len(vs)), key=lambda i: vs[i])
        r = [0.0] * len(vs)
        i = 0
        while i < len(orden):
            j = i
            while j + 1 < len(orden) and vs[orden[j + 1]] == vs[orden[i]]:
                j += 1
            promedio = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[orden[k]] = promedio
            i = j + 1
        return r
    return pearson(rangos(xs), rangos(ys))


def jugar_y_muestrear(spec, apertura, evaluador):
    """Juega una partida agente-contra-si-mismo y devuelve {mv: valor_funcion} + diferencia final."""
    a = AgenteOthello(evaluador, altura=spec["altura"], nombre="A")
    b = AgenteOthello(evaluador, altura=spec["altura"], nombre="B")
    entorno = TableroOthello(estado_inicial=a_estado(*apertura), verbose=False)
    entorno.insertar(a, color=1)
    entorno.insertar(b, color=2)

    muestras = {}
    vistos = set()

    # enganchamos getResultado para mirar el tablero despues de cada jugada,
    # sin tocar la logica del entorno ni la de los agentes
    original = entorno.ejecutar

    def ejecutar_y_muestrear(agente):
        original(agente)
        tab_actual = entorno.juegoActual.tablero
        fichas = int((tab_actual != 0).sum())
        for mv in MV_CORTE:
            if fichas >= mv and mv not in vistos and entorno.resultado is None:
                vistos.add(mv)
                import reglas
                tab = reglas.a_tupla(tab_actual)
                turno = entorno.juegoActual.jugador
                movs = reglas.jugadas_validas(tab, turno)
                valor = evaluador.evaluar(tab, turno, movs, 1)  # perspectiva de Negro
                muestras[mv] = valor

    entorno.ejecutar = ejecutar_y_muestrear
    entorno.run()

    negro, blanco, _ = entorno.resultado
    return muestras, negro - blanco


def main():
    ap = argparse.ArgumentParser(description="Correlacion funcion de evaluacion vs resultado final")
    ap.add_argument("--evaluador", default="V2", choices=list(EVALUADORES))
    ap.add_argument("--altura", type=int, default=4)
    ap.add_argument("--partidas", type=int, default=80)
    ap.add_argument("--plies", type=int, default=4, help="jugadas al azar para variar la apertura")
    ap.add_argument("--semilla", type=int, default=2026)
    ap.add_argument("--salida", default="datos_correlacion.csv")
    args = ap.parse_args()

    evaluador = EVALUADORES[args.evaluador]()
    spec = {"altura": args.altura}
    aperturas = generar_aperturas(args.partidas, args.plies, args.semilla)

    filas = []
    for i, apertura in enumerate(aperturas):
        muestras, diferencia_final = jugar_y_muestrear(spec, apertura, evaluador)
        for mv, valor in muestras.items():
            filas.append({"partida": i, "mv": mv, "valor_funcion": valor,
                         "diferencia_final": diferencia_final})
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(aperturas)} partidas jugadas")

    with open(args.salida, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["partida", "mv", "valor_funcion", "diferencia_final"])
        w.writeheader()
        w.writerows(filas)
    print(f"\nDatos guardados en {args.salida} ({len(filas)} muestras)")

    print(f"\nCorrelacion de la funcion {args.evaluador} (altura={args.altura}) "
          f"con la diferencia final de fichas:")
    print(f"{'mv':>4}{'n':>6}{'Pearson':>12}{'Spearman':>12}")
    for mv in MV_CORTE:
        xs = [f["valor_funcion"] for f in filas if f["mv"] == mv]
        ys = [f["diferencia_final"] for f in filas if f["mv"] == mv]
        r_p = pearson(xs, ys)
        r_s = spearman(xs, ys)
        r_p_txt = f"{r_p:.3f}" if r_p is not None else "n/a"
        r_s_txt = f"{r_s:.3f}" if r_s is not None else "n/a"
        print(f"{mv:>4}{len(xs):>6}{r_p_txt:>12}{r_s_txt:>12}")


if __name__ == "__main__":
    main()
