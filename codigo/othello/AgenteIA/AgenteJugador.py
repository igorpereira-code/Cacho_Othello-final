from AgenteIA.Agente import Agente
from collections import namedtuple
import time

ElEstado = namedtuple('ElEstado', 'jugador, get_utilidad, tablero, movidas')

class AgenteJugador(Agente):
    def __init__(self, altura=3):
        Agente.__init__(self)
        self.estado = None
        self.altura = altura
        self.tecnica = "podaalfabeta" # Por defecto

    def jugadas(self, estado):
        raise NotImplementedError

    def get_utilidad(self, estado, jugador):
        raise NotImplementedError

    def testTerminal(self, estado):
        return not estado.movidas

    def getResultado(self, estado, m):
        raise NotImplementedError

    def funcion_evaluacion(self, estado):
        raise NotImplementedError

    def podaAlphaBeta_eval(self, estado):
        jugador = estado.jugador

        def max_value(e, alpha, beta, profundidad):
            if self.testTerminal(e) or profundidad >= self.altura:
                return self.funcion_evaluacion(e)
            v = -float('inf')
            for accion in self.jugadas(e):
                v = max(v, min_value(self.getResultado(e, accion), alpha, beta, profundidad + 1))
                if v >= beta: return v
                alpha = max(alpha, v)
            return v

        def min_value(e, alpha, beta, profundidad):
            if self.testTerminal(e) or profundidad >= self.altura:
                return self.funcion_evaluacion(e)
            v = float('inf')
            for accion in self.jugadas(e):
                v = min(v, max_value(self.getResultado(e, accion), alpha, beta, profundidad + 1))
                if v <= alpha: return v
                beta = min(beta, v)
            return v

        mejor_score = -float('inf')
        beta = float('inf')
        mejor_accion = self.jugadas(estado)[0] if self.jugadas(estado) else None
        
        for accion in self.jugadas(estado):
            v = min_value(self.getResultado(estado, accion), mejor_score, beta, 1) # Inicia en profundidad 1
            if v > mejor_score:
                mejor_score = v
                mejor_accion = accion
        return mejor_accion

    def mide_tiempo(funcion):
        def funcion_medida(*args, **kwargs):
            inicio = time.time()
            c = funcion(*args, **kwargs)
            return c
        return funcion_medida

    @mide_tiempo
    def programa(self):
        if not self.estado.movidas:
            self.set_acciones(None)
            return
        
        self.set_acciones(self.podaAlphaBeta_eval(self.estado))