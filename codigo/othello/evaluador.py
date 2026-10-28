# evaluador.py
# Desarrollado con asistencia de IA generativa (Claude, Anthropic, 2026). Ver ../README.md.
# Funciones de evaluacion para el agente de Othello.
#
# Todas reciben (tab, turno, movs_turno, raiz):
#   tab        -> tupla plana de 64 casillas (ver reglas.py)
#   turno      -> jugador al que le toca mover en ese tablero
#   movs_turno -> jugadas validas de ese jugador (ya calculadas, se reutilizan)
#   raiz       -> jugador para el que se evalua (el que esta pensando)
# y devuelven un numero: positivo = bueno para la raiz.
#
#   V0  EvaluadorEstatico  solo la matriz de pesos posicionales (linea base)
#   V1  EvaluadorV1        la funcion original del grupo, sin cambios en su logica
#   V2  EvaluadorV2        version mejorada: caracteristicas normalizadas,
#                          esquinas potenciales, casillas X/C dinamicas,
#                          estabilidad real en bordes y paridad

from reglas import VECINOS, jugadas_validas

UTILIDAD_FIN = 1_000_000  # mucho mayor que cualquier valor heuristico

PESOS_POSICIONALES = (
    100, -20, 10,  5,  5, 10, -20, 100,
    -20, -50, -2, -2, -2, -2, -50, -20,
     10,  -2,  1,  1,  1,  1,  -2,  10,
      5,  -2,  1,  1,  1,  1,  -2,   5,
      5,  -2,  1,  1,  1,  1,  -2,   5,
     10,  -2,  1,  1,  1,  1,  -2,  10,
    -20, -50, -2, -2, -2, -2, -50, -20,
    100, -20, 10,  5,  5, 10, -20, 100,
)

ESQUINAS = (0, 7, 56, 63)

# Para cada esquina: sus casillas C (pegadas por el borde) y su casilla X (diagonal)
CASILLAS_PELIGROSAS = {
    0:  (1, 8, 9),
    7:  (6, 15, 14),
    56: (57, 48, 49),
    63: (62, 55, 54),
}

# Los 4 bordes, recorridos desde una esquina hasta la otra
BORDES = (
    tuple(range(0, 8)),            # fila superior
    tuple(range(56, 64)),          # fila inferior
    tuple(range(0, 64, 8)),        # columna izquierda
    tuple(range(7, 64, 8)),        # columna derecha
)


def normalizar(a, b):
    """Lleva la comparacion a/b al rango [-100, 100]: 100*(a-b)/(a+b)."""
    total = a + b
    return 0.0 if total == 0 else 100.0 * (a - b) / total


class Evaluador:
    nombre = "base"

    def evaluar(self, tab, turno, movs_turno, raiz):
        raise NotImplementedError

    @staticmethod
    def utilidad_terminal(tab, raiz):
        """
        Valor de un tablero TERMINADO. Ganar siempre vale mas que cualquier
        tablero a medio terminar, y entre dos victorias se prefiere la de mayor
        diferencia de fichas.
        """
        diferencia = tab.count(raiz) - tab.count(3 - raiz)
        if diferencia > 0:
            return UTILIDAD_FIN + diferencia
        if diferencia < 0:
            return -UTILIDAD_FIN + diferencia
        return 0

    @staticmethod
    def _movilidades(tab, turno, movs_turno, raiz):
        """Cantidad de jugadas de la raiz y del rival, reutilizando las ya calculadas."""
        if turno == raiz:
            return len(movs_turno), len(jugadas_validas(tab, 3 - raiz))
        return len(jugadas_validas(tab, raiz)), len(movs_turno)

    @staticmethod
    def _frontera(tab, jugador):
        """Fichas del jugador pegadas a al menos una casilla vacia."""
        cuenta = 0
        for i in range(64):
            if tab[i] == jugador:
                for v in VECINOS[i]:
                    if tab[v] == 0:
                        cuenta += 1
                        break
        return cuenta


# ----------------------------------------------------------------------
# V0: puramente estatica
# ----------------------------------------------------------------------
class EvaluadorEstatico(Evaluador):
    """Suma de la matriz de pesos en las casillas de cada jugador. O(64)."""
    nombre = "V0"

    def evaluar(self, tab, turno, movs_turno, raiz):
        rival = 3 - raiz
        valor = 0
        for i in range(64):
            v = tab[i]
            if v == raiz:
                valor += PESOS_POSICIONALES[i]
            elif v == rival:
                valor -= PESOS_POSICIONALES[i]
        return valor


# ----------------------------------------------------------------------
# V1: la funcion original del grupo (misma logica y mismos pesos)
# ----------------------------------------------------------------------
class EvaluadorV1(Evaluador):
    nombre = "V1"

    @staticmethod
    def pesos_fase(fichas_en_tablero):
        if fichas_en_tablero < 20:
            return {"fichas": 0, "esquinas": 30, "movilidad": 5, "estabilidad": 2, "posicion": 1}
        if fichas_en_tablero < 45:
            return {"fichas": 1, "esquinas": 30, "movilidad": 3, "estabilidad": 4, "posicion": 1}
        return {"fichas": 5, "esquinas": 30, "movilidad": 1, "estabilidad": 6, "posicion": 1}

    def evaluar(self, tab, turno, movs_turno, raiz):
        rival = 3 - raiz
        propias, ajenas = tab.count(raiz), tab.count(rival)
        p = self.pesos_fase(propias + ajenas)

        score_fichas = propias - ajenas

        score_esquinas = 0
        for e in ESQUINAS:
            if tab[e] == raiz:
                score_esquinas += 1
            elif tab[e] == rival:
                score_esquinas -= 1

        mov_r, mov_o = self._movilidades(tab, turno, movs_turno, raiz)
        score_movilidad = normalizar(mov_r, mov_o)

        score_estabilidad = self._frontera(tab, rival) - self._frontera(tab, raiz)

        score_posicion = 0
        for i in range(64):
            if tab[i] == raiz:
                score_posicion += PESOS_POSICIONALES[i]
            elif tab[i] == rival:
                score_posicion -= PESOS_POSICIONALES[i]

        return (p["fichas"] * score_fichas
                + p["esquinas"] * score_esquinas
                + p["movilidad"] * score_movilidad
                + p["estabilidad"] * score_estabilidad
                + p["posicion"] * score_posicion)


# ----------------------------------------------------------------------
# V2: version mejorada
# ----------------------------------------------------------------------
class EvaluadorV2(Evaluador):
    """
    E(s) = sum_i w_i(fase) * f_i(s), con TODAS las f_i en [-100, 100], de modo
    que el peso w_i si representa la importancia relativa de cada caracteristica.

      f1 fichas       paridad de fichas normalizada
      f2 esquinas     (2*esquinas tomadas + esquinas que puede tomar ya), normalizado
      f3 movilidad    jugadas disponibles, normalizado
      f4 frontera     fichas pegadas a un hueco (menos es mejor), normalizado
      f5 estabilidad  fichas que ya no se pueden voltear (ancladas en bordes), normalizado
      f6 posicion     matriz de pesos con casillas X/C neutralizadas si su esquina ya
                      esta ocupada, escalada a ~[-100, 100]
      f7 paridad      +100 si la raiz hara la ultima jugada (solo pesa en el final)
    """
    nombre = "V2"

    PESOS_FASE = {
        #           fichas esq  mov  front estab pos  paridad
        "apertura": (0,    30,  10,  10,   5,    5,   0),
        "medio":    (2,    30,   8,   8,  10,    4,   0),
        "final":    (15,   30,   4,   3,  15,    2,   5),
    }

    @staticmethod
    def fase(fichas_en_tablero):
        if fichas_en_tablero < 20:
            return "apertura"
        if fichas_en_tablero < 45:
            return "medio"
        return "final"

    @staticmethod
    def estables(tab, jugador):
        """
        Fichas estables en los bordes. Una ficha de borde solo se puede voltear a lo
        largo de ese borde, asi que es estable si: (a) el borde esta completamente
        lleno, o (b) forma una cadena continua del mismo color que arranca en una
        esquina propia. Es una cota inferior de la estabilidad real, calculada en O(32).
        """
        estables = set()
        for borde in BORDES:
            if all(tab[k] for k in borde):
                estables.update(k for k in borde if tab[k] == jugador)
                continue
            for recorrido in (borde, borde[::-1]):
                for k in recorrido:
                    if tab[k] != jugador:
                        break
                    estables.add(k)
        return len(estables)

    @staticmethod
    def posicion(tab, raiz):
        rival = 3 - raiz
        valor = 0
        for i in range(64):
            v = tab[i]
            if v == raiz:
                valor += PESOS_POSICIONALES[i]
            elif v == rival:
                valor -= PESOS_POSICIONALES[i]
        # Si la esquina ya esta ocupada, sus casillas X/C dejan de ser trampa:
        # se quita la penalizacion (se reemplaza por un valor neutro de +5).
        for esquina, peligrosas in CASILLAS_PELIGROSAS.items():
            if tab[esquina]:
                for k in peligrosas:
                    v = tab[k]
                    if v:
                        ajuste = 5 - PESOS_POSICIONALES[k]
                        valor += ajuste if v == raiz else -ajuste
        return max(-100.0, min(100.0, valor / 4.0))

    def evaluar(self, tab, turno, movs_turno, raiz):
        rival = 3 - raiz
        propias, ajenas = tab.count(raiz), tab.count(rival)
        w = self.PESOS_FASE[self.fase(propias + ajenas)]

        # movilidad (y de paso, las jugadas concretas para las esquinas potenciales)
        if turno == raiz:
            movs_r, movs_o = movs_turno, jugadas_validas(tab, rival)
        else:
            movs_r, movs_o = jugadas_validas(tab, raiz), movs_turno

        f_fichas = normalizar(propias, ajenas)

        esq_r = esq_o = 0
        for e in ESQUINAS:
            if tab[e] == raiz:
                esq_r += 2
            elif tab[e] == rival:
                esq_o += 2
        esq_r += sum(1 for m in movs_r if m in ESQUINAS)
        esq_o += sum(1 for m in movs_o if m in ESQUINAS)
        f_esquinas = normalizar(esq_r, esq_o)

        f_movilidad = normalizar(len(movs_r), len(movs_o))
        f_frontera = normalizar(self._frontera(tab, rival), self._frontera(tab, raiz))
        f_estabilidad = normalizar(self.estables(tab, raiz), self.estables(tab, rival))
        f_posicion = self.posicion(tab, raiz)

        f_paridad = 0.0
        if w[6]:
            vacias = 64 - propias - ajenas
            # con vacias impar, el que mueve ahora pone la ultima ficha (sin contar pases)
            ultimo = turno if vacias % 2 == 1 else 3 - turno
            f_paridad = 100.0 if ultimo == raiz else -100.0

        return (w[0] * f_fichas + w[1] * f_esquinas + w[2] * f_movilidad
                + w[3] * f_frontera + w[4] * f_estabilidad + w[5] * f_posicion
                + w[6] * f_paridad)


EVALUADORES = {
    "V0": EvaluadorEstatico,
    "V1": EvaluadorV1,
    "V2": EvaluadorV2,
}