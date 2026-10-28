from AgenteIA.AgenteJugador import AgenteJugador, ElEstado
from collections import Counter
from itertools import combinations_with_replacement
from math import factorial

# ============================================================
# CONSTANTES DEL JUEGO
# ============================================================

CATEGORIAS = ['1','2','3','4','5','6','escalera','full','poker','grande']

NOMBRES_CAT = {
    '1':'Balas (1)', '2':'Doses', '3':'Treses', '4':'Cuatros',
    '5':'Cincos', '6':'Seises', 'escalera':'Escalera',
    'full':'Full', 'poker':'Póker', 'grande':'Grande'
}

TODOS_LOS_ESTADOS = list(combinations_with_replacement(range(1, 7), 5))

# ============================================================
# UTILIDADES
# ============================================================

def normalizar(dados):
    return tuple(sorted(dados))

def puntuar(categoria, dados):
    c = Counter(dados)
    valores = sorted(c.values(), reverse=True)
    if categoria in '123456':
        return dados.count(int(categoria)) * int(categoria)
    elif categoria == 'escalera':
        s = set(dados)
        return 25 if s == {1,2,3,4,5} or s == {2,3,4,5,6} else 0
    elif categoria == 'full':
        return 30 if valores == [3, 2] else 0
    elif categoria == 'poker':
        return 40 if valores[0] >= 4 else 0
    elif categoria == 'grande':
        return 50 if valores[0] == 5 else 0
    return 0

def probabilidad_tirada(dados_actuales, dados_a_tirar):
    indices_mantener = [i for i in range(5) if i not in dados_a_tirar]
    dados_fijos = [dados_actuales[i] for i in indices_mantener]
    n_tirar = len(dados_a_tirar)
    resultados = combinations_with_replacement(range(1, 7), n_tirar)
    total = 6 ** n_tirar
    probas = {}
    for combo in resultados:
        cuenta = Counter(combo)
        formas = factorial(n_tirar)
        for v in cuenta.values():
            formas //= factorial(v)
        estado = normalizar(list(dados_fijos) + list(combo))
        probas[estado] = probas.get(estado, 0) + formas / total
    return probas

def acciones_reservar(dados):
    acciones = set()
    for mascara in range(32):
        mantener = tuple(dados[i] for i in range(5) if mascara & (1 << i))
        tirar = frozenset(i for i in range(5) if not (mascara & (1 << i)))
        acciones.add((normalizar(mantener), tirar))
    return list(acciones)

# ============================================================
# CLASE BASE PARA AGENTES DEL CACHO
# ============================================================

class AgenteCacho(AgenteJugador):
    """Clase base con lógica común a IA y humano."""

    def __init__(self, nombre="Agente", altura=1):
        AgenteJugador.__init__(self, altura=altura)
        self.nombre = nombre
        self.max_profundidad = altura

    # --------- API requerida por AgenteJugador ---------

    def jugadas(self, estado):
        """
        Genera todas las acciones legales:
        - ('tirar', frozenset_indices) si quedan tiradas
        - ('anotar', categoria) siempre
        """
        acciones = []
        turno = estado.jugador
        disponibles = [c for c in CATEGORIAS if c not in estado.tablero['usadas'][turno]]

        # Anotar siempre es posible
        for cat in disponibles:
            acciones.append(('anotar', cat))

        # Tirar solo si quedan tiradas
        if estado.tablero['tiradas_restantes'] > 0:
            for _, tirar in acciones_reservar(estado.tablero['dados']):
                if tirar:
                    acciones.append(('tirar', tirar))

        return acciones

    def getResultado(self, estado, m):
        """Aplica una acción y devuelve el nuevo estado."""
        # tablero = dict(estado.tablero)
        tablero = self._copiar_tablero(estado.tablero)  # ← antes era dict(estado.tablero)
        tablero['usadas'] = [set(estado.tablero['usadas'][0]),
                             set(estado.tablero['usadas'][1])]
        tablero['puntajes'] = list(estado.tablero['puntajes'])
        tablero['dados'] = estado.tablero['dados']
        tablero['tiradas_restantes'] = estado.tablero['tiradas_restantes']

        tipo, param = m
        turno = estado.jugador
        nuevo_jugador = 1 - turno

        if tipo == 'anotar':
            cat = param
            pts = puntuar(cat, tablero['dados'])
            tablero['puntajes'][turno] += pts
            tablero['usadas'][turno].add(cat)
            tablero['dados'] = (1, 1, 1, 1, 1)
            tablero['tiradas_restantes'] = 3
            tablero['ronda'] = estado.tablero.get('ronda', 0) + 1
        elif tipo == 'tirar':
            # La tirada real la resuelve el entorno; aquí simulamos
            # la mejor tirada esperada no aplica (es un nodo de azar)
            tablero['tiradas_restantes'] -= 1

        return ElEstado(
            jugador=nuevo_jugador,
            get_utilidad=0,
            tablero=tablero,
            movidas=self.jugadas(ElEstado(nuevo_jugador, 0, tablero, None))
        )

    def get_utilidad(self, estado, jugador):
        """Utilidad: diferencia de puntaje desde la perspectiva del jugador."""
        p = estado.tablero['puntajes']
        return (p[jugador] - p[1 - jugador])

    def testTerminal(self, estado):
        return estado.tablero.get('ronda', 0) >= 10

    # --------- Función de evaluación para hojas ---------

    def funcion_evaluacion(self, estado):
        """Heurística: puntaje actual + valor esperado de categorías restantes."""
        jugador = estado.jugador
        oponente = 1 - jugador
        p = estado.tablero['puntajes']
        restantes = [c for c in CATEGORIAS if c not in estado.tablero['usadas'][jugador]]
        futuro = sum(self._valor_esperado_cat(c) for c in restantes)
        return (p[jugador] + futuro * 0.6) - p[oponente]

    def _valor_esperado_cat(self, categoria):
        if not hasattr(self, '_cache_ve'):
            self._cache_ve = {}
        if categoria not in self._cache_ve:
            total = sum(puntuar(categoria, e) for e in TODOS_LOS_ESTADOS)
            self._cache_ve[categoria] = total / len(TODOS_LOS_ESTADOS)
        return self._cache_ve[categoria]

    def _copiar_tablero(self, tablero):
        return {
            'dados': tuple(tablero['dados']),
            'tiradas_restantes': tablero['tiradas_restantes'],
            'puntajes': list(tablero['puntajes']),
            'usadas': [set(tablero['usadas'][0]), set(tablero['usadas'][1])],
            'ronda': tablero['ronda'],
        }