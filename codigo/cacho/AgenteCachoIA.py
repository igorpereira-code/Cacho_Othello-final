from AgenteCacho import AgenteCacho, probabilidad_tirada, acciones_reservar, puntuar
from AgenteIA.AgenteJugador import ElEstado

class AgenteCachoIA(AgenteCacho):

    def __init__(self, nombre="IA", altura=1):
        AgenteCacho.__init__(self, nombre=nombre, altura=altura)

    # ============================================================
    # EXPECTIMINIMAX
    # ============================================================

    def expectiminimax(self, estado, profundidad, es_max):
        # Nodo terminal o límite
        if self.testTerminal(estado) or profundidad >= self.max_profundidad:
            return self.funcion_evaluacion(estado)

        turno = estado.jugador
        es_max_nodo = (turno == 0)  # jugador 0 = MAX

        acciones = self.jugadas(estado)

        # Separar acciones anotar / tirar
        anotar_acciones = [a for a in acciones if a[0] == 'anotar']
        tirar_acciones = [a for a in acciones if a[0] == 'tirar']

        valores = []

        # --- Anotar (nodos MAX/MIN puros) ---
        for accion in anotar_acciones:
            nuevo = self.getResultado(estado, accion)
            v = self.expectiminimax(nuevo, profundidad + 1, not es_max_nodo)
            valores.append(v)

        # --- Tirar (nodos de AZAR) ---
        for accion in tirar_acciones:
            _, indices = accion
            probas = probabilidad_tirada(estado.tablero['dados'], indices)
            ve = 0
            for nuevos_dados, p in probas.items():
                # Construir estado tras la tirada (sin cambiar turno)
                tablero = dict(estado.tablero)
                tablero['usadas'] = [set(estado.tablero['usadas'][0]),
                                     set(estado.tablero['usadas'][1])]
                tablero['puntajes'] = list(estado.tablero['puntajes'])
                tablero['dados'] = nuevos_dados
                tablero['tiradas_restantes'] = estado.tablero['tiradas_restantes'] - 1

                nuevo_estado = ElEstado(
                    jugador=turno,
                    get_utilidad=0,
                    tablero=tablero,
                    movidas=None
                )
                ve += p * self.expectiminimax(nuevo_estado, profundidad + 1, es_max_nodo)
            valores.append(ve)

        if not valores:
            return self.funcion_evaluacion(estado)

        return max(valores) if es_max_nodo else min(valores)

    # ============================================================
    # SELECCIÓN DE ACCIÓN
    # ============================================================

    def elegir_accion(self, estado):
        """Devuelve la mejor acción ('anotar', cat) o ('tirar', indices)."""
        turno = estado.jugador
        es_max_nodo = (turno == 0)
        mejor_valor = float('-inf') if es_max_nodo else float('inf')
        mejor_accion = None

        acciones = self.jugadas(estado)

        for accion in acciones:
            if accion[0] == 'anotar':
                nuevo = self.getResultado(estado, accion)
                v = self.expectiminimax(nuevo, 1, not es_max_nodo)
            else:
                _, indices = accion
                probas = probabilidad_tirada(estado.tablero['dados'], indices)
                v = 0
                for nuevos_dados, p in probas.items():
                    tablero = dict(estado.tablero)
                    tablero['usadas'] = [set(estado.tablero['usadas'][0]),
                                         set(estado.tablero['usadas'][1])]
                    tablero['puntajes'] = list(estado.tablero['puntajes'])
                    tablero['dados'] = nuevos_dados
                    tablero['tiradas_restantes'] = estado.tablero['tiradas_restantes'] - 1
                    nuevo = ElEstado(jugador=turno, get_utilidad=0,
                                     tablero=tablero, movidas=None)
                    v += p * self.expectiminimax(nuevo, 1, es_max_nodo)

            if (es_max_nodo and v > mejor_valor) or (not es_max_nodo and v < mejor_valor):
                mejor_valor = v
                mejor_accion = accion
        # 🔒 Si no quedan tiradas, forzar anotar con la mejor categoría inmediata
        if estado.tablero['tiradas_restantes'] == 0:
            candidatas = [a for a in acciones if a[0] == 'anotar']
            if candidatas:
                return max(candidatas,
                           key=lambda a: puntuar(a[1], estado.tablero['dados']))
        if mejor_accion and mejor_accion[0] == 'tirar':
            candidatas = [a for a in acciones if a[0] == 'anotar']
            if candidatas:
                mejor_anotar = max(candidatas,
                                   key=lambda a: puntuar(a[1], estado.tablero['dados']))
                pts = puntuar(mejor_anotar[1], estado.tablero['dados'])
                if pts >= 20:  # umbral: ajusta según qué tan agresiva quieras la IA
                    mejor_accion = mejor_anotar
        return mejor_accion

    # ============================================================
    # PROGRAMA (llamado por el entorno)
    # ============================================================

    def programa(self):
        # Limpiar acciones previas
        self.set_acciones([])

        accion = self.elegir_accion(self.estado)
        if accion is not None:
            self.set_acciones(accion)