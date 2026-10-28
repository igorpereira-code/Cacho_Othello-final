# interfaz_grafica.py
import pygame
import sys
import numpy as np

# Constantes de la Interfaz
WIDTH, HEIGHT = 800, 800
BOARD_SIZE = 8
CELL_SIZE = WIDTH // BOARD_SIZE
DOT_RADIUS = CELL_SIZE // 2 - 5
HIGHLIGHT_RADIUS = CELL_SIZE // 2 - 10

# Colores
BACKGROUND = (0, 128, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
HIGHLIGHT = (255, 255, 0, 100)


class InterfazJuego:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Othello IA")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 24)
        self.big_font = pygame.font.SysFont('Arial', 36, bold=True)
        
        # Tablero por defecto para mostrar mientras se espera
        self.default_board = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=int)
        mid = BOARD_SIZE // 2
        self.default_board[mid - 1][mid - 1] = 2
        self.default_board[mid][mid] = 2
        self.default_board[mid - 1][mid] = 1
        self.default_board[mid][mid - 1] = 1

    def draw_waiting_screen(self, status, player_color_info):
        self.screen.fill(BACKGROUND)
        self._draw_grid()
        self._draw_pieces(self.default_board)

        # Overlay oscuro
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        # Textos
        title = self.big_font.render("Othello IA", True, WHITE)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 150))

        status_text = self.font.render(status, True, YELLOW)
        self.screen.blit(status_text, (WIDTH // 2 - status_text.get_width() // 2, 250))
        
        if player_color_info:
             player_text = self.font.render(f"Juegas como: {player_color_info}", True, WHITE)
             self.screen.blit(player_text, (WIDTH // 2 - player_text.get_width() // 2, 300))

        wait_text = self.big_font.render("Esperando oponente...", True, WHITE)
        self.screen.blit(wait_text, (WIDTH // 2 - wait_text.get_width() // 2, 400))
        
        pygame.display.flip()

    def draw_game_state(self, game_state, player_color):
        self.screen.fill(BACKGROUND)
        self._draw_grid()
        
        if not game_state:
            return

        self._draw_pieces(np.array(game_state['board']))
        
        is_my_turn = game_state['current_player'] == player_color
        if not game_state['game_over'] and is_my_turn:
            self._draw_valid_moves(game_state.get('valid_moves', []))
            
        self._draw_game_info(game_state, player_color)
        
        pygame.display.flip()

    def _draw_grid(self):
        for i in range(BOARD_SIZE + 1):
            pygame.draw.line(self.screen, BLACK, (0, i * CELL_SIZE), (WIDTH, i * CELL_SIZE), 2)
            pygame.draw.line(self.screen, BLACK, (i * CELL_SIZE, 0), (i * CELL_SIZE, HEIGHT), 2)

    def _draw_pieces(self, board):
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if board[r, c] != 0:
                    color = BLACK if board[r, c] == 1 else WHITE
                    center = (c * CELL_SIZE + CELL_SIZE // 2, r * CELL_SIZE + CELL_SIZE // 2)
                    pygame.draw.circle(self.screen, color, center, DOT_RADIUS)

    def _draw_valid_moves(self, valid_moves):
        for move in valid_moves:
            r, c = move
            center = (c * CELL_SIZE + CELL_SIZE // 2, r * CELL_SIZE + CELL_SIZE // 2)
            
            # Círculo semitransparente para resaltar
            highlight_surface = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            pygame.draw.circle(highlight_surface, HIGHLIGHT, (CELL_SIZE // 2, CELL_SIZE // 2), HIGHLIGHT_RADIUS)
            self.screen.blit(highlight_surface, (c * CELL_SIZE, r * CELL_SIZE))

    def _draw_game_info(self, game_state, player_color):
        info_bar = pygame.Surface((WIDTH, 60))
        info_bar.fill(BLACK)
        self.screen.blit(info_bar, (0, HEIGHT - 60))

        # Puntuaciones
        scores = game_state['scores']
        score_text = f"Negro: {scores['black']} | Blanco: {scores['white']}"
        score_surface = self.font.render(score_text, True, WHITE)
        self.screen.blit(score_surface, (10, HEIGHT - 45))
        
        # Turno
        if game_state['game_over']:
            winner = game_state['winner']
            if winner == 0:
                turn_text = "¡EMPATE!"
            elif winner == player_color:
                turn_text = "¡HAS GANADO!"
            else:
                turn_text = "HAS PERDIDO"
            color = YELLOW
        else:
            is_my_turn = game_state['current_player'] == player_color
            turn_text = "TU TURNO" if is_my_turn else "TURNO DEL OPONENTE"
            color = GREEN if is_my_turn else RED

        turn_surface = self.big_font.render(turn_text, True, color)
        self.screen.blit(turn_surface, (WIDTH // 2 - turn_surface.get_width() // 2, HEIGHT - 50))
        
    def get_clicked_cell(self, pos):
        col = pos[0] // CELL_SIZE
        row = pos[1] // CELL_SIZE
        if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE:
            return row, col
        return None, None

    def run_event_loop(self, on_click=None, on_quit=None):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if on_quit:
                    on_quit()
                return False # Indica que se debe salir
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if on_click:
                    on_click(event.pos)
        return True # Indica que se debe continuar

    def quit(self):
        pygame.quit()
        sys.exit()