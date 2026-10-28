# agente.py
# Desarrollado con asistencia de IA generativa (Claude, Anthropic, 2026). Ver ../README.md.
# Agente de Othello: minimax con poda alfa-beta.
#
# Cambios respecto a la version anterior:
#   1. El tipo de nodo (MAX o MIN) se decide por QUIEN tiene el turno, no por
#      alternancia. Asi los pases de turno se manejan bien.
#   2. Los tableros terminados se evaluan con su utilidad real (+-1.000.000),
#      no con la heuristica.
#   3. Ordenamiento de jugadas (mejor primero) -> la poda corta mucho mas.
#   4. Tabla de transposicion: no se reevalua un tablero ya visto.
#   5. Profundizacion iterativa, con limite de tiempo opcional.
#   6. Metricas: tiempo, nodos y evaluaciones por jugada (para el torneo).
# La funcion de evaluacion se recibe como parametro (ver evaluador.py), asi
# todos los agentes comparten la misma busqueda y solo cambia la evaluacion.

import time

from AgenteIA.AgenteJugador import AgenteJugador, ElEstado
from evaluador import Evaluador, EvaluadorV2, PESOS_POSICIONALES, UTILIDAD_FIN
import reglas

EXACTO, COTA_INFERIOR, COTA_SUPERIOR = 0, 1, 2
INF = float("inf")


class _TiempoAgotado(Exception):
    pass


class AgenteOthello(AgenteJugador):

    def __init__(self, evaluador=None, altura=4, tiempo_limite=None, nombre=None,
                 usar_tt=True, ordenar=True, iterativo=True):
        """
        evaluador      instancia de Evaluador (por defecto EvaluadorV2)
        altura         profundidad maxima de busqueda (en jugadas)
        tiempo_limite  segundos por jugada; None = sin limite (profundidad fija)
        usar_tt, ordenar, iterativo  se pueden apagar para medir cuanto aporta cada uno
        """
        super().__init__(altura)
        self.evaluador = evaluador if evaluador is not None else EvaluadorV2()
        self.tiempo_limite = tiempo_limite
        self.usar_tt = usar_tt
        self.ordenar = ordenar
        self.iterativo = iterativo
        self.nombre = nombre or f"{self.evaluador.nombre}-h{altura}"
        self.color = None          # lo asigna el entorno (1 negro, 2 blanco)
        self.BOARD_SIZE = 8
        self.reiniciar_metricas()

    # ------------------------------------------------------------------
    # Metodos que pide AgenteJugador (trabajan con el estado del entorno:
    # tablero numpy 8x8 y jugadas como (fila, col))
    # ------------------------------------------------------------------
    def jugadas(self, estado):
        return estado.movidas

    def testTerminal(self, estado):
        return not estado.movidas

    def get_utilidad(self, estado, jugador):
        return Evaluador.utilidad_terminal(reglas.a_tupla(estado.tablero), jugador)

    def getResultado(self, estado, jugada):
        if jugada not in estado.movidas:
            return estado  # jugada invalida: el estado no cambia
        tab = reglas.a_tupla(estado.tablero)
        nuevo, turno, movs = reglas.siguiente(tab, reglas.a_indice(jugada), estado.jugador)
        return ElEstado(jugador=turno,
                        tablero=reglas.a_numpy(nuevo),
                        movidas=[reglas.a_fila_col(i) for i in movs],
                        get_utilidad=0)

    def funcion_evaluacion(self, estado):
        """Evalua un estado del entorno desde el punto de vista de self.estado.jugador."""
        tab = reglas.a_tupla(estado.tablero)
        raiz = self.estado.jugador
        if not estado.movidas:
            return Evaluador.utilidad_terminal(tab, raiz)
        movs = [reglas.a_indice(m) for m in estado.movidas]
        return self.evaluador.evaluar(tab, estado.jugador, movs, raiz)

    # ------------------------------------------------------------------
    # Busqueda (reemplaza a la de AgenteJugador)
    # ------------------------------------------------------------------
    def podaAlphaBeta_eval(self, estado):
        if not estado.movidas:
            return None
        inicio = time.perf_counter()
        self._inicio = inicio
        self._raiz = estado.jugador
        self._nodos = 0
        self._evaluaciones = 0
        self._tt = {}

        tab = reglas.a_tupla(estado.tablero)
        movs = [reglas.a_indice(m) for m in estado.movidas]
        mejor = self._ordenar(movs, None)[0]
        prof_completada = 0

        profundidades = range(1, self.altura + 1) if self.iterativo else [self.altura]
        for prof in profundidades:
            try:
                jugada, valor = self._buscar_raiz(tab, movs, prof)
            except _TiempoAgotado:
                break  # nos quedamos con lo de la ultima profundidad completa
            mejor, prof_completada = jugada, prof
            if abs(valor) >= UTILIDAD_FIN // 2:
                break  # resultado ya decidido (victoria o derrota forzada)

        self.tiempos.append(time.perf_counter() - inicio)
        self.nodos.append(self._nodos)
        self.evaluaciones.append(self._evaluaciones)
        self.profundidades.append(prof_completada)
        return reglas.a_fila_col(mejor)

    def _buscar_raiz(self, tab, movs, prof):
        raiz = self._raiz
        entrada = self._tt.get((tab, raiz))
        orden = self._ordenar(movs, entrada[3] if entrada else None)
        alpha, mejor = -INF, orden[0]
        for m in orden:
            t2, turno2, movs2 = reglas.siguiente(tab, m, raiz)
            v = self._valor(t2, turno2, movs2, prof - 1, alpha, INF)
            if v > alpha:
                alpha, mejor = v, m
        if self.usar_tt:
            self._tt[(tab, raiz)] = (prof, alpha, EXACTO, mejor)
        return mejor, alpha

    def _valor(self, tab, turno, movs, prof, alpha, beta):
        self._nodos += 1
        if self.tiempo_limite is not None and (self._nodos & 511) == 0:
            if time.perf_counter() - self._inicio > self.tiempo_limite:
                raise _TiempoAgotado()

        if not movs:                     # nadie puede mover: juego terminado
            return Evaluador.utilidad_terminal(tab, self._raiz)
        if prof == 0:                    # se corta por altura
            self._evaluaciones += 1
            return self.evaluador.evaluar(tab, turno, movs, self._raiz)

        clave = (tab, turno)
        mejor_previa = None
        if self.usar_tt:
            entrada = self._tt.get(clave)
            if entrada is not None:
                p, v, tipo, mejor_previa = entrada
                if p >= prof:
                    if tipo == EXACTO:
                        return v
                    if tipo == COTA_INFERIOR:
                        alpha = max(alpha, v)
                    else:
                        beta = min(beta, v)
                    if alpha >= beta:
                        return v

        alpha0, beta0 = alpha, beta
        orden = self._ordenar(movs, mejor_previa)
        mejor_jugada = orden[0]

        if turno == self._raiz:          # nodo MAX: juega el agente
            v = -INF
            for m in orden:
                t2, turno2, movs2 = reglas.siguiente(tab, m, turno)
                w = self._valor(t2, turno2, movs2, prof - 1, alpha, beta)
                if w > v:
                    v, mejor_jugada = w, m
                if v > alpha:
                    alpha = v
                if alpha >= beta:
                    break
        else:                            # nodo MIN: juega el rival
            v = INF
            for m in orden:
                t2, turno2, movs2 = reglas.siguiente(tab, m, turno)
                w = self._valor(t2, turno2, movs2, prof - 1, alpha, beta)
                if w < v:
                    v, mejor_jugada = w, m
                if v < beta:
                    beta = v
                if alpha >= beta:
                    break

        if self.usar_tt:
            if v <= alpha0:
                tipo = COTA_SUPERIOR
            elif v >= beta0:
                tipo = COTA_INFERIOR
            else:
                tipo = EXACTO
            self._tt[clave] = (prof, v, tipo, mejor_jugada)
        return v

    def _ordenar(self, movs, primera):
        """Esquinas y casillas buenas primero; la mejor jugada conocida (TT) adelante de todo."""
        if not self.ordenar:
            orden = list(movs)
        else:
            orden = sorted(movs, key=PESOS_POSICIONALES.__getitem__, reverse=True)
        if primera is not None and primera in orden:
            orden.remove(primera)
            orden.insert(0, primera)
        return orden

    # ------------------------------------------------------------------
    # Metricas
    # ------------------------------------------------------------------
    def reiniciar_metricas(self):
        self.tiempos = []        # segundos por jugada
        self.nodos = []          # nodos visitados por jugada
        self.evaluaciones = []   # llamadas a la funcion de evaluacion por jugada
        self.profundidades = []  # profundidad completada por jugada