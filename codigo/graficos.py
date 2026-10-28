# graficos.py
# Desarrollado con asistencia de IA generativa (Claude, Anthropic, 2026). Ver README.md.
# Genera todas las figuras del articulo a partir de los CSV de ../datos/
# y las guarda en ../articulo/figuras/. Si falta un CSV, esa figura se salta.
#
#   python graficos.py

import csv
import math
import os
import random

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, LogLocator

AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(AQUI, "..", "datos")
FIGURAS = os.path.join(AQUI, "..", "articulo", "figuras")

AZUL = "#2a78d6"       # serie 1
NARANJA = "#eb6834"    # serie 2
GRIS = "#8a8a85"       # referencias (lineas de ajuste, 50 %)
TINTA = "#2b2b29"

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": "#bdbdb6", "axes.labelcolor": TINTA,
    "xtick.color": TINTA, "ytick.color": TINTA, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e6e1",
    "grid.linewidth": 0.8, "axes.axisbelow": True, "legend.frameon": False,
})


def ejes_log_legibles(ax, eje="y"):
    """En escala log, pone numeros comunes (0.01, 0.02, 0.05...) en vez de potencias de 10."""
    loc = LogLocator(base=10, subs=(1.0, 2.0, 5.0))
    fmt = FuncFormatter(lambda v, _: f"{v:g}")
    eje_obj = ax.yaxis if eje == "y" else ax.xaxis
    eje_obj.set_major_locator(loc)
    eje_obj.set_major_formatter(fmt)
    eje_obj.set_minor_formatter(FuncFormatter(lambda v, _: ""))


def leer(nombre):
    ruta = os.path.join(DATOS, nombre)
    if not os.path.exists(ruta):
        print(f"  (no esta {nombre}, se salta)")
        return None
    with open(ruta, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def guardar(fig, nombre):
    os.makedirs(FIGURAS, exist_ok=True)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURAS, nombre), dpi=200)
    plt.close(fig)
    print(f"  -> figuras/{nombre}")


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 1.0
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - m), min(1.0, c + m)


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    return cov / math.sqrt(vx * vy) if vx > 0 and vy > 0 else 0.0


def spearman(xs, ys):
    def rangos(v):
        orden = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(orden):
            j = i
            while j + 1 < len(orden) and v[orden[j + 1]] == v[orden[i]]:
                j += 1
            for k in range(i, j + 1):
                r[orden[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    return pearson(rangos(xs), rangos(ys))


def bootstrap_media(datos, rep=3000, semilla=0):
    rng = random.Random(semilla)
    n = len(datos)
    medias = sorted(sum(rng.choice(datos) for _ in range(n)) / n for _ in range(rep))
    return medias[int(0.025 * rep)], medias[int(0.975 * rep) - 1]


# ----------------------------------------------------------------------
# Othello
# ----------------------------------------------------------------------
def othello_torneo():
    filas = leer("resultados_othello.csv")
    if not filas:
        return
    agentes = []
    for f in filas:
        for a in (f["agente_a"], f["agente_b"]):
            if a not in agentes:
                agentes.append(a)
    pct, err_lo, err_hi = [], [], []
    for a in agentes:
        mias = [f for f in filas if a in (f["agente_a"], f["agente_b"])]
        v = sum(1 for f in mias if f["ganador"] == a)
        lo, hi = wilson(v, len(mias))
        p = v / len(mias)
        pct.append(100 * p)
        err_lo.append(100 * (p - lo))
        err_hi.append(100 * (hi - p))
    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    ax.bar(agentes, pct, color=AZUL, width=0.55)
    ax.errorbar(agentes, pct, yerr=[err_lo, err_hi], fmt="none", ecolor=TINTA, capsize=4, lw=1)
    for i, v in enumerate(pct):
        ax.text(i, v + err_hi[i] + 1.5, f"{v:.1f}%", ha="center", color=TINTA)
    ax.axhline(50, color=GRIS, ls="--", lw=1)
    ax.set_ylabel("% de victorias (IC 95 % Wilson)")
    ax.set_ylim(0, 100)
    ax.set_title("Othello: torneo round-robin")
    guardar(fig, "othello_torneo.png")


def othello_escalabilidad():
    filas = leer("datos_escalabilidad.csv")
    if not filas:
        return
    alturas = sorted({int(f["altura"]) for f in filas})
    prom = [sum(float(f["tiempo"]) for f in filas if int(f["altura"]) == h)
            / sum(1 for f in filas if int(f["altura"]) == h) for h in alturas]
    lx, ly = [math.log(h) for h in alturas], [math.log(t) for t in prom]
    mx, my = sum(lx) / len(lx), sum(ly) / len(ly)
    k = sum((x - mx) * (y - my) for x, y in zip(lx, ly)) / sum((x - mx) ** 2 for x in lx)
    c = math.exp(my - k * mx)
    pred = [k * x + math.log(c) for x in lx]
    r2 = 1 - sum((y - p) ** 2 for y, p in zip(ly, pred)) / sum((y - my) ** 2 for y in ly)
    fig, ax = plt.subplots(figsize=(5.5, 3.8))
    xs = [alturas[0] * 0.92, alturas[-1] * 1.08]
    ax.loglog(xs, [c * x ** k for x in xs], ls="--", color=GRIS, lw=1.2,
              label=f"ajuste: t ∝ altura^{k:.2f} (R² = {r2:.3f})")
    ax.loglog(alturas, prom, "o-", color=AZUL, lw=2, ms=8, label="medido")
    for h, t in zip(alturas, prom):
        ax.annotate(f"{t:.3g} s", (h, t), textcoords="offset points", xytext=(-8, 8),
                    ha="right", fontsize=8.5, color=TINTA)
    ax.set_ylim(min(prom) * 0.6, max(prom) * 2.5)
    ejes_log_legibles(ax, "y")
    ax.set_xticks(alturas)
    ax.set_xticklabels([str(h) for h in alturas])
    ax.minorticks_off()
    ax.set_xlabel("altura (profundidad de búsqueda)")
    ax.set_ylabel("tiempo promedio por jugada (s)")
    ax.set_title("Othello: tiempo vs. profundidad (log-log)")
    ax.legend()
    guardar(fig, "othello_escalabilidad.png")
    print(f"     ajuste: t = {c:.3g} * altura^{k:.2f}, R^2 = {r2:.3f}")


def othello_correlacion():
    filas = leer("datos_correlacion.csv")
    if not filas:
        return
    mvs = sorted({int(f["mv"]) for f in filas})
    rp, rs = [], []
    for mv in mvs:
        xs = [float(f["valor_funcion"]) for f in filas if int(f["mv"]) == mv]
        ys = [float(f["diferencia_final"]) for f in filas if int(f["mv"]) == mv]
        rp.append(pearson(xs, ys))
        rs.append(spearman(xs, ys))
    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    ancho = 0.36
    pos = list(range(len(mvs)))
    ax.bar([p - ancho / 2 - 0.01 for p in pos], rp, ancho, color=AZUL, label="Pearson")
    ax.bar([p + ancho / 2 + 0.01 for p in pos], rs, ancho, color=NARANJA, label="Spearman")
    for p, a, b in zip(pos, rp, rs):
        for x, v in ((p - ancho / 2, a), (p + ancho / 2, b)):
            ax.text(x, v + (0.015 if v >= 0 else -0.015), f"{v:.2f}", ha="center",
                    va="bottom" if v >= 0 else "top", fontsize=8.5, color=TINTA)
    ax.axhline(0, color="#bdbdb6", lw=0.8)
    ax.set_xticks(pos)
    ax.set_xticklabels([str(m) for m in mvs])
    ax.set_xlabel("fichas en el tablero al medir (mv)")
    ax.set_ylabel("correlación con la diferencia final")
    ax.set_ylim(min(0.0, min(rp + rs) - 0.08), max(0.1, max(rp + rs)) * 1.25)
    ax.set_title("Othello: función de evaluación vs. resultado final")
    ax.legend(loc="upper left")
    guardar(fig, "othello_correlacion.png")


def othello_profundidad():
    filas = leer("victorias_profundidad.csv")
    if not filas:
        return
    alturas = sorted({int(f["profundidad_a"]) for f in filas})
    pct, lo_e, hi_e, ts = [], [], [], []
    referencia = filas[0]["agente_b"]
    for h in alturas:
        sub = [f for f in filas if int(f["profundidad_a"]) == h]
        v = sum(1 for f in sub if f["ganador"] == f["agente_a"])
        lo, hi = wilson(v, len(sub))
        p = v / len(sub)
        pct.append(100 * p)
        lo_e.append(100 * (p - lo))
        hi_e.append(100 * (hi - p))
        ts.append(sum(float(f["tiempo_a"]) for f in sub) / len(sub))
    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    ax.errorbar(alturas, pct, yerr=[lo_e, hi_e], fmt="o-", color=AZUL, lw=2, ms=8,
                ecolor=AZUL, elinewidth=1, capsize=4)
    ax.axhline(50, color=GRIS, ls="--", lw=1)
    ax.set_xticks(alturas)
    ax.set_ylim(0, 100)
    ax.set_xlabel(f"altura del agente (rival fijo: {referencia})")
    ax.set_ylabel("% de victorias (IC 95 % Wilson)")
    ax.set_title("Othello: victorias vs. profundidad")
    guardar(fig, "othello_victorias_profundidad.png")

    fig, ax = plt.subplots(figsize=(5.5, 3.4))
    ax.semilogy(alturas, ts, "o-", color=AZUL, lw=2, ms=8)
    for h, t in zip(alturas, ts):
        ax.annotate(f"{t:.3g} s", (h, t), textcoords="offset points", xytext=(-8, 8),
                    ha="right", fontsize=8.5, color=TINTA)
    ax.set_ylim(min(ts) * 0.6, max(ts) * 2.5)
    ejes_log_legibles(ax, "y")
    ax.set_xticks(alturas)
    ax.set_xlabel("altura")
    ax.set_ylabel("tiempo promedio por jugada (s)")
    ax.set_title("Othello: tiempo por movimiento vs. profundidad")
    guardar(fig, "othello_tiempo_profundidad.png")


# ----------------------------------------------------------------------
# Cacho
# ----------------------------------------------------------------------
def puntajes_por_agente(filas):
    pts = {}
    for f in filas:
        pts.setdefault(f["agente_a"], []).append(int(f["puntaje_a"]))
        pts.setdefault(f["agente_b"], []).append(int(f["puntaje_b"]))
    return pts


def cacho_puntajes():
    filas = leer("resultados_cacho.csv")
    if not filas:
        return
    pts = puntajes_por_agente(filas)
    nombres = list(pts)
    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    caja = ax.boxplot([pts[n] for n in nombres], widths=0.45, patch_artist=True,
                      medianprops=dict(color=TINTA, lw=1.5))
    for parche, color in zip(caja["boxes"], [GRIS, AZUL, NARANJA]):
        parche.set_facecolor(color)
        parche.set_alpha(0.75)
    ax.set_xticks(range(1, len(nombres) + 1))
    ax.set_xticklabels([f"{n}\n(prom. {sum(pts[n]) / len(pts[n]):.1f})" for n in nombres])
    ax.set_ylabel("puntaje final por partida")
    ax.set_title(f"Cacho: puntajes ({len(filas)} partidas)")
    guardar(fig, "cacho_puntajes.png")


def cacho_ajuste(nombre_csv, nombre_png, titulo):
    filas = leer(nombre_csv)
    if not filas:
        return
    pts = puntajes_por_agente(filas)
    nombres = list(pts)
    medias = [sum(pts[n]) / len(pts[n]) for n in nombres]
    ics = [bootstrap_media(pts[n]) for n in nombres]
    fig, ax = plt.subplots(figsize=(5.5, 0.6 + 0.55 * len(nombres)))
    y = list(range(len(nombres)))
    ax.errorbar(medias, y, xerr=[[m - lo for m, (lo, hi) in zip(medias, ics)],
                                 [hi - m for m, (lo, hi) in zip(medias, ics)]],
                fmt="o", color=AZUL, ms=8, ecolor=AZUL, elinewidth=1.2, capsize=4)
    for m, yy in zip(medias, y):
        ax.text(m, yy + 0.22, f"{m:.1f}", ha="center", fontsize=8.5, color=TINTA)
    ax.set_yticks(y)
    ax.set_yticklabels(nombres)
    ax.set_ylim(-0.6, len(nombres) - 0.3)
    ax.set_xlabel("puntaje promedio por partida (IC 95 % bootstrap)")
    ax.set_title(titulo)
    guardar(fig, nombre_png)


def cacho_eficiencia():
    filas = leer("eficiencia_cacho.csv")
    if not filas:
        return
    alturas = [a for a in ("1", "2") if any(f["altura"] == a for f in filas)]
    fig, axs = plt.subplots(1, len(alturas), figsize=(5.2 * len(alturas), 3.4), squeeze=False)
    for ax, a in zip(axs[0], alturas):
        sub = [f for f in filas if f["altura"] == a]
        nombres = [f["configuracion"] for f in sub]
        tiempos = [float(f["tiempo_promedio"]) for f in sub]
        ax.barh(nombres, tiempos, color=AZUL, height=0.55)
        ax.set_xscale("log")
        for i, t in enumerate(tiempos):
            ax.text(t * 1.1, i, f"{t:.3g} s", va="center", fontsize=9, color=TINTA)
        ax.set_xlim(min(tiempos) * 0.5, max(tiempos) * 6)
        ejes_log_legibles(ax, "x")
        ax.invert_yaxis()
        ax.set_xlabel("tiempo promedio por decisión (s)")
        ax.set_title(f"altura {a}")
        ax.grid(axis="y", visible=False)
    fig.suptitle("Cacho: efecto de la poda y la memoización", fontsize=11)
    guardar(fig, "cacho_eficiencia.png")


if __name__ == "__main__":
    print("Othello:")
    othello_torneo()
    othello_escalabilidad()
    othello_correlacion()
    othello_profundidad()
    print("Cacho:")
    cacho_puntajes()
    cacho_ajuste("ajuste_w2.csv", "cacho_ajuste_w2.png", "Cacho: ajuste del peso w2")
    cacho_ajuste("ajuste_w3.csv", "cacho_ajuste_w3.png", "Cacho: ajuste del peso w3")
    cacho_ajuste("ajuste_adaptativa.csv", "cacho_ajuste_adaptativa.png",
                 "Cacho: profundidad adaptativa")
    cacho_eficiencia()
    print(f"\nFiguras en {os.path.normpath(FIGURAS)}")
