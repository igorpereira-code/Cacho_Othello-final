from AgenteIA.Entorno import Entorno
from AgenteIA.AgenteJugador import ElEstado
from AgenteCacho import normalizar, puntuar
from AgenteCachoHumano import AgenteCachoHumano
import random


class EntornoCacho(Entorno):
    """
    Entorno del Cacho que coordina los turnos entre IA y humano.

    Convención:
      - jugador 0 → IA (MAX en Expectiminimax)
      - jugador 1 → humano (MIN)
    """

    def __init__(self):
        Entorno.__init__(self)
        self.juegoActual = self._estado_inicial()
        self.historial_ia = []       # log visible de acciones de la IA
        self.log_completo = []       # log técnico de todas las acciones

    def _estado_inicial(self):
        tablero = {
            # CORRECCION: antes era (1, 1, 1, 1, 1) sin tirar, que ya cuenta como
            # "grande": el primer jugador se llevaba 50 puntos gratis. Ahora el primer
            # turno empieza con una tirada real, igual que todos los demas turnos.
            'dados': self._tirar_5(),
            'tiradas_restantes': 3,
            'puntajes': [0, 0],
            'usadas': [set(), set()],
            'ronda': 0,
        }
        return ElEstado(jugador=0, get_utilidad=0, tablero=tablero, movidas=None)

    # ============================================================
    # PERCEPCIONES
    # ============================================================

    def get_percepciones(self, agente):
        agente.estado = self.juegoActual

    # ============================================================
    # VALIDACIÓN Y EJECUCIÓN
    # ============================================================

    @staticmethod
    def _accion_valida(accion):
        return (isinstance(accion, tuple)
                and len(accion) == 2
                and accion[0] in ('tirar', 'anotar'))

    def ejecutar(self, agente):
        accion = agente.get_acciones()
        if not self._accion_valida(accion):
            return
        self._aplicar_accion(accion)

    # ============================================================
    # EVOLUCIONAR (solo turno IA)
    # ============================================================

    def evolucionar(self):
        """Un paso del juego: solo actúa si es turno de la IA."""
        if self.finalizar():
            return
        turno = self.juegoActual.jugador
        if turno != 0:
            return  # el humano se controla desde la vista
        agente = self.get_agentes()[turno]
        self.get_percepciones(agente)
        agente.programa()
        self.ejecutar(agente)

    # ============================================================
    # API HUMANA (aplica directo, sin pasar por evolucionar)
    # ============================================================

    def accion_humano(self, accion):
        if self.juegoActual.jugador != 1:
            return
        if not self._accion_valida(accion):
            return
        self._aplicar_accion(accion)

    # ============================================================
    # APLICAR ACCIONES
    # ============================================================

    def _aplicar_accion(self, accion):
        tipo, param = accion
        tablero = self.juegoActual.tablero
        turno = self.juegoActual.jugador
        dados_antes = tablero['dados']
        nombre = "IA" if turno == 0 else "HUMANO"

        # -------- TIRAR --------
        if tipo == 'tirar':
            indices = param
            dados = list(dados_antes)
            for i in indices:
                dados[i] = random.randint(1, 6)
            nuevos = normalizar(dados)

            if turno == 0:
                mantiene = [dados_antes[i] for i in range(5) if i not in indices]
                msg = (f"IA tiró {len(indices)} dado(s) "
                       f"→ {nuevos}")
                self.historial_ia.append(msg)
                print(f"\n[IA] Tira índices {sorted(indices)}")
                print(f"     Mantiene: {mantiene if mantiene else '(ninguno)'}")
                print(f"     Antes:    {dados_antes}")
                print(f"     Después:  {nuevos}")
                print(f"     Tiradas restantes: {tablero['tiradas_restantes'] - 1}")
            else:
                print(f"\n[HUMANO] Tira índices {sorted(indices)} → {nuevos}")

            tablero['dados'] = nuevos
            tablero['tiradas_restantes'] -= 1

            self.log_completo.append({
                'ronda': tablero['ronda'], 'turno': turno,
                'tipo': 'tirar', 'detalle': (sorted(indices), nuevos),
                'puntajes': list(tablero['puntajes'])
            })
            self.get_agentes()[turno].set_acciones([])
            return  # ⚠️ NO cambia turno: mismo jugador sigue

        # -------- ANOTAR --------
        if tipo == 'anotar':
            cat = param
            pts = puntuar(cat, tablero['dados'])

            if turno == 0:
                msg = f"IA anotó en '{cat}' → +{pts} pts"
                self.historial_ia.append(msg)
                print(f"\n[IA] ANOTA en '{cat}' con dados {dados_antes}")
                print(f"     → +{pts} pts | Total IA: {tablero['puntajes'][turno] + pts}")
            else:
                print(f"\n[HUMANO] ANOTA en '{cat}' con dados {dados_antes}")
                print(f"     → +{pts} pts | Total humano: {tablero['puntajes'][turno] + pts}")

            tablero['puntajes'][turno] += pts
            tablero['usadas'][turno].add(cat)
            tablero['ronda'] += 1

            self.log_completo.append({
                'ronda': tablero['ronda'] - 1, 'turno': turno,
                'tipo': 'anotar', 'detalle': (cat, pts),
                'puntajes': list(tablero['puntajes'])
            })
            self.get_agentes()[turno].set_acciones([])

            # ¿Fin del juego?
            if tablero['ronda'] >= 10:
                for a in self.get_agentes():
                    a.inhabilitar()
                print("\n=== FIN DEL JUEGO ===")
                print(f"IA:     {tablero['puntajes'][0]} pts")
                print(f"Humano: {tablero['puntajes'][1]} pts")
                return

            # 🔑 CAMBIO DE TURNO EXPLÍCITO
            nuevo_jugador = 1 if turno == 0 else 0
            tablero['dados'] = self._tirar_5()
            tablero['tiradas_restantes'] = 3

            print(f"[TURNO] Cambia de {nombre} a "
                  f"{'HUMANO' if nuevo_jugador == 1 else 'IA'}")

            self.juegoActual = ElEstado(
                jugador=nuevo_jugador,
                get_utilidad=0,
                tablero=tablero,
                movidas=None
            )

    def _tirar_5(self):
        return normalizar([random.randint(1, 6) for _ in range(5)])

    # ============================================================
    # CONSULTAS
    # ============================================================

    def get_estado(self):
        return self.juegoActual

    def es_turno_humano(self):
        return self.juegoActual.jugador == 1

    def es_fin(self):
        return self.juegoActual.tablero['ronda'] >= 10