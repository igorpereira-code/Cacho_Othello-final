# cliente_humano.py
from cliente_base import ClienteBase
from interfaz_grafica import InterfazJuego
import time

class ClienteHumano(ClienteBase):
    def __init__(self, host, port):
        super().__init__(host, port)
        self.ui = InterfazJuego()
        self.running = True

    def handle_click(self, pos):
        if not self.game_state or self.game_state['game_over']: return
        if self.game_state['current_player'] != self.player_color: return

        row, col = self.ui.get_clicked_cell(pos)
        if row is not None:
            # Validar si el movimiento está en la lista de movimientos válidos
            valid_moves = [tuple(m) for m in self.game_state.get('valid_moves', [])]
            if (row, col) in valid_moves:
                self.send_move(row, col)
            else:
                print(f"❌ Movimiento inválido en ({row}, {col})")
    
    def on_quit(self):
        self.running = False
        self.disconnect("Usuario cerró la ventana")

    def run(self):
        self.connect()
        
        while self.running:
            # Manejar eventos de Pygame
            if not self.ui.run_event_loop(on_click=self.handle_click, on_quit=self.on_quit):
                break

            # Dibujar el estado actual
            if not self.connected or self.waiting_for_opponent:
                color_info = f"{'Negro' if self.player_color == 1 else 'Blanco'}" if self.player_color else ""
                self.ui.draw_waiting_screen(self.connection_status, color_info)
            else:
                self.ui.draw_game_state(self.game_state, self.player_color)
            
            self.ui.clock.tick(30)
        
        self.ui.quit()

if __name__ == "__main__":
    host = input("Servidor [localhost]: ").strip() or 'localhost'
    port_input = input("Puerto [5555]: ").strip()
    port = int(port_input) if port_input.isdigit() else 5555
    
    cliente = ClienteHumano(host, port)
    cliente.run()