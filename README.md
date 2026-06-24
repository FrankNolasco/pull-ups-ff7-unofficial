# FF7R Pull-ups Bot

Bot de practica para automatizar el minijuego de pull-ups de **Final Fantasy VII Remake** en Windows.

El script aprende los primeros 4 botones de la secuencia desde tu mando real y luego reproduce esa secuencia con un mando Xbox virtual. No lee memoria del juego, no modifica archivos, no inyecta codigo y no usa hooks del proceso del juego.

## Que hace

- Captura los primeros 4 botones unicos que presionas en el mando.
- Arranca automaticamente despues de capturar la secuencia.
- Reproduce la secuencia como mando Xbox virtual.
- Usa una curva de aceleracion calibrada para el ritmo del minijuego.
- Permite recapturar una segunda fase sin cerrar el programa.
- Permite preparar o disparar manualmente el "machaque" del prompt amarillo.

## Requisitos

- Windows.
- Python 3.12 recomendado.
- Un mando compatible con pygame.
- [ViGEmBus](https://github.com/nefarius/ViGEmBus) instalado para crear el mando virtual.

## Instalacion

```powershell
cd "C:\ruta\a\FF-GYM"
py -3.12 -m pip install -r requirements.txt
```

Si no tienes Python 3.12, instalalo desde python.org. Python 3.14 puede dar problemas con pygame segun la disponibilidad de wheels.

## Uso

1. Conecta tu mando.
2. Abre el juego y entra al minijuego.
3. Ejecuta:

```powershell
py -3.12 ff7_pullups_bot.py
```

4. Cuando el programa lo pida, presiona los primeros 4 botones de la secuencia en orden.
5. El bot arranca automaticamente.

## Hotkeys

| Tecla | Accion |
| --- | --- |
| F1 | Reiniciar velocidad |
| F2 | Acelerar 10% |
| F3 | Desacelerar 10% |
| F4 | Machacar la siguiente pulsacion inmediata |
| F5 | Capturar nueva secuencia de 4 botones |
| F6 | Preparar machaque para el proximo primer boton |
| F7 | Activar/desactivar modo machaque continuo |
| F8 | Reanudar |
| F9 | Pausar |
| F10 | Detener |

Tip: para el prompt amarillo, normalmente es mas comodo presionar **F6** un poco antes. El bot esperara hasta el proximo primer boton de la secuencia y aplicara el machaque ahi.

## Ajustes principales

Los valores calibrados estan al inicio de `ff7_pullups_bot.py`:

```python
INITIAL_INTERVAL = 0.82
SPEED_MULTIPLIER_PER_PRESS = 0.975
MINIMUM_INTERVAL = 0.28
PRESS_DURATION = 0.045
BURST_REPEAT_COUNT = 6
BURST_TOTAL_DURATION = 0.50
BURST_RECOVERY_EXTRA_DELAY = 0.12
```

Si el bot se adelanta, sube `MINIMUM_INTERVAL` o usa `F3` durante la partida.
Si queda lento, baja `MINIMUM_INTERVAL` o usa `F2`.

## Notas

- `pygame` se usa para leer el mando real.
- `vgamepad` se usa para crear el mando Xbox virtual.
- `keyboard` se usa para las hotkeys globales.
- El juego debe recibir el mando virtual. Si tienes varios mandos conectados, revisa cual esta usando el juego.

## Aviso

Este proyecto es para practica, accesibilidad, experimentacion local y preservacion de conocimiento tecnico. Usalo bajo tu propio criterio y respeta las reglas de los juegos o plataformas donde lo ejecutes.
