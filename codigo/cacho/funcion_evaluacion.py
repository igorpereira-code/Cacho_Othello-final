# funcion_evaluacion.py
# Desarrollado con asistencia de IA generativa (Claude, Anthropic, 2026). Ver README.md.
# Funcion de evaluacion mejorada para el Cacho.
#
#   E_nueva(s) = w1 * f1(s) + w2 * f2(s) + w3(etapa) * f3(s)
#
#   f1 = puntaje actual propio - puntaje actual del rival
#   f2 = puntos que cada uno espera sumar hasta el final (propio - rival)
#   f3 = termino de riesgo: -sigma * tanh(mu / sigma), con mu = f1 + f2 (diferencia
#        final esperada) y sigma = su desviacion estandar. Si voy ganando claro
#        conviene jugar seguro; si voy perdiendo claro conviene arriesgar.
#
# Rango de los pesos: w1 = 1 (fija la escala en puntos), w2 > 0, 0 <= w3 < 1.
# Con w3 < 1 la evaluacion siempre sube cuando sube mu (la derivada es
# 1 - w3 / cosh^2(mu/sigma) > 0): la IA nunca prefiere una diferencia esperada
# menor solo para cambiar el riesgo.
#
# Que limitacion de la funcion base corrige cada parte:
#   - Valores estaticos       -> f2 usa los dados actuales y las tiradas que quedan,
#                                con las probabilidades reales de los dados
#   - Interaccion entre       -> f2 solo cuenta los turnos que le quedan a cada uno y en
#     categorias                 cada uno usa la mejor categoria libre: gastar una
#                                categoria hoy cambia lo que se puede sumar despues
#   - Varianza                -> f3, con un peso distinto por etapa del juego
#   - alpha = 0.6 arbitrario  -> w2 se justifica (f2 esta en puntos, igual que f1) y
#                                los pesos se ajustan con experimentos (torneo)
#
# Las tablas se calculan una sola vez al importar el modulo (memoizacion):
# despues, evaluar un estado es buscar valores y ordenar a lo sumo 10 numeros.

from itertools import combinations_with_replacement
from collections import Counter
from math import factorial, sqrt, tanh

from AgenteCacho import CATEGORIAS, puntuar

RONDAS_TOTALES = 10      # el juego termina con 10 anotaciones en total (ver testTerminal)
TIRADAS_POR_TURNO = 3    # tiradas extra despues de la tirada inicial

ESTADOS = list(combinations_with_replacement(range(1, 7), 5))

# Pesos por defecto. w3 cambia segun la etapa (ver etapa()).
W1 = 1.0
W2 = 1.0
W3_POR_ETAPA = {"inicio": 0.0, "medio": 0.1, "final": 0.3}


# ------------------------------------------------------------
# Probabilidades reales de los dados
# ------------------------------------------------------------

def distribucion_tirada(n):
    """Probabilidad de cada resultado (ordenado) al tirar n dados."""
    dist = {}
    total = 6 ** n
    for combo in combinations_with_replacement(range(1, 7), n):
        formas = factorial(n)
        for v in Counter(combo).values():
            formas //= factorial(v)
        dist[combo] = formas / total
    return dist


DIST_TIRADA = [distribucion_tirada(n) for n in range(6)]


def resultados_de_guardar(guardados):
    """Distribucion de los 5 dados finales si se guardan esos dados y se tiran los demas."""
    dist = {}
    for tirados, p in DIST_TIRADA[5 - len(guardados)].items():
        final = tuple(sorted(guardados + tirados))
        dist[final] = dist.get(final, 0) + p
    return dist


def formas_de_guardar(dados):
    """Todos los grupos distintos de dados que se pueden guardar (sin repetir grupos iguales)."""
    grupos = set()
    for mascara in range(32):
        grupos.add(tuple(dados[i] for i in range(5) if mascara & (1 << i)))
    return list(grupos)


GUARDADOS_POSIBLES = set()
for _e in ESTADOS:
    GUARDADOS_POSIBLES.update(formas_de_guardar(_e))
DIST_GUARDADOS = {g: resultados_de_guardar(g) for g in GUARDADOS_POSIBLES}
GUARDAR_DESDE = {e: formas_de_guardar(e) for e in ESTADOS}


# ------------------------------------------------------------
# Tablas por categoria (r = tiradas que quedan, jugando para esa categoria):
#   VALOR[c][r][dados]      puntos esperados
#   VARIANZA[c][r][dados]   varianza de esos puntos
#   MEJOR_GUARDAR[c][r][dados]  que dados conviene guardar
# ------------------------------------------------------------

def calcular_tablas(categoria):
    media = [{e: puntuar(categoria, e) for e in ESTADOS}]
    momento2 = [{e: puntuar(categoria, e) ** 2 for e in ESTADOS}]
    guardar = [{}]
    for r in range(1, TIRADAS_POR_TURNO + 1):
        m_ant, m2_ant = media[-1], momento2[-1]
        media_g = {g: sum(p * m_ant[s] for s, p in d.items()) for g, d in DIST_GUARDADOS.items()}
        m2_g = {g: sum(p * m2_ant[s] for s, p in d.items()) for g, d in DIST_GUARDADOS.items()}
        nivel_m, nivel_m2, nivel_g = {}, {}, {}
        for e in ESTADOS:
            mejor = max(GUARDAR_DESDE[e], key=lambda g: media_g[g])
            nivel_m[e], nivel_m2[e], nivel_g[e] = media_g[mejor], m2_g[mejor], mejor
        media.append(nivel_m)
        momento2.append(nivel_m2)
        guardar.append(nivel_g)
    varianza = [{e: max(0.0, m2[e] - m[e] ** 2) for e in ESTADOS} for m, m2 in zip(media, momento2)]
    return media, varianza, guardar


VALOR, VARIANZA, MEJOR_GUARDAR = {}, {}, {}
for _c in CATEGORIAS:
    VALOR[_c], VARIANZA[_c], MEJOR_GUARDAR[_c] = calcular_tablas(_c)

# Un turno que recien empieza: tirada inicial al azar + 3 tiradas
VALOR_TURNO_NUEVO, VARIANZA_TURNO_NUEVO = {}, {}
for _c in CATEGORIAS:
    m = sum(p * VALOR[_c][TIRADAS_POR_TURNO][e] for e, p in DIST_TIRADA[5].items())
    m2 = sum(p * (VARIANZA[_c][TIRADAS_POR_TURNO][e] + VALOR[_c][TIRADAS_POR_TURNO][e] ** 2)
             for e, p in DIST_TIRADA[5].items())
    VALOR_TURNO_NUEVO[_c] = m
    VARIANZA_TURNO_NUEVO[_c] = max(0.0, m2 - m ** 2)


# ------------------------------------------------------------
# Piezas de la funcion
# ------------------------------------------------------------

def turnos_restantes(ronda, jugador):
    """Turnos que le quedan al jugador (contando el actual si esta jugando). Empieza el jugador 0."""
    return sum(1 for t in range(ronda, RONDAS_TOTALES) if t % 2 == jugador)


def etapa(ronda):
    if ronda < 4:
        return "inicio"
    if ronda < 7:
        return "medio"
    return "final"


def plan_futuro(libres, k):
    """Las k mejores categorias para los turnos que quedan: (media, varianza) del plan."""
    if k <= 0:
        return 0.0, 0.0
    elegidas = sorted(libres, key=lambda c: VALOR_TURNO_NUEVO[c], reverse=True)[:k]
    return (sum(VALOR_TURNO_NUEVO[c] for c in elegidas),
            sum(VARIANZA_TURNO_NUEVO[c] for c in elegidas))


def futuro_esperado(tablero, jugador, en_turno):
    """(media, varianza) de los puntos que el jugador va a sumar de aqui al final."""
    libres = [c for c in CATEGORIAS if c not in tablero['usadas'][jugador]]
    k = turnos_restantes(tablero.get('ronda', 0), jugador)
    dados = tablero['dados']

    if not en_turno or dados is None:
        # sus turnos todavia no empezaron
        return plan_futuro(libres, k)

    # esta a mitad de su turno: este turno depende de los dados que tiene ahora
    r = tablero['tiradas_restantes']
    mejor_media, mejor_var = 0.0, 0.0
    for c in libres:
        media_despues, var_despues = plan_futuro([o for o in libres if o != c], k - 1)
        media = VALOR[c][r][dados] + media_despues
        if media > mejor_media:
            mejor_media = media
            mejor_var = VARIANZA[c][r][dados] + var_despues
    return mejor_media, mejor_var


def caracteristicas(estado, raiz):
    """Devuelve (f1, f2, f3) desde el punto de vista del jugador raiz."""
    t = estado.tablero
    rival = 1 - raiz
    f1 = t['puntajes'][raiz] - t['puntajes'][rival]
    media_yo, var_yo = futuro_esperado(t, raiz, estado.jugador == raiz)
    media_riv, var_riv = futuro_esperado(t, rival, estado.jugador == rival)
    f2 = media_yo - media_riv
    mu = f1 + f2                       # diferencia final esperada
    sigma = sqrt(var_yo + var_riv)     # incertidumbre de esa diferencia
    # Voy ganando claro -> f3 = -sigma (la incertidumbre me perjudica).
    # Voy perdiendo claro -> f3 = +sigma (la incertidumbre es mi oportunidad).
    # Parejo -> f3 cerca de 0. La tanh hace el paso suave: con un cambio brusco
    # de signo en mu = 0, a la IA le convenia regalar puntos para quedar
    # "apenas atras" y cobrar el premio por riesgo.
    f3 = -sigma * tanh(mu / sigma) if sigma > 0 else 0.0
    return f1, f2, f3


def evaluar(estado, raiz, w1=W1, w2=W2, w3_por_etapa=None):
    """E_nueva(s) desde el punto de vista del jugador raiz (el que esta decidiendo)."""
    if w3_por_etapa is None:
        w3_por_etapa = W3_POR_ETAPA
    f1, f2, f3 = caracteristicas(estado, raiz)
    w3 = w3_por_etapa[etapa(estado.tablero.get('ronda', 0))]
    return w1 * f1 + w2 * f2 + w3 * f3
