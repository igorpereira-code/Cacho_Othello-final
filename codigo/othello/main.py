# main.py
# Partida Humano (consola) vs IA usando el entorno TableroOthello.
#   python main.py

from AgenteIA.AgenteJugador import AgenteJugador
from TableroOthello import TableroOthello
from agente import AgenteOthello
from evaluador import EvaluadorV2


class HumanoOthello(AgenteJugador):
    def __init__(self):
        super().__init__()
        self.nombre = "Humano"
        self.color = None

    def programa(self):
        validas = self.estado.movidas
        print(f"Jugadas validas: {validas}")
        while True:
            texto = input("Tu jugada (fila col): ").replace(",", " ").split()
            if len(texto) == 2 and all(t.isdigit() for t in texto):
                jugada = (int(texto[0]), int(texto[1]))
                if jugada in validas:
                    self.set_acciones(jugada)
                    return
            print("Jugada invalida, intenta de nuevo.")

    def getResultado(self, estado, jugada):
        # el humano usa las mismas reglas que el agente
        return AgenteOthello().getResultado(estado, jugada)


if __name__ == "__main__":
    color = input("¿Jugas con negras (1) o blancas (2)? [1]: ").strip() or "1"
    humano = HumanoOthello()
    ia = AgenteOthello(EvaluadorV2(), altura=5, nombre="IA V2")

    entorno = TableroOthello()
    if color == "2":
        entorno.insertar(ia, color=1)
        entorno.insertar(humano, color=2)
    else:
        entorno.insertar(humano, color=1)
        entorno.insertar(ia, color=2)
    entorno.run()