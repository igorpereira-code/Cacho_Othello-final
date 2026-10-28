# agente_ia.py
# Desarrollado con asistencia de IA generativa (Claude, Anthropic, 2026). Ver README.md.
# IA del Cacho mejorada, construida SOBRE la IA del docente (AgenteCachoIA).
#
# Se mantiene la misma estructura: expectiminimax con nodos MAX/MIN para anotar
# y nodos de AZAR para tirar, y elegir_accion que prueba cada accion de la raiz.
# Cada cambio respecto al codigo del docente esta marcado con "CAMBIO".
#
#   CAMBIO 1  funcion de evaluacion nueva (funcion_evaluacion.py)
#   CAMBIO 2  el nodo MAX es el jugador que decide, no siempre el jugador 0
#   CAMBIO 3  poda: solo se consideran las formas de tirar que sirven para
#             alguna categoria libre (y nunca dos que guarden los mismos dados)
#   CAMBIO 4  memoizacion: un estado ya calculado no se vuelve a calcular
#   CAMBIO 5  profundidad adaptativa: si las dos mejores acciones estan muy
#             parejas, se vuelve a buscar con un nivel mas
#   CAMBIO 6  al anotar, el turno del rival empieza con dados nuevos (dados=None)
#             en vez de los dados ficticios (1,1,1,1,1); ahi se corta la busqueda
#   CAMBIO 7  sin los parches de la base (umbral de 20 puntos): la funcion ya
#             sabe que al final del turno hay que anotar
#   CAMBIO 8  eficiencia: las probabilidades de cada tirada y la lista de formas
#             de tirar dependen solo de los dados, asi que se calculan una vez y
#             se guardan (cache); tampoco se arma la lista de jugadas del estado
#             siguiente, que el codigo del docente calculaba y nadie usaba.
#             Las decisiones son exactamente las mismas, solo mas rapido.

import time
from functools import lru_cache

from AgenteCachoIA import AgenteCachoIA
from AgenteCacho import probabilidad_tirada, acciones_reservar, puntuar
from AgenteIA.AgenteJugador import ElEstado
import funcion_evaluacion as fe


# ------------------------------------------------------------
# CAMBIO 8: calculos que dependen solo de los dados (se hacen una vez)
# ------------------------------------------------------------
@lru_cache(maxsize=None)
def probas_de_tirar(dados, indices):
    """Resultados posibles (dados, probabilidad) al tirar los dados en 'indices'."""
    return tuple(probabilidad_tirada(dados, indices).items())


@lru_cache(maxsize=None)
def formas_de_tirar(dados):
    """Todas las acciones ('tirar', indices) posibles con estos dados (mismo orden que el docente)."""
    return tuple(('tirar', tirar) for _, tirar in acciones_reservar(dados) if tirar)


class AgenteCachoIAMejorada(AgenteCachoIA):

    def __init__(self, nombre="IA mejorada", altura=1,
                 usar_poda=True, usar_memo=True, profundidad_adaptativa=True,
                 umbral_critico=1.0, w1=fe.W1, w2=fe.W2, w3_por_etapa=None):
        AgenteCachoIA.__init__(self, nombre=nombre, altura=altura)
        self.altura_base = altura
        self.usar_poda = usar_poda
        self.usar_memo = usar_memo
        self.profundidad_adaptativa = profundidad_adaptativa
        self.umbral_critico = umbral_critico     # puntos: "parejas" si difieren menos que esto
        self.w1, self.w2 = w1, w2
        self.w3_por_etapa = w3_por_etapa if w3_por_etapa is not None else dict(fe.W3_POR_ETAPA)
        # metricas por decision
        self.tiempos = []
        self.evaluaciones = []        # veces que se pidio evaluar un estado
        self.calculos = []            # veces que de verdad se calculo (sin memo)
        self.profundidades = []
        self._memo_eval = {}
        self._memo_arbol = {}
        self._n_eval = 0
        self._n_calc = 0

    # ------------------------------------------------------------
    # CAMBIO 1 y 4: funcion de evaluacion nueva, con memoizacion
    # ------------------------------------------------------------
    @staticmethod
    def clave(estado):
        t = estado.tablero
        return (estado.jugador, t['dados'], t['tiradas_restantes'], t.get('ronda', 0),
                tuple(t['puntajes']), frozenset(t['usadas'][0]), frozenset(t['usadas'][1]))

    def funcion_evaluacion(self, estado):
        self._n_eval += 1
        raiz = self.estado.jugador
        if self.usar_memo:
            k = (self.clave(estado), raiz)
            if k in self._memo_eval:
                return self._memo_eval[k]
        self._n_calc += 1
        v = fe.evaluar(estado, raiz, self.w1, self.w2, self.w3_por_etapa)
        if self.usar_memo:
            self._memo_eval[k] = v
        return v

    # ------------------------------------------------------------
    # CAMBIO 6: anotar deja al rival con un turno nuevo (dados sin tirar)
    # CAMBIO 8: no se arma la lista de jugadas del estado siguiente
    # ------------------------------------------------------------
    def getResultado(self, estado, m):
        t = estado.tablero
        tablero = self._copiar_tablero(t)
        tipo, param = m
        turno = estado.jugador
        if tipo == 'anotar':
            tablero['puntajes'][turno] += puntuar(param, tablero['dados'])
            tablero['usadas'][turno].add(param)
            tablero['dados'] = None                      # CAMBIO 6
            tablero['tiradas_restantes'] = 3
            tablero['ronda'] = t.get('ronda', 0) + 1
        else:
            tablero['tiradas_restantes'] -= 1
        return ElEstado(jugador=1 - turno, get_utilidad=0, tablero=tablero, movidas=None)

    # ------------------------------------------------------------
    # Acciones de anotar y de tirar (con CAMBIO 3: poda de las de tirar)
    # ------------------------------------------------------------
    def acciones_anotar(self, estado):
        usadas = estado.tablero['usadas'][estado.jugador]
        return [('anotar', c) for c in fe.CATEGORIAS if c not in usadas]

    def acciones_tirar(self, estado):
        t = estado.tablero
        if t['tiradas_restantes'] <= 0:
            return []
        dados = t['dados']
        acciones = formas_de_tirar(dados)                # CAMBIO 8
        if not self.usar_poda or not acciones:
            return list(acciones)
        r = t['tiradas_restantes']
        libres = [c for c in fe.CATEGORIAS if c not in t['usadas'][estado.jugador]]
        # dados que conviene guardar segun cada categoria libre (tablas de funcion_evaluacion)
        utiles = {fe.MEJOR_GUARDAR[c][r][dados] for c in libres}
        elegidas, vistos = [], set()
        for accion in acciones:
            guardados = tuple(dados[i] for i in range(5) if i not in accion[1])
            if guardados in utiles and guardados not in vistos:
                vistos.add(guardados)
                elegidas.append(accion)
        return elegidas

    # ============================================================
    # EXPECTIMINIMAX (estructura del docente)
    # ============================================================

    def expectiminimax(self, estado, profundidad, es_max):
        # Nodo terminal o limite
        if self.testTerminal(estado) or profundidad >= self.max_profundidad:
            return self.funcion_evaluacion(estado)
        # CAMBIO 6: empieza el turno del rival con dados al azar -> se corta aqui
        if estado.tablero['dados'] is None:
            return self.funcion_evaluacion(estado)

        # CAMBIO 4: memoizacion de estados del arbol
        if self.usar_memo:
            k = (self.clave(estado), profundidad, self.max_profundidad)
            if k in self._memo_arbol:
                return self._memo_arbol[k]

        turno = estado.jugador
        es_max_nodo = (turno == self.estado.jugador)  # CAMBIO 2 (antes: turno == 0)

        anotar_acciones = self.acciones_anotar(estado)
        tirar_acciones = self.acciones_tirar(estado)   # CAMBIO 3

        valores = []

        # --- Anotar (nodos MAX/MIN puros) ---
        for accion in anotar_acciones:
            nuevo = self.getResultado(estado, accion)
            v = self.expectiminimax(nuevo, profundidad + 1, not es_max_nodo)
            valores.append(v)

        # --- Tirar (nodos de AZAR) ---
        for accion in tirar_acciones:
            _, indices = accion
            ve = 0
            for nuevos_dados, p in probas_de_tirar(estado.tablero['dados'], indices):
                ve += p * self.expectiminimax(self.estado_tras_tirar(estado, nuevos_dados),
                                              profundidad + 1, es_max_nodo)
            valores.append(ve)

        if not valores:
            resultado = self.funcion_evaluacion(estado)
        else:
            resultado = max(valores) if es_max_nodo else min(valores)

        if self.usar_memo:
            self._memo_arbol[k] = resultado
        return resultado

    def estado_tras_tirar(self, estado, nuevos_dados):
        """Igual que en el codigo del docente: misma persona, una tirada menos."""
        tablero = dict(estado.tablero)
        tablero['usadas'] = [set(estado.tablero['usadas'][0]),
                             set(estado.tablero['usadas'][1])]
        tablero['puntajes'] = list(estado.tablero['puntajes'])
        tablero['dados'] = nuevos_dados
        tablero['tiradas_restantes'] = estado.tablero['tiradas_restantes'] - 1
        return ElEstado(jugador=estado.jugador, get_utilidad=0, tablero=tablero, movidas=None)

    # ============================================================
    # SELECCION DE ACCION (estructura del docente)
    # ============================================================

    def valorar_acciones(self, estado):
        """Valor de cada accion de la raiz con la altura actual (self.max_profundidad)."""
        es_max_nodo = True  # CAMBIO 2: en la raiz siempre decide el agente
        resultado = []
        acciones = self.acciones_anotar(estado) + self.acciones_tirar(estado)
        for accion in acciones:
            if accion[0] == 'anotar':
                nuevo = self.getResultado(estado, accion)
                v = self.expectiminimax(nuevo, 1, not es_max_nodo)
            else:
                _, indices = accion
                v = 0
                for nuevos_dados, p in probas_de_tirar(estado.tablero['dados'], indices):
                    v += p * self.expectiminimax(self.estado_tras_tirar(estado, nuevos_dados),
                                                 1, es_max_nodo)
            resultado.append((v, accion))
        resultado.sort(key=lambda x: x[0], reverse=True)
        return resultado

    def elegir_accion(self, estado):
        """Devuelve la mejor accion ('anotar', cat) o ('tirar', indices)."""
        self.max_profundidad = self.altura_base
        self._memo_arbol = {}
        valores = self.valorar_acciones(estado)
        profundidad_usada = self.altura_base

        # CAMBIO 5: profundidad adaptativa en decisiones criticas
        if (self.profundidad_adaptativa and len(valores) > 1
                and estado.tablero['tiradas_restantes'] > 0
                and valores[0][0] - valores[1][0] < self.umbral_critico):
            self.max_profundidad = self.altura_base + 1
            self._memo_arbol = {}
            valores = self.valorar_acciones(estado)
            profundidad_usada = self.max_profundidad

        self.profundidades.append(profundidad_usada)
        return valores[0][1] if valores else None
        # CAMBIO 7: ya no hace falta forzar anotar ni el umbral de 20 puntos

    # ============================================================
    # PROGRAMA (llamado por el entorno)
    # ============================================================

    def programa(self):
        self.set_acciones([])
        if len(self._memo_eval) > 200000:   # para que la memoria no crezca sin limite
            self._memo_eval = {}
        self._n_eval = 0
        self._n_calc = 0
        inicio = time.perf_counter()
        accion = self.elegir_accion(self.estado)
        self.tiempos.append(time.perf_counter() - inicio)
        self.evaluaciones.append(self._n_eval)
        self.calculos.append(self._n_calc)
        if accion is not None:
            self.set_acciones(accion)
