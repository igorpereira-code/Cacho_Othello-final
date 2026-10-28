# pruebas_funcion.py
# Desarrollado con asistencia de IA generativa (Claude, Anthropic, 2026). Ver README.md.
# Comprobaciones de que la funcion de evaluacion y la IA mejorada funcionan bien.
#   python pruebas_funcion.py
#
# Cada prueba compara contra un valor que se puede calcular a mano o contra
# un comportamiento que tiene que cumplirse si o si.

import io
import random
import contextlib
from itertools import product

import funcion_evaluacion as fe
from AgenteCacho import AgenteCacho, puntuar, CATEGORIAS
from AgenteIA.AgenteJugador import ElEstado
from EntornoCacho import EntornoCacho
from agente_ia import AgenteCachoIAMejorada

resultados = []


def prueba(nombre, condicion, detalle=""):
    resultados.append(condicion)
    print(f"[{'OK' if condicion else 'FALLA'}] {nombre}" + (f"  ({detalle})" if detalle else ""))


def estado_de(dados, tiradas, usadas0=(), puntajes=(0, 0), ronda=0):
    tab = {'dados': dados, 'tiradas_restantes': tiradas, 'puntajes': list(puntajes),
           'usadas': [set(usadas0), set()], 'ronda': ronda}
    return ElEstado(jugador=0, get_utilidad=0, tablero=tab, movidas=None)


def decidir(ia, estado):
    ia.estado = estado
    return ia.elegir_accion(estado)


# ------------------------------------------------------------
print("1) Probabilidades y tablas")
# ------------------------------------------------------------
suma = sum(fe.DIST_TIRADA[5].values())
prueba("las probabilidades de 5 dados suman 1", abs(suma - 1) < 1e-12, f"{suma:.12f}")

base = AgenteCacho()
real_grande = sum(puntuar('grande', d) for d in product(range(1, 7), repeat=5)) / 6 ** 5
prueba("la base sobreestima 'grande' (trata las 252 combinaciones como igual de probables)",
       base._valor_esperado_cat('grande') > 20 * real_grande,
       f"base {base._valor_esperado_cat('grande'):.3f} vs real {real_grande:.3f}")

p = sum(q * fe.VALOR['grande'][2][e] for e, q in fe.DIST_TIRADA[5].items()) / 50
prueba("P(grande) con tirada inicial + 2 tiradas = 4.60% (valor conocido del Yahtzee)",
       abs(100 * p - 4.60) < 0.01, f"{100 * p:.2f}%")

m = sum(q * fe.VALOR['6'][0][e] for e, q in fe.DIST_TIRADA[5].items())
m2 = sum(q * fe.VALOR['6'][0][e] ** 2 for e, q in fe.DIST_TIRADA[5].items())
prueba("varianza de '6' con una tirada = 36*5*(1/6)*(5/6) = 25", abs(m2 - m * m - 25) < 1e-9,
       f"{m2 - m * m:.6f}")

m2g = sum(q * (fe.VARIANZA['grande'][2][e] + fe.VALOR['grande'][2][e] ** 2)
          for e, q in fe.DIST_TIRADA[5].items())
prueba("varianza de 'grande' = 2500*p*(1-p)", abs(m2g - (50 * p) ** 2 - 2500 * p * (1 - p)) < 1e-9)

# ------------------------------------------------------------
print("\n2) Punto de vista y simetria")
# ------------------------------------------------------------
tab = {'dados': None, 'tiradas_restantes': 3, 'puntajes': [30, 10],
       'usadas': [{'6'}, {'1'}], 'ronda': 2}
s = ElEstado(jugador=0, get_utilidad=0, tablero=tab, movidas=None)
prueba("evaluar desde un jugador es exactamente el opuesto que desde el otro",
       abs(fe.evaluar(s, 0, w3_por_etapa={'inicio': 0, 'medio': 0, 'final': 0})
           + fe.evaluar(s, 1, w3_por_etapa={'inicio': 0, 'medio': 0, 'final': 0})) < 1e-9)
fin = ElEstado(jugador=0, get_utilidad=0, tablero={'dados': None, 'tiradas_restantes': 3,
               'puntajes': [80, 95], 'usadas': [set(), set()], 'ronda': 10}, movidas=None)
prueba("en un estado final la funcion da la diferencia real de puntos", fe.evaluar(fin, 0) == -15,
       f"{fe.evaluar(fin, 0)}")

# con w3 < 1, tener mas puntos nunca puede empeorar la evaluacion (el termino de riesgo
# no debe incentivar a regalar puntos)
w3_alto = {'inicio': 0.9, 'medio': 0.9, 'final': 0.9}
rng = random.Random(3)
monotona = True
for _ in range(300):
    usadas = [set(rng.sample(CATEGORIAS, 2)), set(rng.sample(CATEGORIAS, 2))]
    p0, p1 = rng.randint(0, 120), rng.randint(0, 120)
    def con_puntos(extra):
        return ElEstado(jugador=1, get_utilidad=0, movidas=None, tablero={
            'dados': None, 'tiradas_restantes': 3, 'puntajes': [p0 + extra, p1],
            'usadas': usadas, 'ronda': 5})
    valores = [fe.evaluar(con_puntos(x), 0, w3_por_etapa=w3_alto) for x in range(0, 40, 2)]
    monotona = monotona and all(b > a for a, b in zip(valores, valores[1:]))
prueba("con w3 < 1, mas puntos propios siempre suben la evaluacion (300 estados al azar)", monotona)

# caso real que encontro el error del termino de riesgo: (3,3,5,5,6) sin tiradas,
# ronda 4, puntajes 54-52 -> anotar 10 en '5' tiene que ser mejor que 6 en '6'
caso = ElEstado(jugador=0, get_utilidad=0, movidas=None, tablero={
    'dados': (3, 3, 5, 5, 6), 'tiradas_restantes': 0, 'puntajes': [54, 52],
    'usadas': [{'grande', '4'}, {'3', 'poker'}], 'ronda': 4})
prueba("con (3,3,5,5,6) sin tiradas no regala puntos: anota 10 en '5'",
       decidir(AgenteCachoIAMejorada(), caso) == ('anotar', '5'))

# ------------------------------------------------------------
print("\n3) Decisiones de la IA mejorada")
# ------------------------------------------------------------
prueba("con (6,6,6,6,6) anota 'grande'",
       decidir(AgenteCachoIAMejorada(), estado_de((6, 6, 6, 6, 6), 2)) == ('anotar', 'grande'))
prueba("con (3,3,3,4,4) anota 'full'",
       decidir(AgenteCachoIAMejorada(), estado_de((3, 3, 3, 4, 4), 3)) == ('anotar', 'full'))
a = decidir(AgenteCachoIAMejorada(), estado_de((2, 2, 2, 5, 6), 3))
prueba("con (2,2,2,5,6) y 3 tiradas guarda los tres 2", a[0] == 'tirar' and a[1] == frozenset({3, 4}))
a = decidir(AgenteCachoIAMejorada(), estado_de((1, 3, 4, 5, 6), 0))
prueba("sin tiradas siempre anota", a[0] == 'anotar', str(a))

# ------------------------------------------------------------
print("\n4) Las optimizaciones no cambian la decision")
# ------------------------------------------------------------
iguales = True
rng = random.Random(7)
for _ in range(15):
    dados = tuple(sorted(rng.randint(1, 6) for _ in range(5)))
    tiradas = rng.randint(1, 3)
    usadas = set(rng.sample(CATEGORIAS, rng.randint(0, 4)))
    e = estado_de(dados, tiradas, usadas0=usadas, ronda=2 * len(usadas))
    con = decidir(AgenteCachoIAMejorada(profundidad_adaptativa=False), e)
    sin_memo = decidir(AgenteCachoIAMejorada(profundidad_adaptativa=False, usar_memo=False), e)
    iguales = iguales and con == sin_memo
prueba("con y sin memoizacion se elige la misma accion (15 estados al azar)", iguales)

ia_poda = AgenteCachoIAMejorada(profundidad_adaptativa=False)
ia_sin = AgenteCachoIAMejorada(profundidad_adaptativa=False, usar_poda=False)
e = estado_de((1, 2, 3, 3, 5), 3)
ia_poda.estado = ia_sin.estado = e
ia_poda._n_eval = ia_sin._n_eval = 0
ia_poda.elegir_accion(e)
ia_sin.elegir_accion(e)
prueba("la poda reduce las evaluaciones", ia_poda._n_eval < ia_sin._n_eval,
       f"{ia_poda._n_eval} con poda vs {ia_sin._n_eval} sin poda")

# ------------------------------------------------------------
print("\n5) Partida completa en el entorno")
# ------------------------------------------------------------
random.seed(1)
dados_inicio = [EntornoCacho().juegoActual.tablero['dados'] for _ in range(200)]
prueba("el primer turno arranca con una tirada al azar", len(set(dados_inicio)) > 50,
       f"{len(set(dados_inicio))} tiradas distintas en 200 partidas")


class EntornoIAvsIA(EntornoCacho):
    def evolucionar(self):
        if self.finalizar():
            return
        agente = self.get_agentes()[self.juegoActual.jugador]
        self.get_percepciones(agente)
        agente.programa()
        self.ejecutar(agente)


with contextlib.redirect_stdout(io.StringIO()):
    e = EntornoIAvsIA()
    e.insertar(AgenteCachoIAMejorada())
    e.insertar(AgenteCachoIAMejorada())
    e.run()
t = e.juegoActual.tablero
prueba("una partida IA mejorada vs IA mejorada termina bien",
       t['ronda'] == 10 and len(t['usadas'][0]) == 5 and len(t['usadas'][1]) == 5,
       f"puntajes {t['puntajes']}")

print(f"\n{sum(resultados)}/{len(resultados)} pruebas OK")
