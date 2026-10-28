# TableroOthello.py
# Desarrollado con asistencia de IA generativa (Claude, Anthropic, 2026). Ver ../README.md.
# Entorno de Othello.
#
# Cambios respecto a la version anterior:
#   - Cada agente tiene un color (agente.color). Solo juega el agente al que le
#     toca; antes, si un jugador pasaba, el otro agente jugaba con sus fichas.
#   - Ya no depende de la clase HumanoOthello (no estaba importada); usa agente.nombre.
#   - Se puede arrancar desde un estado dado (aperturas del torneo) y en modo
#     silencioso (verbose=False).
#   - Guarda el resultado final en self.resultado.

import numpy as np

from AgenteIA.Entorno import Entorno
from AgenteIA.AgenteJugador import ElEstado
import reglas


class TableroOthello(Entorno):

    def __init__(self, board_size=8, estado_inicial=None, verbose=True):
        super().__init__()
        self.BOARD_SIZE = board_size
        self.verbose = verbose
        self.resultado = None      # (fichas_negro, fichas_blanco, ganador) al terminar
        self.historial = []        # [(color, jugada), ...]

        if estado_inicial is None:
            tab = reglas.tablero_inicial()
            estado_inicial = ElEstado(
                jugador=1,  # negro empieza
                tablero=reglas.a_numpy(tab),
                movidas=[reglas.a_fila_col(i) for i in reglas.jugadas_validas(tab, 1)],
                get_utilidad=0,
            )
        self.juegoActual = estado_inicial

        if self.verbose:
            print("--- Tablero Inicial ---")
            self.mostrar_tablero(self.juegoActual.tablero)

    def insertar(self, agente, color=None):
        """Agrega un agente. Si no se indica color: el primero es negro (1), el segundo blanco (2)."""
        if color is None:
            color = 1 if not self.get_agentes() else 2
        agente.color = color
        super().insertar(agente)

    def get_percepciones(self, agente):
        if self.resultado is not None:
            return
        if not self.juegoActual.movidas:     # nadie puede mover
            self._terminar()
            return
        if agente.color != self.juegoActual.jugador:
            agente.set_acciones(None)        # no es su turno
            return
        agente.estado = self.juegoActual
        agente.programa()

    def ejecutar(self, agente):
        if self.resultado is not None:
            return
        movida = agente.get_acciones()
        if movida is None:
            return
        agente.set_acciones(None)
        self.juegoActual = agente.getResultado(self.juegoActual, movida)
        self.historial.append((agente.color, movida))

        if self.verbose:
            nombre = getattr(agente, "nombre", type(agente).__name__)
            color = "Negro (1)" if agente.color == 1 else "Blanco (2)"
            print(f"\n--- {nombre} [{color}] elige {movida} ---")
            self.mostrar_tablero(self.juegoActual.tablero)

        if not self.juegoActual.movidas:
            self._terminar()

    def _terminar(self):
        negro = int(np.sum(self.juegoActual.tablero == 1))
        blanco = int(np.sum(self.juegoActual.tablero == 2))
        ganador = 1 if negro > blanco else 2 if blanco > negro else 0
        self.resultado = (negro, blanco, ganador)

        if self.verbose:
            print("\n--- ¡JUEGO TERMINADO! ---")
            print(f"Resultado Final: Negro (1): {negro} - Blanco (2): {blanco}")
            if ganador == 1:
                print("¡Gana el jugador Negro (1)!")
            elif ganador == 2:
                print("¡Gana el jugador Blanco (2)!")
            else:
                print("¡Es un empate!")

        for a in self.get_agentes():
            a.inhabilitar()

    def mostrar_tablero(self, tablero):
        """Muestra el tablero en formato de texto en la consola."""
        print("  " + " ".join(map(str, range(self.BOARD_SIZE))))
        print(" +" + "--" * self.BOARD_SIZE)
        for i, fila in enumerate(tablero):
            print(f"{i}|", end=" ")
            for celda in fila:
                print("B" if celda == 1 else "W" if celda == 2 else ".", end=" ")
            print()
        negro = int(np.sum(tablero == 1))
        blanco = int(np.sum(tablero == 2))
        print(f"Puntuación -> Negro (B): {negro} | Blanco (W): {blanco}")