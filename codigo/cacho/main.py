from EntornoCacho import EntornoCacho
from AgenteCachoIA import AgenteCachoIA
from AgenteCachoHumano import AgenteCachoHumano
from VistaCacho import VistaCacho
from agente_ia import AgenteCachoIAMejorada


if __name__ == "__main__":
    opcion = input("¿Contra que IA queres jugar? 1 = base (docente), 2 = mejorada [2]: ").strip()

    entorno = EntornoCacho()

    if opcion == "1":
        ia = AgenteCachoIA(nombre="IA", altura=1)
    else:
        ia = AgenteCachoIAMejorada(nombre="IA mejorada", altura=1)
    humano = AgenteCachoHumano(nombre="Tú")

    entorno.insertar(ia)
    entorno.insertar(humano)

    vista = VistaCacho(entorno)
    vista.loop()
