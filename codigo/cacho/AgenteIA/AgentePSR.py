#################################################################
# Nombre      : Agente PSR                                      #
# Version     : 0.05.03.2017                                    #
# Autor       : Victor                                          #
# Descripcion : Clase especificacion de Agente, implementa      #
#               algoritmos Backtrack para PSR                   #
#################################################################

from AgenteIA.Agente import Agente

class AgentePSR(Agente):
    def __init__(self):
        Agente.__init__(self)
        self.__variables = None
        self.__dominio = None
        self.__vecinos = None

    def setVariables(self, variables):
        self.__variables = variables

    def get_variables(self):
        return self.__variables

    def setDominio(self, dominio):
        self.__dominio = dominio

    def get_dominio(self):
        return self.__dominio

    def setVecinos(self, vecinos):
        self.__vecinos = vecinos

    def get_vecinos(self):
        return self.__vecinos

    def asignar(self, variable, val, asignacion):
        raise Exception("Error: No existe implementacion")

    def desasignar(self, variable, asignacion):
        raise Exception("Error: No existe implementacion")

    def seleccionarVariableNoAsignada(self, asignacion):
        return ([var for var in self.get_variables() if var not in asignacion])[0]

    def getConflictos(self, var, val, assignment):
        raise Exception("Error: No existe implementacion")

    def getDominio(self):
        return self.__dominio

    def esCompleto(self, asignacion):
        raise Exception("Error: No existe implementacion")

    def programa(self):

        def backtrack(asignacion):
            if self.esCompleto(asignacion):
                return asignacion
            vari = self.seleccionarVariableNoAsignada(asignacion)

            for valor in self.getDominio():
                if self.getConflictos(vari, valor, asignacion) == 0 :
                    self.asignar(vari, valor, asignacion)
                    resultado = backtrack(asignacion)
                    if resultado is not None:
                        return resultado

            self.desasignar(vari, asignacion)
            return None

        self.set_acciones(backtrack({}))


