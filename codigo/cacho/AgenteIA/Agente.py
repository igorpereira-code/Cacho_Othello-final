# *************************************************************
# * Clase: Agente                                             *
# * Autor: Victor Estevez                                     *
# * Version: v2023.03.29                                      *
# * Descripcion: Implementacion de agente, percibe de su      *
# *              entorno, mapea las percepciones y modifica   *
# *              su entorno para resolucion de problema       *
# *************************************************************


class Agente:

    def __init__(self):
        self.__percepciones = None
        self.__acciones = []
        self.__habilitado = True

    def set_percepciones(self, p):
        self.__percepciones = p

    def get_percepciones(self):
        return self.__percepciones

    def get_acciones(self):
        return self.__acciones

    def set_acciones(self, a):
        self.__acciones = a

    def inhabilitar(self):
        self.__habilitado = False

    def habilitar(self):
        self.__habilitado = True

    def esta_habilitado(self):
        return self.__habilitado

    def programa(self):
        raise Exception("No existe implementacion")
