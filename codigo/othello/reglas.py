# reglas.py
# Desarrollado con asistencia de IA generativa (Claude, Anthropic, 2026). Ver ../README.md.
# Reglas de Othello optimizadas para la busqueda.
#
# El tablero se representa como una TUPLA PLANA de 64 enteros (0 vacio,
# 1 negro, 2 blanco); la casilla (fila, col) es el indice fila*8 + col.
# Se usa tupla (no numpy) porque:
#   - acceder a un elemento de una tupla es ~10 veces mas rapido que a un np.array
#   - es inmutable y "hasheable": sirve directo como clave de la tabla de transposicion
# Los rayos (las casillas en cada una de las 8 direcciones) se calculan una sola
# vez al importar el modulo, asi el bucle interno no hace chequeos de bordes.

import numpy as np

N = 8
DIRECCIONES = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _rayos_de(i):
    fila, col = divmod(i, N)
    rayos = []
    for df, dc in DIRECCIONES:
        rayo = []
        f, c = fila + df, col + dc
        while 0 <= f < N and 0 <= c < N:
            rayo.append(f * N + c)
            f += df
            c += dc
        if len(rayo) >= 2:  # con menos de 2 casillas no se puede encerrar nada
            rayos.append(tuple(rayo))
    return tuple(rayos)


def _vecinos_de(i):
    fila, col = divmod(i, N)
    return tuple((fila + df) * N + (col + dc) for df, dc in DIRECCIONES
                 if 0 <= fila + df < N and 0 <= col + dc < N)


RAYOS = tuple(_rayos_de(i) for i in range(N * N))
VECINOS = tuple(_vecinos_de(i) for i in range(N * N))


def es_valida(tab, i, jugador):
    """True si el jugador puede poner ficha en la casilla i."""
    if tab[i]:
        return False
    oponente = 3 - jugador
    for rayo in RAYOS[i]:
        if tab[rayo[0]] != oponente:
            continue
        for k in rayo[1:]:
            v = tab[k]
            if v == oponente:
                continue
            if v == jugador:
                return True
            break
    return False


def jugadas_validas(tab, jugador):
    """Lista de indices (en orden fila por fila) donde el jugador puede jugar."""
    return [i for i in range(64) if tab[i] == 0 and es_valida(tab, i, jugador)]


def aplicar(tab, i, jugador):
    """Devuelve un tablero nuevo con la ficha puesta en i y las fichas volteadas."""
    t = list(tab)
    t[i] = jugador
    oponente = 3 - jugador
    for rayo in RAYOS[i]:
        a_voltear = []
        for k in rayo:
            v = t[k]
            if v == oponente:
                a_voltear.append(k)
            else:
                if v == jugador:
                    for f in a_voltear:
                        t[f] = jugador
                break
    return tuple(t)


def siguiente(tab, i, jugador):
    """
    Aplica la jugada y resuelve de quien es el turno, igual que getResultado:
    si el rival no tiene jugadas, vuelve a jugar el mismo. Devuelve
    (tablero, jugador_en_turno, sus_jugadas). Si sus_jugadas esta vacia,
    ninguno de los dos puede mover: el juego termino.
    """
    nuevo = aplicar(tab, i, jugador)
    rival = 3 - jugador
    movs = jugadas_validas(nuevo, rival)
    if movs:
        return nuevo, rival, movs
    return nuevo, jugador, jugadas_validas(nuevo, jugador)


# --- conversiones entre la representacion del entorno (numpy 8x8, (fila,col))
# --- y la representacion interna (tupla plana, indice) ---

def a_tupla(tablero_np):
    return tuple(np.asarray(tablero_np).ravel().tolist())


def a_numpy(tab):
    return np.array(tab, dtype=int).reshape(N, N)


def a_indice(jugada):
    return int(jugada[0]) * N + int(jugada[1])


def a_fila_col(i):
    return (i // N, i % N)


def tablero_inicial():
    t = [0] * 64
    t[27], t[36] = 2, 2   # (3,3) y (4,4) blancas
    t[28], t[35] = 1, 1   # (3,4) y (4,3) negras
    return tuple(t)