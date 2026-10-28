# torneo_cacho.py
# Desarrollado con asistencia de IA generativa (Claude, Anthropic, 2026). Ver README.md.
# Torneo IA vs IA del Cacho + metricas de eficiencia + analisis de decisiones.
#
# Uso:
#   python torneo_cacho.py torneo --agentes base mejorada --semillas 100
#       cada semilla se juega 2 veces cambiando quien empieza -> 200 partidas
#       guarda resultados_cacho.csv y muestra la estadistica
#   python torneo_cacho.py eficiencia --estados 200
#       tiempo y evaluaciones por decision con / sin poda y memoizacion
#   python torneo_cacho.py decisiones --estados 300
#       en que situaciones la IA mejorada decide distinto que la base
#
# Agentes disponibles (ver AGENTES): base, mejorada, sin_varianza,
# varianza_alta, sin_adaptativa, w2_06, w2_08, w2_12.
#
# Columnas del CSV (seccion 22 de la practica): agente_a, agente_b, puntaje_a,
# puntaje_b, version_funcion (funcion que usa agente_b), tiempo_decision_promedio
# (de agente_b); y ademas, para el analisis: semilla, empieza, tiempos,
# evaluaciones y decisiones de cada agente.

import argparse
import contextlib
import csv
import io
import math
import random
import time
from itertools import combinations

from AgenteIA.AgenteJugador import ElEstado
from AgenteCacho import puntuar
from AgenteCachoIA import AgenteCachoIA
from EntornoCacho import EntornoCacho
from agente_ia import AgenteCachoIAMejorada


# ----------------------------------------------------------------------
# Agentes
# ----------------------------------------------------------------------
class AgenteBaseMedido(AgenteCachoIA):
    """La IA del docente sin ningun cambio; solo cuenta cuantas veces evalua."""

    def __init__(self, nombre="base"):
        AgenteCachoIA.__init__(self, nombre=nombre, altura=1)
        self._n_eval = 0

    def funcion_evaluacion(self, estado):
        self._n_eval += 1
        return AgenteCachoIA.funcion_evaluacion(self, estado)


ADAPTATIVA = True   # con --sin-adaptativa todas las versiones mejoradas buscan solo a altura 1

AGENTES = {
    "base":           lambda: AgenteBaseMedido(),
    "mejorada":       lambda: AgenteCachoIAMejorada(nombre="mejorada",
                                                    profundidad_adaptativa=ADAPTATIVA),
    "sin_varianza":   lambda: AgenteCachoIAMejorada(nombre="sin_varianza",
                                                    profundidad_adaptativa=ADAPTATIVA,
                                                    w3_por_etapa={"inicio": 0, "medio": 0, "final": 0}),
    "varianza_alta":  lambda: AgenteCachoIAMejorada(nombre="varianza_alta",
                                                    profundidad_adaptativa=ADAPTATIVA,
                                                    w3_por_etapa={"inicio": 0, "medio": 0.3, "final": 0.6}),
    "sin_adaptativa": lambda: AgenteCachoIAMejorada(nombre="sin_adaptativa",
                                                    profundidad_adaptativa=False),
    # w2 = peso del futuro esperado; 0.6 es el alpha de la funcion base
    "w2_06":          lambda: AgenteCachoIAMejorada(nombre="w2_06", w2=0.6,
                                                    profundidad_adaptativa=ADAPTATIVA),
    "w2_08":          lambda: AgenteCachoIAMejorada(nombre="w2_08", w2=0.8,
                                                    profundidad_adaptativa=ADAPTATIVA),
    "w2_12":          lambda: AgenteCachoIAMejorada(nombre="w2_12", w2=1.2,
                                                    profundidad_adaptativa=ADAPTATIVA),
}

VERSION_FUNCION = {"base": "base", "mejorada": "mejorada", "sin_varianza": "mejorada_w3_0",
                   "varianza_alta": "mejorada_w3_alto", "sin_adaptativa": "mejorada_sin_adaptativa",
                   "w2_06": "mejorada_w2_0.6", "w2_08": "mejorada_w2_0.8", "w2_12": "mejorada_w2_1.2"}


# ----------------------------------------------------------------------
# Entorno IA vs IA
# ----------------------------------------------------------------------
def copiar_estado(estado):
    t = estado.tablero
    tablero = {'dados': t['dados'], 'tiradas_restantes': t['tiradas_restantes'],
               'puntajes': list(t['puntajes']), 'usadas': [set(t['usadas'][0]), set(t['usadas'][1])],
               'ronda': t['ronda']}
    return ElEstado(jugador=estado.jugador, get_utilidad=0, tablero=tablero, movidas=None)


class EntornoTorneo(EntornoCacho):
    """El entorno del docente, pero los dos jugadores son IAs. Mide el tiempo de cada decision."""

    def __init__(self, guardar_estados=False):
        EntornoCacho.__init__(self)
        self.tiempos = {0: [], 1: []}
        self.evaluaciones = {0: [], 1: []}
        self.guardar_estados = guardar_estados
        self.estados_vistos = []
        self._pasos = 0

    def evolucionar(self):
        if self.finalizar():
            return
        self._pasos += 1
        if self._pasos > 500:   # una partida tiene a lo sumo 10 * 4 = 40 decisiones
            raise RuntimeError("la partida no avanza (accion invalida repetida)")
        turno = self.juegoActual.jugador
        agente = self.get_agentes()[turno]
        self.get_percepciones(agente)
        if self.guardar_estados:
            self.estados_vistos.append(copiar_estado(self.juegoActual))
        agente._n_eval = 0
        inicio = time.perf_counter()
        agente.programa()
        self.tiempos[turno].append(time.perf_counter() - inicio)
        self.evaluaciones[turno].append(agente._n_eval)
        self.ejecutar(agente)


def _promedio(xs):
    return sum(xs) / len(xs) if xs else 0.0


def jugar_partida(nombre_a, nombre_b, semilla, a_empieza):
    """Una partida entre dos agentes. a_empieza=True -> agente_a es el jugador 0."""
    random.seed(semilla)
    a, b = AGENTES[nombre_a](), AGENTES[nombre_b]()
    with contextlib.redirect_stdout(io.StringIO()):
        entorno = EntornoTorneo()
        if a_empieza:
            entorno.insertar(a)
            entorno.insertar(b)
        else:
            entorno.insertar(b)
            entorno.insertar(a)
        entorno.run()
    puntajes = entorno.juegoActual.tablero['puntajes']
    ia, ib = (0, 1) if a_empieza else (1, 0)
    return {
        "agente_a": nombre_a, "agente_b": nombre_b,
        "puntaje_a": puntajes[ia], "puntaje_b": puntajes[ib],
        "version_funcion": VERSION_FUNCION[nombre_b],
        "tiempo_decision_promedio": round(_promedio(entorno.tiempos[ib]), 5),
        "semilla": semilla, "empieza": nombre_a if a_empieza else nombre_b,
        "tiempo_decision_a": round(_promedio(entorno.tiempos[ia]), 5),
        "tiempo_decision_b": round(_promedio(entorno.tiempos[ib]), 5),
        "evaluaciones_a": round(_promedio(entorno.evaluaciones[ia]), 1),
        "evaluaciones_b": round(_promedio(entorno.evaluaciones[ib]), 1),
        "decisiones_a": len(entorno.tiempos[ia]), "decisiones_b": len(entorno.tiempos[ib]),
    }


COLUMNAS = ["agente_a", "agente_b", "puntaje_a", "puntaje_b", "version_funcion",
            "tiempo_decision_promedio", "semilla", "empieza", "tiempo_decision_a",
            "tiempo_decision_b", "evaluaciones_a", "evaluaciones_b", "decisiones_a", "decisiones_b"]


# ----------------------------------------------------------------------
# Estadistica (sin librerias externas)
# ----------------------------------------------------------------------
def test_binomial(k, n, p=0.5):
    """p-valor exacto bilateral de H0: proporcion de victorias = p."""
    if n == 0:
        return 1.0
    # se calcula con logaritmos: con miles de partidas math.comb(n, i) es un entero
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


def bootstrap_media(datos, repeticiones=5000, semilla=0):
    """Intervalo de confianza 95 % de la media por bootstrap (percentiles)."""
    rng = random.Random(semilla)
    n = len(datos)
    medias = sorted(sum(rng.choice(datos) for _ in range(n)) / n for _ in range(repeticiones))
    return medias[int(0.025 * repeticiones)], medias[int(0.975 * repeticiones) - 1]


def chi2_cola(x, gl):
    """P(Chi2(gl) >= x), con la serie de la gamma incompleta regularizada."""
    if x <= 0:
        return 1.0
    s, z = gl / 2.0, x / 2.0
    if z > s + 300:          # cola muy chica (< 1e-100): la serie se desbordaria
        return 0.0
    termino = suma = 1.0 / s
    for n in range(1, 2000):
        termino *= z / (s + n)
        suma += termino
        if termino < suma * 1e-15:
            break
    inferior = math.exp(-z + s * math.log(z) - math.lgamma(s)) * suma
    return max(0.0, 1.0 - inferior)


def test_chi_cuadrado(tabla):
    """Chi-cuadrado de homogeneidad: ¿todos los agentes ganan en la misma proporcion?"""
    total = sum(sum(f) for f in tabla)
    tot_col = [sum(f[j] for f in tabla) for j in range(len(tabla[0]))]
    if total == 0 or 0 in tot_col or len(tabla) < 2:
        return None, None, None
    chi2 = 0.0
    for f in tabla:
        tf = sum(f)
        for j, obs in enumerate(f):
            esp = tf * tot_col[j] / total
            chi2 += (obs - esp) ** 2 / esp
    gl = (len(tabla) - 1) * (len(tot_col) - 1)
    return chi2, gl, chi2_cola(chi2, gl)


def formato_p(p):
    return "< 1e-15" if p == 0 else f"{p:.4g}"


def resumen(filas, nombres):
    print("\n" + "=" * 86)
    print("TABLA DEL TORNEO")
    print("=" * 86)
    stats = {s: {"V": 0, "D": 0, "E": 0, "pts": [], "t": [], "ev": []} for s in nombres}
    for f in filas:
        for yo, otro, lado in ((f["agente_a"], f["agente_b"], "a"), (f["agente_b"], f["agente_a"], "b")):
            mio = f[f"puntaje_{lado}"]
            suyo = f["puntaje_b"] if lado == "a" else f["puntaje_a"]
            s = stats[yo]
            s["V" if mio > suyo else "D" if mio < suyo else "E"] += 1
            s["pts"].append(mio)
            s["t"].append(f[f"tiempo_decision_{lado}"])
            s["ev"].append(f[f"evaluaciones_{lado}"])
    print(f"{'Agente':<16}{'V':>5}{'D':>5}{'E':>5}{'%Vict':>8}{'IC95% Wilson':>17}"
          f"{'Pts prom':>10}{'t/decision':>12}{'eval/dec':>10}")
    for s in nombres:
        d = stats[s]
        n = d["V"] + d["D"] + d["E"]
        lo, hi = intervalo_wilson(d["V"], n)
        print(f"{s:<16}{d['V']:>5}{d['D']:>5}{d['E']:>5}{100 * d['V'] / n:>7.1f}%"
              f"{f'[{100 * lo:.1f}, {100 * hi:.1f}]':>17}{_promedio(d['pts']):>10.2f}"
              f"{_promedio(d['t']):>11.4f}s{_promedio(d['ev']):>10.0f}")

    print("\nCOMPARACIONES POR PAREJA")
    print("-" * 86)
    for a, b in combinations(nombres, 2):
        partidas = [f for f in filas if {f["agente_a"], f["agente_b"]} == {a, b}]
        dif = [(f["puntaje_a"] - f["puntaje_b"]) if f["agente_a"] == a else (f["puntaje_b"] - f["puntaje_a"])
               for f in partidas]
        va = sum(1 for d in dif if d > 0)
        vb = sum(1 for d in dif if d < 0)
        e = len(dif) - va - vb
        n = va + vb
        p = test_binomial(va, n)
        lo, hi = intervalo_wilson(va, n)
        blo, bhi = bootstrap_media(dif)
        print(f"{a} vs {b}: {len(partidas)} partidas | victorias {va}-{vb} (empates {e})")
        print(f"   % victorias de {a} (sin empates) = {100 * va / n if n else 0:.1f}%  "
              f"IC95% Wilson [{100 * lo:.1f}, {100 * hi:.1f}]")
        print(f"   test binomial H0 p=0.5: p-valor = {formato_p(p)} -> "
              f"{'diferencia significativa (p<0.05)' if p < 0.05 else 'NO significativa'}")
        print(f"   diferencia de puntaje promedio ({a} - {b}) = {_promedio(dif):.2f}  "
              f"IC95% bootstrap [{blo:.2f}, {bhi:.2f}]")
        for quien in (a, b):
            sub = [d for d, f in zip(dif, partidas) if f["empieza"] == quien]
            if sub:
                print(f"   cuando empieza {quien}: diferencia promedio = {_promedio(sub):.2f} "
                      f"({len(sub)} partidas)")

    if len(nombres) > 2:
        tabla = [[stats[s]["V"], stats[s]["D"] + stats[s]["E"]] for s in nombres]
        chi2, gl, p = test_chi_cuadrado(tabla)
        if chi2 is not None:
            print(f"\nChi-cuadrado de homogeneidad (victorias vs no victorias por agente): "
                  f"chi2 = {chi2:.3f}, gl = {gl}, p = {formato_p(p)}")


def modo_torneo(args):
    global ADAPTATIVA
    ADAPTATIVA = not args.sin_adaptativa
    nombres = args.agentes
    parejas = list(combinations(nombres, 2))
    total = len(parejas) * args.semillas * 2
    print(f"Agentes: {nombres} | semillas {args.semilla_inicial}..{args.semilla_inicial + args.semillas - 1}"
          f" (cada una 2 veces, cambiando quien empieza) | partidas: {total}")
    filas = []
    inicio = time.time()
    for a, b in parejas:
        for s in range(args.semilla_inicial, args.semilla_inicial + args.semillas):
            for a_empieza in (True, False):
                filas.append(jugar_partida(a, b, s, a_empieza))
                if len(filas) % 20 == 0 or len(filas) == total:
                    print(f"  {len(filas)}/{total} partidas ({time.time() - inicio:.0f}s)")
    with open(args.salida, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNAS)
        w.writeheader()
        w.writerows(filas)
    print(f"\nResultados guardados en {args.salida}")
    resumen(filas, nombres)


def modo_analizar(args):
    filas = []
    for ruta in args.csv:
        with open(ruta, encoding="utf-8") as fh:
            for f in csv.DictReader(fh):
                for k in ("puntaje_a", "puntaje_b", "semilla", "decisiones_a", "decisiones_b"):
                    f[k] = int(f[k])
                for k in ("tiempo_decision_promedio", "tiempo_decision_a", "tiempo_decision_b",
                          "evaluaciones_a", "evaluaciones_b"):
                    f[k] = float(f[k])
                filas.append(f)
    nombres = []
    for f in filas:
        for n in (f["agente_a"], f["agente_b"]):
            if n not in nombres:
                nombres.append(n)
    print(f"{len(filas)} partidas leidas de {len(args.csv)} archivo(s)")
    resumen(filas, nombres)


# ----------------------------------------------------------------------
# Estados de muestra (para eficiencia y decisiones)
# ----------------------------------------------------------------------
def estados_de_muestra(cantidad, semilla, solo_jugador0=False, con_tiradas=True):
    """Estados reales de decision, sacados de partidas mejorada vs mejorada."""
    estados = []
    s = semilla
    while len(estados) < cantidad:
        random.seed(s)
        with contextlib.redirect_stdout(io.StringIO()):
            entorno = EntornoTorneo(guardar_estados=True)
            entorno.insertar(AgenteCachoIAMejorada())
            entorno.insertar(AgenteCachoIAMejorada())
            entorno.run()
        for e in entorno.estados_vistos:
            if solo_jugador0 and e.jugador != 0:
                continue
            if con_tiradas and e.tablero['tiradas_restantes'] == 0:
                continue
            estados.append(e)
        s += 1
    rng = random.Random(semilla)
    rng.shuffle(estados)
    return estados[:cantidad]


def decidir(agente, estado):
    agente.estado = estado
    agente._n_eval = 0
    agente._n_calc = 0
    inicio = time.perf_counter()
    accion = agente.elegir_accion(estado)
    return accion, time.perf_counter() - inicio, agente._n_eval, getattr(agente, "_n_calc", agente._n_eval)


def modo_eficiencia(args):
    estados = estados_de_muestra(args.estados, args.semilla_inicial)
    print(f"{len(estados)} estados de decision reales (con tiradas disponibles)\n")
    configuraciones = [
        ("sin poda, sin memo", dict(usar_poda=False, usar_memo=False)),
        ("con poda, sin memo", dict(usar_poda=True, usar_memo=False)),
        ("sin poda, con memo", dict(usar_poda=False, usar_memo=True)),
        ("con poda, con memo", dict(usar_poda=True, usar_memo=True)),
    ]
    filas = []
    print(f"{'altura':<8}{'configuracion':<22}{'t prom (s)':>12}{'t max (s)':>11}"
          f"{'evaluaciones':>14}{'calculos':>10}{'misma accion':>14}")
    for altura, cuantos in ((1, len(estados)), (2, min(args.estados_prof2, len(estados)))):
        if cuantos == 0:
            continue
        referencia = None
        resultados = {}
        for nombre, kw in configuraciones:
            if altura == 2 and nombre == "sin poda, sin memo" and not args.incluir_lento:
                continue
            acciones, ts, evs, cals = [], [], [], []
            for e in estados[:cuantos]:
                ag = AgenteCachoIAMejorada(altura=altura, profundidad_adaptativa=False, **kw)
                acc, t, ev, cal = decidir(ag, e)
                acciones.append(acc)
                ts.append(t)
                evs.append(ev)
                cals.append(cal)
            resultados[nombre] = (acciones, ts, evs, cals)
        referencia = resultados.get("sin poda, con memo")[0]   # memo no cambia nada: es exacta
        for nombre, (acciones, ts, evs, cals) in resultados.items():
            iguales = sum(1 for x, y in zip(acciones, referencia) if x == y)
            filas.append({"altura": altura, "configuracion": nombre, "estados": cuantos,
                          "tiempo_promedio": _promedio(ts), "tiempo_max": max(ts),
                          "evaluaciones_promedio": _promedio(evs), "calculos_promedio": _promedio(cals),
                          "misma_accion_pct": 100 * iguales / cuantos})
            print(f"{altura:<8}{nombre:<22}{_promedio(ts):>12.4f}{max(ts):>11.3f}"
                  f"{_promedio(evs):>14.0f}{_promedio(cals):>10.0f}{100 * iguales / cuantos:>13.1f}%")

    # el agente completo (con profundidad adaptativa), como juega de verdad
    ts, evs, prof = [], [], []
    for e in estados:
        ag = AgenteCachoIAMejorada()
        _, t, ev, _ = decidir(ag, e)
        ts.append(t)
        evs.append(ev)
        prof.append(ag.profundidades[-1])
    print(f"\nAgente completo (profundidad adaptativa): t prom {_promedio(ts):.4f}s, t max {max(ts):.3f}s, "
          f"{_promedio(evs):.0f} evaluaciones, profundidad 2 en {100 * prof.count(2) / len(prof):.1f}% "
          f"de las decisiones")
    filas.append({"altura": "adaptativa", "configuracion": "completo", "estados": len(estados),
                  "tiempo_promedio": _promedio(ts), "tiempo_max": max(ts),
                  "evaluaciones_promedio": _promedio(evs), "calculos_promedio": "",
                  "misma_accion_pct": ""})
    with open(args.salida, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    print(f"\nGuardado en {args.salida}")


def texto_accion(estado, accion):
    d = estado.tablero['dados']
    if accion[0] == 'tirar':
        return f"tirar, guarda {[d[i] for i in range(5) if i not in accion[1]]}"
    return f"anotar '{accion[1]}' (+{puntuar(accion[1], d)})"


def modo_decisiones(args):
    # la IA base esta escrita para ser el jugador 0, asi que se comparan estados del jugador 0
    estados = estados_de_muestra(args.estados, args.semilla_inicial, solo_jugador0=True, con_tiradas=False)
    filas = []
    for e in estados:
        acc_base, _, _, _ = decidir(AgenteBaseMedido(), copiar_estado(e))
        acc_mej, _, _, _ = decidir(AgenteCachoIAMejorada(), copiar_estado(e))
        t = e.tablero
        filas.append({"dados": t['dados'], "tiradas_restantes": t['tiradas_restantes'], "ronda": t['ronda'],
                      "libres": sorted(set(['1', '2', '3', '4', '5', '6', 'escalera', 'full', 'poker',
                                            'grande']) - t['usadas'][0]),
                      "accion_base": texto_accion(e, acc_base), "accion_mejorada": texto_accion(e, acc_mej),
                      "distinta": acc_base != acc_mej,
                      "tipo": (f"{acc_base[0]}/{acc_mej[0]}")})
    distintas = [f for f in filas if f["distinta"]]
    print(f"{len(filas)} estados del jugador 0 | decisiones distintas: {len(distintas)} "
          f"({100 * len(distintas) / len(filas):.1f}%)\n")
    print("Tipo de desacuerdo (base/mejorada):")
    tipos = {}
    for f in distintas:
        tipos[f["tipo"]] = tipos.get(f["tipo"], 0) + 1
    for tipo, n in sorted(tipos.items(), key=lambda x: -x[1]):
        print(f"   {tipo:<16} {n:>4}  ({100 * n / len(distintas):.1f}%)")
    print("\nEjemplos:")
    for f in distintas[:args.ejemplos]:
        print(f"   dados {f['dados']}, tiradas {f['tiradas_restantes']}, ronda {f['ronda']}")
        print(f"      base:     {f['accion_base']}")
        print(f"      mejorada: {f['accion_mejorada']}")
    with open(args.salida, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    print(f"\nGuardado en {args.salida}")


# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Torneo y metricas del Cacho")
    sub = ap.add_subparsers(dest="modo", required=True)

    t = sub.add_parser("torneo")
    t.add_argument("--agentes", nargs="+", default=["base", "mejorada"], choices=list(AGENTES))
    t.add_argument("--semillas", type=int, default=100)
    t.add_argument("--semilla-inicial", type=int, default=2026)
    t.add_argument("--salida", default="resultados_cacho.csv")
    t.add_argument("--sin-adaptativa", action="store_true",
                   help="versiones mejoradas solo a altura 1 (mas rapido, para ajustar pesos)")

    e = sub.add_parser("eficiencia")
    e.add_argument("--estados", type=int, default=200)
    e.add_argument("--estados-prof2", type=int, default=20)
    e.add_argument("--incluir-lento", action="store_true",
                   help="incluye altura 2 sin poda ni memo (cerca de 100 s por decision)")
    e.add_argument("--semilla-inicial", type=int, default=2026)
    e.add_argument("--salida", default="eficiencia_cacho.csv")

    d = sub.add_parser("decisiones")
    d.add_argument("--estados", type=int, default=300)
    d.add_argument("--ejemplos", type=int, default=8)
    d.add_argument("--semilla-inicial", type=int, default=2026)
    d.add_argument("--salida", default="decisiones_cacho.csv")

    a = sub.add_parser("analizar", help="recalcula la estadistica a partir de uno o mas CSV del torneo")
    a.add_argument("csv", nargs="+")

    args = ap.parse_args()
    {"torneo": modo_torneo, "eficiencia": modo_eficiencia, "decisiones": modo_decisiones,
     "analizar": modo_analizar}[args.modo](args)


if __name__ == "__main__":
    main()
