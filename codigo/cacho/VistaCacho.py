import pygame
import sys
import random
from AgenteCacho import CATEGORIAS, NOMBRES_CAT, puntuar

ANCHO, ALTO = 1000, 700
FPS = 60

NEGRO = (0, 0, 0)
BLANCO = (255, 255, 255)
GRIS = (60, 60, 70)
GRIS_CLARO = (100, 100, 110)
VERDE = (60, 180, 100)
VERDE_HOVER = (80, 210, 120)
ROJO = (200, 70, 70)
ROJO_HOVER = (230, 90, 90)
AZUL = (70, 130, 200)
AZUL_HOVER = (90, 160, 230)
AMARILLO = (240, 200, 70)
FONDO = (30, 30, 40)
PANEL = (45, 45, 60)
RESALTADO = (255, 215, 0)

DADO_TAM = 70
DADO_Y = 480
DADO_X_INICIO = 320
DADO_ESPACIO = 85

PIPS = {
    1: [(0.5, 0.5)],
    2: [(0.25, 0.25), (0.75, 0.75)],
    3: [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75)],
    4: [(0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)],
    5: [(0.25, 0.25), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), (0.75, 0.75)],
    6: [(0.25, 0.25), (0.75, 0.25), (0.25, 0.5), (0.75, 0.5), (0.25, 0.75), (0.75, 0.75)],
}

def dibujar_dado(pantalla, x, y, valor, tam, seleccionado=False, resaltado=False):
    rect = pygame.Rect(x, y, tam, tam)
    pygame.draw.rect(pantalla, (20, 20, 25), rect.move(3, 3), border_radius=10)
    color = (255, 255, 200) if seleccionado else BLANCO
    pygame.draw.rect(pantalla, color, rect, border_radius=10)
    borde = RESALTADO if resaltado else (AZUL if seleccionado else NEGRO)
    pygame.draw.rect(pantalla, borde, rect, 3, border_radius=10)
    for (px, py) in PIPS[valor]:
        cx = x + px * tam
        cy = y + py * tam
        pygame.draw.circle(pantalla, NEGRO, (int(cx), int(cy)), tam // 10)


class Boton:
    def __init__(self, x, y, w, h, texto, color, color_hover, accion, fuente):
        self.rect = pygame.Rect(x, y, w, h)
        self.texto = texto
        self.color = color
        self.color_hover = color_hover
        self.accion = accion
        self.fuente = fuente
        self.habilitado = True

    def dibujar(self, pantalla):
        mouse = pygame.mouse.get_pos()
        hover = self.rect.collidepoint(mouse) and self.habilitado
        color = self.color_hover if hover else self.color
        if not self.habilitado:
            color = (80, 80, 80)
        pygame.draw.rect(pantalla, color, self.rect, border_radius=8)
        pygame.draw.rect(pantalla, NEGRO, self.rect, 2, border_radius=8)
        txt = self.fuente.render(self.texto, True, BLANCO)
        pantalla.blit(txt, txt.get_rect(center=self.rect.center))

    def click(self, pos):
        if self.habilitado and self.rect.collidepoint(pos):
            self.accion()
            return True
        return False


class VistaCacho:

    def __init__(self, entorno):
        pygame.init()
        self.pantalla = pygame.display.set_mode((ANCHO, ALTO))
        pygame.display.set_caption("Cacho - Expectiminimax")
        self.reloj = pygame.time.Clock()
        self.entorno = entorno

        self.f_peq = pygame.font.SysFont("Arial", 14)
        self.f_med = pygame.font.SysFont("Arial", 20)
        self.f_grande = pygame.font.SysFont("Arial", 26)
        self.f_titulo = pygame.font.SysFont("Arial", 36, bold=True)

        self.dados_seleccionados = set()
        self.mensaje = "Presiona TIRAR para comenzar"
        self.mensaje_color = BLANCO
        self.esperando_categoria = False
        self.categorias_botones = []
        self.ultimo_tiempo_ia = pygame.time.get_ticks()
        self.accion_ia_mostrada = None

        self._construir_botones()

    def _construir_botones(self):
        self.btn_tirar = Boton(130, 580, 160, 55, "TIRAR", VERDE, VERDE_HOVER,
                               self._accion_tirar, self.f_med)
        self.btn_anotar = Boton(310, 580, 160, 55, "ANOTAR", AZUL, AZUL_HOVER,
                                self._accion_mostrar_categorias, self.f_med)
        self.btn_nueva = Boton(700, 580, 180, 55, "NUEVA PARTIDA", ROJO, ROJO_HOVER,
                               self._reiniciar, self.f_med)

    # ============================================================
    # ACCIONES DE LA UI → van al entorno
    # ============================================================

    def _accion_tirar(self):
        estado = self.entorno.get_estado()
        if not self.entorno.es_turno_humano():
            return
        if estado.tablero['tiradas_restantes'] <= 0:
            self.mensaje = "No te quedan tiradas."
            self.mensaje_color = ROJO
            return
        indices = set(self.dados_seleccionados) if self.dados_seleccionados else set(range(5))
        self.entorno.accion_humano(('tirar', frozenset(indices)))
        self.dados_seleccionados.clear()
        self.mensaje = f"Tirando {len(indices)} dado(s)..."
        self.mensaje_color = AMARILLO

    def _accion_mostrar_categorias(self):
        if not self.entorno.es_turno_humano():
            return
        self.esperando_categoria = True
        self._construir_botones_categorias()

    def _construir_botones_categorias(self):
        self.categorias_botones = []
        estado = self.entorno.get_estado()
        disponibles = [c for c in CATEGORIAS if c not in estado.tablero['usadas'][1]]
        x0, y0 = 620, 60
        w, h = 340, 42
        for i, cat in enumerate(disponibles):
            pts = puntuar(cat, estado.tablero['dados'])
            texto = f"{NOMBRES_CAT[cat]}: {pts} pts"
            btn = Boton(x0, y0 + i * 48, w, h, texto, AZUL, AZUL_HOVER,
                        lambda c=cat: self._anotar(c), self.f_peq)
            self.categorias_botones.append(btn)

    def _anotar(self, categoria):
        self.entorno.accion_humano(('anotar', categoria))
        self.esperando_categoria = False
        self.categorias_botones = []
        self.mensaje = f"Anotaste en {NOMBRES_CAT[categoria]}"
        self.mensaje_color = VERDE

    def _reiniciar(self):
        self.entorno.juegoActual = self.entorno._estado_inicial()
        for a in self.entorno.get_agentes():
            a.habilitar()
        self.dados_seleccionados.clear()
        self.mensaje = "Nueva partida"
        self.mensaje_color = BLANCO
        self.esperando_categoria = False

    # ============================================================
    # DIBUJO
    # ============================================================

    def dibujar(self):
        self.pantalla.fill(FONDO)
        estado = self.entorno.get_estado()
        tablero = estado.tablero

        titulo = self.f_titulo.render("🎲 CACHO - Expectiminimax", True, BLANCO)
        self.pantalla.blit(titulo, (30, 20))

        ronda = min(tablero['ronda'] + 1, 10)
        ronda_txt = self.f_med.render(f"Ronda {ronda}/10", True, AMARILLO)
        self.pantalla.blit(ronda_txt, (30, 70))

        self._dibujar_puntajes(estado)
        self._dibujar_tablero(estado)
        self._dibujar_dados(estado)
        self._dibujar_mensaje()

        self.btn_tirar.dibujar(self.pantalla)
        self.btn_anotar.dibujar(self.pantalla)
        self.btn_nueva.dibujar(self.pantalla)

        es_humano = self.entorno.es_turno_humano() and not self.entorno.es_fin()
        self.btn_tirar.habilitado = es_humano and tablero['tiradas_restantes'] > 0
        self.btn_anotar.habilitado = es_humano

        if self.esperando_categoria:
            self._dibujar_panel_categorias()

        if self.entorno.es_fin():
            self._dibujar_final(estado)

    def _dibujar_puntajes(self, estado):
        panel = pygame.Rect(30, 120, 250, 130)
        pygame.draw.rect(self.pantalla, PANEL, panel, border_radius=10)
        pygame.draw.rect(self.pantalla, GRIS_CLARO, panel, 2, border_radius=10)
        p = estado.tablero['puntajes']
        ia = self.f_med.render(f"🤖 IA: {p[0]}", True, BLANCO)
        hu = self.f_med.render(f"👤 Tú: {p[1]}", True, BLANCO)
        self.pantalla.blit(ia, (50, 140))
        self.pantalla.blit(hu, (50, 185))
        turno = "IA" if estado.jugador == 0 else "Tú"
        t = self.f_peq.render(f"Turno: {turno}", True, AMARILLO)
        self.pantalla.blit(t, (50, 220))

    def _dibujar_tablero(self, estado):
        panel = pygame.Rect(30, 270, 550, 190)
        pygame.draw.rect(self.pantalla, PANEL, panel, border_radius=10)
        pygame.draw.rect(self.pantalla, GRIS_CLARO, panel, 2, border_radius=10)

        for txt, x in [("Categoría", 50), ("IA", 300), ("Tú", 400)]:
            self.pantalla.blit(self.f_peq.render(txt, True, AMARILLO), (x, 280))

        for i, cat in enumerate(CATEGORIAS):
            y = 305 + i * 15
            self.pantalla.blit(self.f_peq.render(NOMBRES_CAT[cat], True, BLANCO), (50, y))
            m_ia = "✓" if cat in estado.tablero['usadas'][0] else "-"
            m_hu = "✓" if cat in estado.tablero['usadas'][1] else "-"
            c_ia = VERDE if cat in estado.tablero['usadas'][0] else GRIS_CLARO
            c_hu = VERDE if cat in estado.tablero['usadas'][1] else GRIS_CLARO
            self.pantalla.blit(self.f_peq.render(m_ia, True, c_ia), (305, y))
            self.pantalla.blit(self.f_peq.render(m_hu, True, c_hu), (405, y))

    def _dibujar_dados(self, estado):
        seleccionables = (self.entorno.es_turno_humano()
                          and estado.tablero['tiradas_restantes'] > 0
                          and not self.entorno.es_fin())
        for i, valor in enumerate(estado.tablero['dados']):
            x = DADO_X_INICIO + i * DADO_ESPACIO
            y = DADO_Y
            sel = i in self.dados_seleccionados
            res = seleccionables and not self.dados_seleccionados
            dibujar_dado(self.pantalla, x, y, valor, DADO_TAM, sel, res)

        if seleccionables:
            txt = ("Click en dados para seleccionar cuáles tirar"
                   if not self.dados_seleccionados
                   else f"{len(self.dados_seleccionados)} seleccionado(s)")
            color = GRIS_CLARO if not self.dados_seleccionados else AZUL
            self.pantalla.blit(self.f_peq.render(txt, True, color), (250, 440))

    def _dibujar_mensaje(self):
        panel = pygame.Rect(30, 620, 940, 50)
        pygame.draw.rect(self.pantalla, PANEL, panel, border_radius=10)
        pygame.draw.rect(self.pantalla, GRIS_CLARO, panel, 2, border_radius=10)
        txt = self.f_med.render(self.mensaje, True, self.mensaje_color)
        self.pantalla.blit(txt, txt.get_rect(center=panel.center))

    def _dibujar_panel_categorias(self):
        overlay = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.pantalla.blit(overlay, (0, 0))
        panel = pygame.Rect(600, 30, 380, 640)
        pygame.draw.rect(self.pantalla, PANEL, panel, border_radius=10)
        pygame.draw.rect(self.pantalla, AMARILLO, panel, 3, border_radius=10)
        self.pantalla.blit(self.f_med.render("¿Dónde anotar?", True, AMARILLO), (620, 40))
        for btn in self.categorias_botones:
            btn.dibujar(self.pantalla)

    def _dibujar_final(self, estado):
        overlay = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.pantalla.blit(overlay, (0, 0))
        panel = pygame.Rect(250, 200, 500, 300)
        pygame.draw.rect(self.pantalla, PANEL, panel, border_radius=20)
        pygame.draw.rect(self.pantalla, AMARILLO, panel, 4, border_radius=20)

        p0, p1 = estado.tablero['puntajes']
        self.pantalla.blit(self.f_titulo.render("FIN DEL JUEGO", True, AMARILLO),
                           (ANCHO // 2 - 130, 230))
        self.pantalla.blit(self.f_grande.render(f"IA: {p0}", True, BLANCO),
                           (ANCHO // 2 - 60, 320))
        self.pantalla.blit(self.f_grande.render(f"Tú: {p1}", True, BLANCO),
                           (ANCHO // 2 - 60, 370))
        if p0 > p1:
            res, color = "Gana la IA 🤖", ROJO
        elif p1 > p0:
            res, color = "¡Ganaste! 🏆", VERDE
        else:
            res, color = "Empate 🤝", AMARILLO
        self.pantalla.blit(self.f_grande.render(res, True, color),
                           (ANCHO // 2 - 100, 440))

    # ============================================================
    # EVENTOS Y LOOP
    # ============================================================

    def manejar_evento(self, evento):
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            pos = evento.pos

            if self.esperando_categoria:
                for btn in self.categorias_botones:
                    if btn.click(pos):
                        return
                return

            if self.btn_tirar.click(pos):
                return
            if self.btn_anotar.click(pos):
                return
            if self.btn_nueva.click(pos):
                return

            estado = self.entorno.get_estado()
            if (self.entorno.es_turno_humano()
                    and estado.tablero['tiradas_restantes'] > 0
                    and not self.entorno.es_fin()):
                for i in range(5):
                    x = DADO_X_INICIO + i * DADO_ESPACIO
                    rect = pygame.Rect(x, DADO_Y, DADO_TAM, DADO_TAM)
                    if rect.collidepoint(pos):
                        if i in self.dados_seleccionados:
                            self.dados_seleccionados.remove(i)
                        else:
                            self.dados_seleccionados.add(i)
                        break

    def actualizar(self):
        if self.entorno.es_fin():
            return
        # Solo la IA se auto-ejecuta
        if not self.entorno.es_turno_humano():
            ahora = pygame.time.get_ticks()
            if ahora - self.ultimo_tiempo_ia > 900:
                self.entorno.evolucionar()
                self.ultimo_tiempo_ia = ahora
                if self.entorno.historial_ia:
                    self.mensaje = self.entorno.historial_ia[-1]
                    self.mensaje_color = AMARILLO

    def loop(self):
        while True:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self.manejar_evento(evento)
            self.actualizar()
            self.dibujar()
            pygame.display.flip()
            self.reloj.tick(FPS)