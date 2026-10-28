from AgenteCacho import AgenteCacho

class AgenteCachoHumano(AgenteCacho):

    def __init__(self, nombre="Humano", altura=1):
        AgenteCacho.__init__(self, nombre=nombre, altura=altura)
        self.accion_pendiente = None
        self.esperando = False

    def set_accion_pendiente(self, accion):
        self.accion_pendiente = accion
        self.esperando = False

    def programa(self):
        # Siempre limpia primero
        self.set_acciones([])

        if self.accion_pendiente is not None:
            self.set_acciones(self.accion_pendiente)
            self.accion_pendiente = None
        else:
            self.esperando = True