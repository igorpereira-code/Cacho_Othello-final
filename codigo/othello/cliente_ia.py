# cliente_ia.py
# Conecta el agente al servidor de la competencia (mismo protocolo que cliente_humano.py).
#   py cliente_ia.py --host 192.168.0.10 --agente V2:6
#   py cliente_ia.py --host 192.168.0.10 --agente V2:6 --ver      (con ventana de pygame)

import argparse
import time

import numpy as np

from AgenteIA.AgenteJugador import ElEstado
from cliente_base import ClienteBase
from agente import AgenteOthello
from evaluador import EVALUADORES


class ClienteIA(ClienteBase):
    def __init__(self, host, port, agente, ver=False):
        super().__init__(host, port)
        self.agente = agente
        # Cada mensaje con un estado nuevo sube este contador. La IA juega una sola vez
        # por mensaje, asi no responde dos veces al mismo estado, y si el servidor
        # reinicia la partida (nuevo game_start) vuelve a jugar aunque el tablero
        # sea igual al de la partida anterior.
        self._version = 0
        self._version_respondida = 0
        self.on_message_received = self._al_recibir
        self.ui = None
        if ver:
            from interfaz_grafica import InterfazJuego
            self.ui = InterfazJuego()

    def _al_recibir(self, mensaje):
        if mensaje.get("type") in ("game_start", "game_update"):
            if mensaje.get("type") == "game_start":
                print("🎬 Partida nueva")
            self._version += 1

    def _mi_turno(self):
        gs = self.game_state
        return (gs is not None and not gs["game_over"]
                and gs["current_player"] == self.player_color
                and gs.get("valid_moves"))

    def jugar_turno(self):
        gs = self.game_state
        estado = ElEstado(jugador=gs["current_player"],
                          tablero=np.array(gs["board"], dtype=int),
                          movidas=[tuple(m) for m in gs["valid_moves"]],   # llegan como listas
                          get_utilidad=0)
        self.agente.estado = estado
        jugada = self.agente.podaAlphaBeta_eval(estado)
        print(f"🤖 {self.agente.nombre} juega {jugada} en {self.agente.tiempos[-1]:.2f}s "
              f"(profundidad {self.agente.profundidades[-1]}, {self.agente.nodos[-1]} nodos)")
        self.send_move(*jugada)

    def _dibujar(self):
        if not self.ui.run_event_loop(on_quit=lambda: self.disconnect("Ventana cerrada")):
            return False
        if self.waiting_for_opponent or not self.game_state:
            color = ("Negro" if self.player_color == 1 else "Blanco") if self.player_color else ""
            self.ui.draw_waiting_screen(self.connection_status, color)
        else:
            self.ui.draw_game_state(self.game_state, self.player_color)
        return True

    def run(self):
        if not self.connect():
            return
        fin_anunciado = False
        try:
            while self.connected:
                version = self._version
                if (version != self._version_respondida
                        and not self.waiting_for_opponent and self._mi_turno()):
                    self._version_respondida = version
                    self.jugar_turno()

                gs = self.game_state
                if gs and gs["game_over"] and not fin_anunciado:
                    s = gs["scores"]
                    print(f"🏁 Fin: Negro {s['black']} - Blanco {s['white']}")
                    fin_anunciado = True
                elif gs and not gs["game_over"]:
                    fin_anunciado = False

                if self.ui is not None:
                    if not self._dibujar():
                        break
                    self.ui.clock.tick(30)
                else:
                    time.sleep(0.05)
        except KeyboardInterrupt:
            pass
        finally:
            self.disconnect("Cliente IA terminado")
            if self.ui is not None:
                self.ui.quit()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=5555)
    ap.add_argument("--agente", default="V2:6", help="EVALUADOR:ALTURA, ej. V2:6")
    ap.add_argument("--tiempo", type=float, default=None, help="segundos por jugada")
    ap.add_argument("--ver", action="store_true", help="mostrar la partida en una ventana")
    args = ap.parse_args()

    nombre_eval, altura = args.agente.split(":")
    agente = AgenteOthello(EVALUADORES[nombre_eval](), altura=int(altura),
                           tiempo_limite=args.tiempo, nombre=args.agente)
    ClienteIA(args.host, args.port, agente, ver=args.ver).run()