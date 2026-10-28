@echo off
REM Corre todos los experimentos de la practica y deja los CSV en ..\datos
REM y las figuras en ..\articulo\figuras.
REM Tiempo total aproximado: 2 a 3 horas (depende de la computadora).
REM Se puede cerrar y volver a correr: cada paso sobreescribe su propio CSV.

set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

echo === Instalando librerias (numpy, pygame, matplotlib) ===
py -3.13 -m pip install -r requirements.txt

echo.
echo ================= OTHELLO =================
cd /d "%~dp0othello"

echo [1/9] Torneo V0 vs V1 vs V2 (300 partidas, ~10 min)
py -3.13 torneo.py --agentes V0:4 V1:4 V2:4 --aperturas 50 --salida ..\..\datos\resultados_othello.csv > ..\..\datos\log_torneo_othello.txt

echo [2/9] Correlacion funcion vs resultado final (100 partidas, ~3 min)
py -3.13 correlacion.py --evaluador V2 --altura 4 --partidas 100 --plies 6 --salida ..\..\datos\datos_correlacion.csv > ..\..\datos\log_correlacion.txt

echo [3/9] Tiempo vs profundidad 4-7 (~8 min)
py -3.13 escalabilidad.py --alturas 4 5 6 7 --partidas 4 --plies 6 --salida ..\..\datos\datos_escalabilidad.csv > ..\..\datos\log_escalabilidad.txt

echo [4/9] Victorias vs profundidad 4-7 (~30 min)
py -3.13 profundidad.py --alturas 4 5 6 7 --aperturas 20 --salida ..\..\datos\victorias_profundidad.csv > ..\..\datos\log_profundidad.txt

echo.
echo ================= CACHO =================
cd /d "%~dp0cacho"

echo [5/9] Pruebas de la funcion de evaluacion
py -3.13 pruebas_funcion.py > ..\..\datos\log_pruebas_cacho.txt

echo [6/9] Ajuste de w2 (4800 partidas, ~15 min)
py -3.13 torneo_cacho.py torneo --agentes w2_06 w2_08 mejorada w2_12 --semillas 400 --sin-adaptativa --salida ..\..\datos\ajuste_w2.csv > ..\..\datos\log_ajuste_w2.txt

echo [7/9] Ajuste de w3 (6000 partidas, ~20 min)
py -3.13 torneo_cacho.py torneo --agentes sin_varianza mejorada varianza_alta --semillas 1000 --sin-adaptativa --salida ..\..\datos\ajuste_w3.csv > ..\..\datos\log_ajuste_w3.txt

echo [8/9] Profundidad adaptativa (600 partidas, ~15 min)
py -3.13 torneo_cacho.py torneo --agentes mejorada sin_adaptativa --semillas 300 --salida ..\..\datos\ajuste_adaptativa.csv > ..\..\datos\log_ajuste_adaptativa.txt

echo [9/9] Torneo base vs mejorada + eficiencia + decisiones (~10 min)
py -3.13 torneo_cacho.py torneo --agentes base mejorada --semillas 100 --salida ..\..\datos\resultados_cacho.csv > ..\..\datos\log_torneo_cacho.txt
py -3.13 torneo_cacho.py eficiencia --estados 200 --estados-prof2 20 --salida ..\..\datos\eficiencia_cacho.csv > ..\..\datos\log_eficiencia_cacho.txt
py -3.13 torneo_cacho.py decisiones --estados 300 --ejemplos 10 --salida ..\..\datos\decisiones_cacho.csv > ..\..\datos\log_decisiones_cacho.txt

echo.
echo ================= FIGURAS =================
cd /d "%~dp0"
py -3.13 graficos.py

echo.
echo Listo. Resultados en ..\datos (los log_*.txt tienen las tablas y la estadistica)
echo y figuras en ..\articulo\figuras.
pause
