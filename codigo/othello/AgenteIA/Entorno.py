# ******************************************************************
# * Clase: Entorno                                                 *
# * Autor: Victor Estevez                                          *
# * Version: v2023.03.29                                           *
# * Descripcion: Implementacion del entorno, proporciona           *
# *              percepciones a los agentes y ejecuta las acciones *
# *              de cada agente  que se encuentra en el            *
# ******************************************************************


class Entorno:

    def __init__(self):
        self.__agentes = []

    def get_percepciones(self, agente):
        raise Exception("No existe implementacion")

    def get_agentes(self):
        return self.__agentes

    def ejecutar(self, agente):
        raise Exception("No existe implementacion")

    def evolucionar(self):
        if not self.finalizar():
            for agente in self.__agentes:
                self.get_percepciones(agente)
                self.ejecutar(agente)

    def run(self):
        while True:
            if self.finalizar():
                break
            self.evolucionar()

    def finalizar(self):
        return any(not agente.esta_habilitado() for agente in self.__agentes)

    def insertar(self, agente):
        self.__agentes.append(agente)
