# torneo.py
# Desarrollado con asistencia de IA generativa (Claude, Anthropic, 2026). Ver ../README.md.
# Torneo round-robin entre agentes de Othello + analisis estadistico.
#
# Uso (desde la carpeta othello/):
#   python torneo.py                                   # V0, V1 y V2 a altura 4
#   python torneo.py --agentes V1:4 V2:4 --aperturas 50
#   python torneo.py --agentes V2:6 V1:6 --tiempo 2    # 2 s por jugada
#
# Formato de agente: EVALUADOR:ALTURA (EVALUADOR = V0, V1 o V2).
#
# Por que aperturas aleatorias: los agentes son deterministas, asi que dos
# partidas desde el mismo tablero salen IDENTICAS. Para tener partidas
# distintas (y poder hacer estadistica) cada partida arranca desde una
# apertura de unas pocas jugadas al azar (con semilla fija -> reproducible),
# y cada apertura se juega DOS veces cambiando colores, para que ninguna
# apertura favorezca a un agente.

import argparse
import csv
import math
import random
from itertools import combinations

from AgenteIA.AgenteJugador import ElEstado
from TableroOthello import TableroOthello
from agente import AgenteOthello
from evaluador import EVALUADORES
import reglas

COLUMNAS = ["agente_a", "agente_b", "ganador", "diferencia_fichas",
            "profundidad_a", "profundidad_b", "tiempo_a", "tiempo_b",
            "color_a", "apertura", "semilla", "nodos_a", "nodos_b",
            "nodos_por_seg_a", "nodos_por_seg_b"]


# ----------------------------------------------------------------------
# Agentes y aperturas
# ----------------------------------------------------------------------
def crear_agente(spec, tiempo_limite=None):
    nombre_eval, altura = spec.split(":")
    return AgenteOthello(EVALUADORES[nombre_eval](), altura=int(altura),
                         tiempo_limite=tiempo_limite, nombre=spec)


def generar_aperturas(cantidad, plies, semilla):
    """Tableros distintos obtenidos jugando `plies` jugadas al azar desde el inicio."""
    rng = random.Random(semilla)
    vistas, aperturas = set(), []
    intentos = 0
    while len(aperturas) < cantidad and intentos < cantidad * 100:
        intentos += 1
        tab, turno = reglas.tablero_inicial(), 1
        movs = reglas.jugadas_validas(tab, 1)
        for _ in range(plies):
            tab, turno, movs = reglas.siguiente(tab, rng.choice(movs), turno)
            if not movs:
                break
        if movs and (tab, turno) not in vistas:
            vistas.add((tab, turno))
            aperturas.append((tab, turno, movs))
    return aperturas


def a_estado(tab, turno, movs):
    return ElEstado(jugador=turno, tablero=reglas.a_numpy(tab),
                    movidas=[reglas.a_fila_col(i) for i in movs], get_utilidad=0)


def _promedio(xs):
    return sum(xs) / len(xs) if xs else 0.0


def jugar_partida(spec_a, spec_b, apertura, a_es_negro, tiempo_limite):
    """Juega una partida usando el entorno TableroOthello. Devuelve una fila del CSV."""
    a = crear_agente(spec_a, tiempo_limite)
    b = crear_agente(spec_b, tiempo_limite)
    entorno = TableroOthello(estado_inicial=a_estado(*apertura), verbose=False)
    entorno.insertar(a, color=1 if a_es_negro else 2)
    entorno.insertar(b, color=2 if a_es_negro else 1)
    entorno.run()

    negro, blanco, ganador_color = entorno.resultado
    fichas_a, fichas_b = (negro, blanco) if a_es_negro else (blanco, negro)
    if ganador_color == 0:
        ganador = "Empate"
    else:
        ganador = spec_a if ganador_color == a.color else spec_b

    def nps(ag):
        t = sum(ag.tiempos)
        return round(sum(ag.nodos) / t) if t > 0 else 0

    return {
        "agente_a": spec_a, "agente_b": spec_b, "ganador": ganador,
        "diferencia_fichas": fichas_a - fichas_b,
        # profundidad fija -> la altura configurada; con limite de tiempo -> la alcanzada en promedio
        "profundidad_a": a.altura if tiempo_limite is None else round(_promedio(a.profundidades), 2),
        "profundidad_b": b.altura if tiempo_limite is None else round(_promedio(b.profundidades), 2),
        "tiempo_a": round(_promedio(a.tiempos), 4),
        "tiempo_b": round(_promedio(b.tiempos), 4),
        "color_a": "negro" if a_es_negro else "blanco",
        "nodos_a": round(_promedio(a.nodos)), "nodos_b": round(_promedio(b.nodos)),
        "nodos_por_seg_a": nps(a), "nodos_por_seg_b": nps(b),
    }


# ----------------------------------------------------------------------
# Estadistica (sin dependencias; chi-cuadrado usa scipy si esta instalado)
# ----------------------------------------------------------------------
def test_binomial(k, n, p=0.5):
    """p-valor exacto bilateral de H0: proporcion de victorias = p."""
    if n == 0:
        return 1.0
    # se calcula con logaritmos: con muchas partidas math.comb(n, i) es un entero
    # demasiado grande para pasarlo a float
    lp, lq = math.log(p), math.log(1 - p)
    log_probs = [math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * lp + (n - i) * lq
                 for i in range(n + 1)]
    obs = log_probs[k]
    return min(1.0, sum(math.exp(lq_i) for lq_i in log_probs if lq_i <= obs + 1e-9))


def intervalo_wilson(k, n, z=1.96):
    """Intervalo de confianza de Wilson (95 %) para la proporcion k/n."""
    if n == 0:
        return (0.0, 1.0)
    phat = k / n
    den = 1 + z * z / n
    centro = (phat + z * z / (2 * n)) / den
    margen = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centro - margen), min(1.0, centro + margen))


def test_chi_cuadrado(tabla):
    """Chi-cuadrado de homogeneidad: ¿todos los agentes tienen la misma tasa de victorias?"""
    filas = [f for f in tabla if sum(f) > 0]
    total = sum(sum(f) for f in filas)
    tot_col = [sum(f[j] for f in filas) for j in range(len(filas[0]))]
    if total == 0 or 0 in tot_col or len(filas) < 2:
        return None, None, None
    chi2 = 0.0
    for f in filas:
        tf = sum(f)
        for j, obs in enumerate(f):
            esp = tf * tot_col[j] / total
            chi2 += (obs - esp) ** 2 / esp
    gl = (len(filas) - 1) * (len(tot_col) - 1)
    try:
        from scipy.stats import chi2 as dist_chi2
        p = float(dist_chi2.sf(chi2, gl))
    except ImportError:
        p = None
    return chi2, gl, p


def calcular_elo(filas, k=16, base=1500):
    """Elo secuencial en el orden en que se jugaron las partidas."""
    elo = {}
    for f in filas:
        a, b = f["agente_a"], f["agente_b"]
        ra, rb = elo.setdefault(a, base), elo.setdefault(b, base)
        esperado_a = 1 / (1 + 10 ** ((rb - ra) / 400))
        resultado_a = 1.0 if f["ganador"] == a else 0.0 if f["ganador"] == b else 0.5
        elo[a] = ra + k * (resultado_a - esperado_a)
        elo[b] = rb - k * (resultado_a - esperado_a)
    return elo


def resumen(filas, specs):
    print("\n" + "=" * 78)
    print("TABLA DEL TORNEO")
    print("=" * 78)
    elo = calcular_elo(filas)
    stats = {s: {"V": 0, "D": 0, "E": 0, "dif": [], "t": [], "nodos": []} for s in specs}
    for f in filas:
        for yo, otro, signo, lado in ((f["agente_a"], f["agente_b"], 1, "a"),
                                      (f["agente_b"], f["agente_a"], -1, "b")):
            s = stats[yo]
            if f["ganador"] == yo:
                s["V"] += 1
            elif f["ganador"] == otro:
                s["D"] += 1
            else:
                s["E"] += 1
            s["dif"].append(signo * f["diferencia_fichas"])
            s["t"].append(f[f"tiempo_{lado}"])
            s["nodos"].append(f[f"nodos_{lado}"])

    print(f"{'Agente':<10}{'V':>5}{'D':>5}{'E':>5}{'%Vict':>8}{'IC95% Wilson':>18}"
          f"{'DifProm':>9}{'t/jug(s)':>10}{'Elo':>7}")
    for s in sorted(specs, key=lambda x: -elo.get(x, 0)):
        d = stats[s]
        n = d["V"] + d["D"] + d["E"]
        lo, hi = intervalo_wilson(d["V"], n)
        print(f"{s:<10}{d['V']:>5}{d['D']:>5}{d['E']:>5}{100 * d['V'] / n:>7.1f}%"
              f"{f'[{100 * lo:.1f}, {100 * hi:.1f}]':>18}{_promedio(d['dif']):>9.2f}"
              f"{_promedio(d['t']):>10.4f}{elo.get(s, 1500):>7.0f}")

    print("\nCOMPARACIONES POR PAREJA (test binomial bilateral, sin contar empates)")
    print("-" * 78)
    for a, b in combinations(specs, 2):
        partidas = [f for f in filas if {f["agente_a"], f["agente_b"]} == {a, b}]
        va = sum(1 for f in partidas if f["ganador"] == a)
        vb = sum(1 for f in partidas if f["ganador"] == b)
        e = len(partidas) - va - vb
        n = va + vb
        p = test_binomial(va, n)
        lo, hi = intervalo_wilson(va, n)
        concl = "significativo (p<0.05)" if p < 0.05 else "NO significativo"
        print(f"{a} vs {b}: {va}-{vb} (empates {e}) | %vict {a} = "
              f"{100 * va / n if n else 0:.1f}% IC95% [{100 * lo:.1f}, {100 * hi:.1f}] | "
              f"p = {p:.4g} -> {concl}")

    tabla = [[stats[s]["V"], stats[s]["D"]] for s in specs]
    chi2, gl, p = test_chi_cuadrado(tabla)
    if chi2 is not None:
        p_txt = f"{p:.4g}" if p is not None else "(instala scipy para el p-valor)"
        print(f"\nChi-cuadrado de homogeneidad (victorias/derrotas por agente): "
              f"chi2 = {chi2:.3f}, gl = {gl}, p = {p_txt}")


# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Torneo round-robin de agentes Othello")
    ap.add_argument("--agentes", nargs="+", default=["V0:4", "V1:4", "V2:4"])
    ap.add_argument("--aperturas", type=int, default=50,
                    help="aperturas distintas; cada una se juega 2 veces (se cambian colores)")
    ap.add_argument("--plies", type=int, default=6, help="jugadas al azar de cada apertura")
    ap.add_argument("--semilla", type=int, default=2026)
    ap.add_argument("--tiempo", type=float, default=None, help="segundos por jugada (opcional)")
    ap.add_argument("--salida", default="resultados_othello.csv")
    args = ap.parse_args()

    aperturas = generar_aperturas(args.aperturas, args.plies, args.semilla)
    parejas = list(combinations(args.agentes, 2))
    total = len(parejas) * len(aperturas) * 2
    print(f"Agentes: {args.agentes} | aperturas: {len(aperturas)} ({args.plies} jugadas al azar, "
          f"semilla {args.semilla}) | partidas: {total}")

    filas, jugadas = [], 0
    for a, b in parejas:
        for i, apertura in enumerate(aperturas):
            for a_es_negro in (True, False):
                fila = jugar_partida(a, b, apertura, a_es_negro, args.tiempo)
                fila["apertura"], fila["semilla"] = i, args.semilla
                filas.append(fila)
                jugadas += 1
                if jugadas % 20 == 0 or jugadas == total:
                    print(f"  {jugadas}/{total} partidas jugadas")

    with open(args.salida, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNAS)
        w.writeheader()
        w.writerows(filas)
    print(f"\nResultados guardados en {args.salida}")
    resumen(filas, args.agentes)


if __name__ == "__main__":
    main()