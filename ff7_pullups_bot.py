"""FF7R Pull-ups Bot.

Bot de practica para el minijuego de pull-ups de Final Fantasy VII Remake.

Instalacion:
    py -3.12 -m pip install pygame keyboard vgamepad

Tambien necesitas el driver ViGEmBus instalado para que vgamepad pueda crear
un mando Xbox virtual en Windows.

Notas:
    - No lee memoria del juego.
    - No modifica archivos del juego.
    - No inyecta codigo.
    - Captura botones del mando real con pygame.
    - Reproduce la secuencia como botones de un mando Xbox virtual.
"""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Any, Dict, List

import keyboard
import pygame

try:
    import vgamepad
except ImportError:
    vgamepad = None


# Ajustes fijos para no tener que salir del juego a configurar nada.
# El minijuego empieza lento y acelera progresivamente; un intervalo plano
# puede promediar bien, pero se siente mal dentro del juego.
INITIAL_INTERVAL = 0.82
SPEED_MULTIPLIER_PER_PRESS = 0.975
MINIMUM_INTERVAL = 0.28
PRESS_DURATION = 0.045
BURST_REPEAT_COUNT = 6
BURST_TOTAL_DURATION = 0.50
BURST_PRESS_GAP = BURST_TOTAL_DURATION / BURST_REPEAT_COUNT
BURST_RECOVERY_EXTRA_DELAY = 0.12
AUTO_BURST_EVERY_CYCLES = 5
AUTO_BURST_ENABLED_BY_DEFAULT = False
MANUAL_SPEED_FACTOR = 0.10
LEARNED_INTERVAL_MIN = 0.36
LEARNED_INTERVAL_MAX = 0.78
START_SPEED_FACTOR_AFTER_CAPTURE = 0.78


# En muchos mandos:
#   0 = A / Cross, 1 = B / Circle, 2 = X / Square, 3 = Y / Triangle
DEFAULT_BUTTON_NAMES: Dict[int, str] = {
    0: "A / Cross",
    1: "B / Circle",
    2: "X / Square",
    3: "Y / Triangle",
    4: "LB / L1",
    5: "RB / R1",
    6: "Back / Share",
    7: "Start / Options",
    8: "Left Stick",
    9: "Right Stick",
}


@dataclass
class BotConfig:
    """Valores ajustables del bucle de inputs."""

    initial_interval: float = INITIAL_INTERVAL
    speed_multiplier_per_press: float = SPEED_MULTIPLIER_PER_PRESS
    minimum_interval: float = MINIMUM_INTERVAL
    press_duration: float = PRESS_DURATION


@dataclass
class SequenceStep:
    """Un punto de la secuencia capturada."""

    button_id: int
    button_name: str


class GamepadListener:
    """Inicializa pygame y captura botones del mando real."""

    def __init__(self) -> None:
        pygame.init()
        pygame.joystick.init()
        self.joystick = self._get_first_joystick()
        self.last_learned_interval = INITIAL_INTERVAL

    def _get_first_joystick(self) -> pygame.joystick.Joystick:
        joystick_count = pygame.joystick.get_count()
        if joystick_count <= 0:
            raise RuntimeError(
                "No se detecto ningun mando. Conecta un gamepad y reinicia el programa."
            )

        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        print(f"Mando real detectado: {joystick.get_name()}")
        print(f"ID interno del mando real: {joystick.get_instance_id()}")
        return joystick

    def get_button_name(self, button_id: int) -> str:
        return DEFAULT_BUTTON_NAMES.get(button_id, f"Boton {button_id}")

    def capture_unique_sequence(self, length: int = 4) -> List[SequenceStep]:
        """Captura los primeros botones unicos presionados, en orden."""

        sequence: List[SequenceStep] = []
        seen = set()
        real_joystick_id = self.joystick.get_instance_id()
        press_times: List[float] = []

        print("\nPresiona los primeros 4 botones de la secuencia")
        print("Ni bien capture los 4, el bot arranca automatico.\n")
        pygame.event.clear()

        while len(sequence) < length:
            for event in pygame.event.get():
                if (
                    event.type == pygame.JOYBUTTONDOWN
                    and event.instance_id == real_joystick_id
                ):
                    button_id = int(event.button)
                    button_name = self.get_button_name(button_id)

                    if button_id in seen:
                        print(f"Boton repetido ignorado: {button_name}")
                        continue

                    seen.add(button_id)
                    press_times.append(time.perf_counter())
                    sequence.append(
                        SequenceStep(button_id=button_id, button_name=button_name)
                    )
                    print(f"Boton detectado #{len(sequence)}: {button_name}")

            time.sleep(0.01)

        print("\nSecuencia capturada:")
        print("[" + ", ".join(step.button_name for step in sequence) + "]")

        self.last_learned_interval = self._calculate_learned_interval(press_times)
        print(f"Intervalo aprendido: {self.last_learned_interval:.3f}s")
        return sequence

    def _calculate_learned_interval(self, press_times: List[float]) -> float:
        if len(press_times) < 2:
            return INITIAL_INTERVAL

        intervals = [
            press_times[index] - press_times[index - 1]
            for index in range(1, len(press_times))
        ]
        intervals.sort()
        learned = intervals[len(intervals) // 2]
        return min(LEARNED_INTERVAL_MAX, max(LEARNED_INTERVAL_MIN, learned))


class VirtualGamepadSender:
    """Envia botones a Windows usando un mando Xbox virtual."""

    def __init__(self, press_duration: float) -> None:
        if vgamepad is None:
            raise RuntimeError(
                "Falta vgamepad. Instala con: py -3.12 -m pip install vgamepad"
            )

        self.press_duration = press_duration
        self.gamepad = vgamepad.VX360Gamepad()
        self.button_map = self._build_button_map()
        print("Mando Xbox virtual creado.")

    def _build_button_map(self) -> Dict[int, Any]:
        return {
            0: vgamepad.XUSB_BUTTON.XUSB_GAMEPAD_A,
            1: vgamepad.XUSB_BUTTON.XUSB_GAMEPAD_B,
            2: vgamepad.XUSB_BUTTON.XUSB_GAMEPAD_X,
            3: vgamepad.XUSB_BUTTON.XUSB_GAMEPAD_Y,
            4: vgamepad.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
            5: vgamepad.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
            6: vgamepad.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
            7: vgamepad.XUSB_BUTTON.XUSB_GAMEPAD_START,
            8: vgamepad.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
            9: vgamepad.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
        }

    def send_button(self, step: SequenceStep) -> None:
        if step.button_id not in self.button_map:
            print(f"No hay mapeo de mando virtual para {step.button_name}.")
            return

        virtual_button = self.button_map[step.button_id]
        self.gamepad.press_button(button=virtual_button)
        self.gamepad.update()
        time.sleep(self.press_duration)
        self.gamepad.release_button(button=virtual_button)
        self.gamepad.update()
        print(f"Boton enviado al mando virtual: {step.button_name}")


class PullupsBot:
    """Controla el bucle de reproduccion, pausa y detencion."""

    def __init__(
        self,
        sequence: List[SequenceStep],
        config: BotConfig,
        sender: VirtualGamepadSender,
    ) -> None:
        self.sequence = sequence
        self.config = config
        self.sender = sender
        self.current_interval = config.initial_interval

        self._running = threading.Event()
        self._stop_requested = threading.Event()
        self._burst_mode_enabled = threading.Event()
        self._next_burst_enabled = threading.Event()
        self._next_first_button_burst_enabled = threading.Event()
        self._auto_first_button_burst_enabled = threading.Event()
        if AUTO_BURST_ENABLED_BY_DEFAULT:
            self._auto_first_button_burst_enabled.set()
        self._worker: threading.Thread | None = None
        self._sequence_lock = threading.Lock()
        self._cycle_count = 1
        self._pending_initial_delay = threading.Event()
        self._pending_initial_delay.set()

    def start(self) -> None:
        if self._worker and self._worker.is_alive():
            self._running.set()
            print("Bot iniciado/reanudado.")
            return

        self.current_interval = self.config.initial_interval
        self._cycle_count = 1
        self._pending_initial_delay.set()
        self._stop_requested.clear()
        self._running.set()
        self._worker = threading.Thread(target=self._run_loop, daemon=True)
        self._worker.start()
        print("Bot iniciado automaticamente.")

    def pause(self) -> None:
        self._running.clear()
        print("Bot pausado.")

    def stop(self) -> None:
        self._stop_requested.set()
        self._running.set()
        self.current_interval = self.config.initial_interval
        self._cycle_count = 1
        self._pending_initial_delay.set()
        print("Bot detenido. La velocidad se reinicio.")

    def replace_sequence(
        self,
        sequence: List[SequenceStep],
        learned_interval: float | None = None,
    ) -> None:
        with self._sequence_lock:
            if learned_interval is not None:
                self.config.initial_interval = learned_interval
            self.sequence = sequence
            self.current_interval = self.config.initial_interval
            self._cycle_count = 1
            self._pending_initial_delay.set()

        self._next_burst_enabled.clear()
        self._next_first_button_burst_enabled.clear()
        self._burst_mode_enabled.clear()
        if AUTO_BURST_ENABLED_BY_DEFAULT:
            self._auto_first_button_burst_enabled.set()
        else:
            self._auto_first_button_burst_enabled.clear()
        print(
            "Secuencia reemplazada. "
            f"Segunda fase inicia como una ronda nueva: {self.current_interval:.3f}s."
        )

    def reset_speed(self) -> None:
        self.current_interval = self.config.initial_interval
        print(f"Velocidad reiniciada: intervalo {self.current_interval:.3f}s")

    def speed_up(self) -> None:
        self.current_interval = max(
            self.config.minimum_interval,
            self.current_interval * (1.0 - MANUAL_SPEED_FACTOR),
        )
        print(f"Velocidad aumentada: intervalo {self.current_interval:.3f}s")

    def slow_down(self) -> None:
        self.current_interval = self.current_interval * (1.0 + MANUAL_SPEED_FACTOR)
        print(f"Velocidad reducida: intervalo {self.current_interval:.3f}s")

    def trigger_next_burst(self) -> None:
        self._next_burst_enabled.set()
        print(
            "Siguiente pulsacion: machaque "
            f"x{BURST_REPEAT_COUNT} en {BURST_TOTAL_DURATION:.2f}s."
        )

    def trigger_next_first_button_burst(self) -> None:
        self._next_first_button_burst_enabled.set()
        print(
            "Machaque preparado: se aplicara al proximo primer boton "
            "de la secuencia."
        )

    def toggle_burst_mode(self) -> None:
        if self._burst_mode_enabled.is_set():
            self._burst_mode_enabled.clear()
            print("Modo machaque: DESACTIVADO.")
            return

        self._burst_mode_enabled.set()
        print(
            "Modo machaque: ACTIVADO. Cada boton se enviara "
            f"{BURST_REPEAT_COUNT} veces."
        )

    def toggle_auto_first_button_burst(self) -> None:
        """Toggle experimental; no esta enlazado a una hotkey por defecto."""

        if self._auto_first_button_burst_enabled.is_set():
            self._auto_first_button_burst_enabled.clear()
            print("Machaque automatico cada 5 vueltas: DESACTIVADO.")
            return

        self._auto_first_button_burst_enabled.set()
        print("Machaque automatico cada 5 vueltas: ACTIVADO.")

    def _get_repeats_for_step(self, step_index: int) -> int:
        if self._burst_mode_enabled.is_set():
            return BURST_REPEAT_COUNT

        if self._next_burst_enabled.is_set():
            self._next_burst_enabled.clear()
            return BURST_REPEAT_COUNT

        if step_index == 0 and self._next_first_button_burst_enabled.is_set():
            self._next_first_button_burst_enabled.clear()
            return BURST_REPEAT_COUNT

        should_auto_burst = (
            self._auto_first_button_burst_enabled.is_set()
            and step_index == 0
            and self._cycle_count > 0
            and self._cycle_count % AUTO_BURST_EVERY_CYCLES == 0
        )
        if should_auto_burst:
            print(
                f"Despues de {self._cycle_count} vueltas: "
                f"machaque x{BURST_REPEAT_COUNT} automatico en el boton inicial."
            )
            return BURST_REPEAT_COUNT

        return 1

    def _accelerate(self) -> None:
        self.current_interval = max(
            self.config.minimum_interval,
            self.current_interval * self.config.speed_multiplier_per_press,
        )

    def _run_loop(self) -> None:
        while not self._stop_requested.is_set():
            self._running.wait()

            with self._sequence_lock:
                sequence_snapshot = list(self.sequence)

            for step_index, step in enumerate(sequence_snapshot):
                if self._stop_requested.is_set() or not self._running.is_set():
                    break

                if self._pending_initial_delay.is_set():
                    print(
                        "Esperando intervalo aprendido antes del primer input: "
                        f"{self.current_interval:.3f}s"
                    )
                    time.sleep(self.current_interval)
                    self.current_interval = max(
                        self.config.minimum_interval,
                        self.current_interval * START_SPEED_FACTOR_AFTER_CAPTURE,
                    )
                    self._pending_initial_delay.clear()

                repeats = self._get_repeats_for_step(step_index)
                print(f"Velocidad actual: intervalo {self.current_interval:.3f}s")

                for repeat_index in range(repeats):
                    if self._stop_requested.is_set() or not self._running.is_set():
                        break

                    if repeats > 1:
                        print(
                            f"Repeticion {repeat_index + 1}/{repeats} "
                            f"para {step.button_name}"
                        )

                    self.sender.send_button(step)

                    if repeat_index < repeats - 1:
                        time.sleep(BURST_PRESS_GAP)

                recovery_delay = BURST_RECOVERY_EXTRA_DELAY if repeats > 1 else 0.0
                if recovery_delay > 0:
                    print(
                        "Recuperacion post-machaque: "
                        f"+{recovery_delay:.3f}s antes del siguiente boton."
                    )

                time.sleep(self.current_interval + recovery_delay)
                self._accelerate()

            if self._running.is_set() and not self._stop_requested.is_set():
                self._cycle_count += 1
                print(f"Vuelta completada: {self._cycle_count}")


class HotkeyController:
    """Registra hotkeys globales para controlar el bot."""

    def __init__(
        self,
        bot: PullupsBot,
        listener: GamepadListener,
    ) -> None:
        self.bot = bot
        self.listener = listener
        self._recapture_requested = threading.Event()

    def register(self) -> None:
        keyboard.add_hotkey("F1", self.bot.reset_speed)
        keyboard.add_hotkey("F2", self.bot.speed_up)
        keyboard.add_hotkey("F3", self.bot.slow_down)
        keyboard.add_hotkey("F4", self.bot.trigger_next_burst)
        keyboard.add_hotkey("F5", self.recapture_sequence)
        keyboard.add_hotkey("F6", self.bot.trigger_next_first_button_burst)
        keyboard.add_hotkey("F7", self.bot.toggle_burst_mode)
        keyboard.add_hotkey("F8", self.bot.start)
        keyboard.add_hotkey("F9", self.bot.pause)
        keyboard.add_hotkey("F10", self.bot.stop)

        print("\nHotkeys:")
        print("  F1  reiniciar velocidad")
        print("  F2  acelerar 10%")
        print("  F3  desacelerar 10%")
        print("  F4  machacar la siguiente pulsacion inmediata")
        print("  F5  capturar nueva secuencia de 4 botones")
        print("  F6  preparar machaque para el proximo primer boton")
        print("  F7  activar / desactivar modo machaque continuo")
        print("  F8  reanudar")
        print("  F9  pausar")
        print("  F10 detener")
        print("\nDeja esta ventana abierta. Presiona Ctrl+C para salir.\n")

    def recapture_sequence(self) -> None:
        self._recapture_requested.set()
        print("\nRecaptura solicitada. Esperando al hilo principal...")

    def consume_recapture_request(self) -> bool:
        if not self._recapture_requested.is_set():
            return False

        self._recapture_requested.clear()
        return True


def main() -> None:
    print("FF7 Pull-ups Bot")
    print("================")
    print("Sin preguntas: captura 4 botones y arranca automatico.")
    print(
        "Preset: curva de aceleracion "
        f"{INITIAL_INTERVAL:.3f}s -> {MINIMUM_INTERVAL:.3f}s "
        f"(x{SPEED_MULTIPLIER_PER_PRESS:.3f} por boton)."
    )

    try:
        listener = GamepadListener()
        sequence = listener.capture_unique_sequence(length=4)
        config = BotConfig(initial_interval=listener.last_learned_interval)
        sender = VirtualGamepadSender(config.press_duration)
        bot = PullupsBot(sequence, config, sender)
        hotkeys = HotkeyController(bot, listener)
        hotkeys.register()
        bot.start()

        while True:
            if hotkeys.consume_recapture_request():
                print("\nBot pausado para capturar la segunda fase.")
                bot.pause()
                time.sleep(0.25)
                sequence = listener.capture_unique_sequence(length=4)
                bot.replace_sequence(
                    sequence,
                    learned_interval=listener.last_learned_interval,
                )
                bot.start()

            time.sleep(0.25)

    except KeyboardInterrupt:
        print("\nSaliendo...")
    except RuntimeError as error:
        print(f"\nError: {error}")
        print("Para mando virtual instala:")
        print("  py -3.12 -m pip install vgamepad")
        print("Y asegúrate de tener ViGEmBus instalado en Windows.")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
