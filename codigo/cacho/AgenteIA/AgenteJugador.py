#################################################################
# Nombre      : Entorno                                         #
# Version     : 0.05.03.2017                                    #
# Autor       : Victor Estevez                                  #
# Descripcion : Clase Agentes con Adversarios                   #
##################################################################


from AgenteIA.Agente import Agente
from collections import namedtuple
import time


ElEstado = namedtuple('ElEstado', 'jugador, get_utilidad, tablero, movidas')


class AgenteJugador(Agente):

    def __init__(self, altura=3):
        Agente.__init__(self)
        self.estado = None
        self.juego = None
        self.utilidad = None
        self.tecnica = None
        self.altura = altura

    def jugadas(self, estado):
        raise Exception("Error: No se implemento")

    def get_utilidad(self, estado, jugador):
        raise Exception("Error: No se implemento")

    def testTerminal(self, estado):
        return not self.jugadas(estado)

    def getResultado(self, estado, m):
        raise Exception("Error: No se implemento")

    def minimax(self, estado):

        def valorMax(e):
            if self.testTerminal(e):
                return self.get_utilidad(e, self.estado.jugador)
            v = -100
            for a in self.jugadas(e):
                v = max(v, valorMin(self.getResultado(e, a)))
            return v

        def valorMin(e):
            if self.testTerminal(e):
                return self.get_utilidad(e, self.estado.jugador)
            v = 100
            for a in self.jugadas(e):
                v = min(v, valorMax(self.getResultado(e, a)))
            return v

        return max(self.jugadas(estado), key=lambda a: valorMin(self.getResultado(estado, a)))

    def podaAlphaBeta(self, estado):
        jugador = estado.jugador

        def max_value(e, alpha, betita):
            if self.testTerminal(e):
                return self.get_utilidad(e, jugador)
            vm = -100
            for j in self.jugadas(e):
                vm = max(vm, min_value(self.getResultado(e, j), alpha, betita))
                if vm >= beta:
                    return vm
                alpha = max(alpha, vm)
            return vm

        def min_value(e, alpha, betita):
            if self.testTerminal(e):
                return self.get_utilidad(e, jugador)
            vm = 100
            for j in self.jugadas(e):
                vm = min(vm, max_value(self.getResultado(e, j), alpha, betita))
                if vm <= alpha:
                    return vm
                betita = min(betita, vm)
            return vm

        mejor_score = -100
        beta = 100
        mejor_accion = None
        for a in self.jugadas(estado):
            v = min_value(self.getResultado(estado, a), mejor_score, beta)
            if v > mejor_score:
                mejor_score = v
                mejor_accion = a
        return mejor_accion


    def funcion_evaluacion(self, estado):
        raise Exception("no se implemento")

    def podaAlphaBeta_eval(self, estado):
        jugador = estado.jugador
        a = 0
        def max_value(e, alpha, betita, a):
            if self.testTerminal(e):
                return self.get_utilidad(e, jugador)
            if a == self.altura:
                print("vencio la altura con valor : ", self.funcion_evaluacion(e))
                return self.funcion_evaluacion(e)

            vm = -100
            for j in self.jugadas(e):
                vm = max(vm, min_value(self.getResultado(e, j), alpha, betita, a + 1))
                if vm >= beta:
                    return vm
                alpha = max(alpha, vm)
            return vm

        def min_value(e, alpha, betita, a):
            if self.testTerminal(e):
                return self.get_utilidad(e, jugador)
            if a == self.altura:
                print("vencio la altura con valor : ", self.funcion_evaluacion(e))
                return self.funcion_evaluacion(e)
            vm = 100
            for j in self.jugadas(e):
                vm = min(vm, max_value(self.getResultado(e, j), alpha, betita, a + 1))
                if vm <= alpha:
                    return vm
                betita = min(betita, vm)
            return vm

        mejor_score = -100
        beta = 100
        mejor_accion = None
        for a in self.jugadas(estado):
            v = min_value(self.getResultado(estado, a), mejor_score, beta, self.altura)
            if v > mejor_score:
                mejor_score = v
                mejor_accion = a
        return mejor_accion

    def expectimax(self, estado, profundidad, es_turno_jugador):
        if self.testTerminal(estado) or profundidad == self.max_profundidad:
            return self.funcion_evaluacion(estado)

        if es_turno_jugador:
            max_valor = -float('inf')
            for movida in self.jugadas(estado):
                nuevo_estado = self.getResultado(estado, movida)
                valor = self.expectimax(nuevo_estado, profundidad + 1, False)
                max_valor = max(max_valor, valor)
            return max_valor
        else:
            suma_valores = 0
            jugadas = self.jugadas(estado)
            probabilidad = 1 / len(jugadas)  # Supone que cada movimiento es igualmente probable

            for movida in jugadas:
                nuevo_estado = self.getResultado(estado, movida)
                valor = self.expectimax(nuevo_estado, profundidad + 1, True)
                suma_valores += valor * probabilidad

            return suma_valores

    # Agregar en AgenteJugador.py

    def expectiminimax(self, estado, profundidad, es_max):
        """
        Expectiminimax con nodos de azar (probabilidades).
        - es_max: True si es turno del agente MAX.
        - El estado debe exponer 'es_nodo_azar' y 'probabilidades_hijos'.
        """
        if self.testTerminal(estado) or profundidad == self.altura:
            return self.funcion_evaluacion(estado)

        # Nodo de AZAR
        if getattr(estado, 'es_nodo_azar', False):
            valor = 0
            for hijo, prob in self.hijos_con_probabilidad(estado):
                valor += prob * self.expectiminimax(hijo, profundidad + 1, es_max)
            return valor

        # Nodo MAX
        if es_max:
            mejor = -float('inf')
            for movida in self.jugadas(estado):
                hijo = self.getResultado(estado, movida)
                mejor = max(mejor, self.expectiminimax(hijo, profundidad + 1, False))
            return mejor

        # Nodo MIN
        else:
            mejor = float('inf')
            for movida in self.jugadas(estado):
                hijo = self.getResultado(estado, movida)
                mejor = min(mejor, self.expectiminimax(hijo, profundidad + 1, True))
            return mejor

    def hijos_con_probabilidad(self, estado):
        """
        Devuelve lista de (estado_hijo, probabilidad) para nodos de azar.
        El estado de Cacho debe implementarlo.
        """
        raise Exception("No se implemento")

    def elige_expectiminimax(self, estado):
        """Devuelve la mejor acción usando Expectiminimax."""
        mejor_valor = -float('inf')
        mejor_accion = None
        for movida in self.jugadas(estado):
            hijo = self.getResultado(estado, movida)
            valor = self.expectiminimax(hijo, 0, False)
            if valor > mejor_valor:
                mejor_valor = valor
                mejor_accion = movida
        return mejor_accion
    def mide_tiempo(funcion):
        def funcion_medida(*args, **kwards):
            inicio = time.time()
            c = funcion(*args, **kwards)
            print("Tiempo de ejecucion: ", time.time() - inicio)
            return c

        return funcion_medida

    @mide_tiempo
    def programa(self):
        if self.tecnica == "minimax":
            self.set_acciones(self.minimax(self.estado))
        elif self.tecnica == "podaalfabeta":
            self.set_acciones(self.podaAlphaBeta(self.estado))
        elif self.tecnica == "fun_eval":
            self.set_acciones(self.podaAlphaBeta_eval(self.estado))
        elif self.tecnica == "expectiminimax":
            self.set_acciones(self.elige_expectiminimax(self.estado))
