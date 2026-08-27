"""Drives the HAT's 3 onboard APA102 RGB LEDs (SPI0) as a recording indicator.

Requires SPI enabled (`dtparam=spi=on` in /boot/firmware/config.txt, then reboot)
and the `apa102-pi` package (see button_listen_demo.py's `uv run --with`).

If the LEDs aren't wired/working (SPI off, no HAT, different clone board), we
degrade to a no-op rather than crashing the voice pipeline over cosmetics.
"""

import threading
from typing import Self

NUM_LEDS = 3
COLOR = (0, 200, 200)  # cyan: reads as "listening"


def _dim(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(int(c * factor) for c in color)


def _chase(strip, stop_event: threading.Event) -> None:
    """Rotating 'comet': one bright LED plus a dim trailing pixel, circling
    continuously while recording."""
    i = 0
    while not stop_event.is_set():
        for led in range(NUM_LEDS):
            if led == i:
                strip.set_pixel(led, *COLOR)
            elif led == (i - 1) % NUM_LEDS:
                strip.set_pixel(led, *_dim(COLOR, 0.25))
            else:
                strip.set_pixel(led, 0, 0, 0)
        strip.show()
        i = (i + 1) % NUM_LEDS
        stop_event.wait(0.15)
    strip.clear_strip()
    strip.show()


class RecordingIndicator:
    """Context manager: animates the HAT's LEDs while its `with` block runs.

    Usage:
        with RecordingIndicator():
            record(...)
    """

    def __init__(self) -> None:
        self.strip = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        try:
            from apa102_pi.driver import apa102

            self.strip = apa102.APA102(num_led=NUM_LEDS)
        except Exception as e:  # noqa: BLE001 — LEDs are cosmetic, never block recording
            print(f"(LEDs unavailable, continuing without them: {e})")

    def __enter__(self) -> Self:
        if self.strip is not None:
            self._stop.clear()
            self._thread = threading.Thread(
                target=_chase, args=(self.strip, self._stop), daemon=True
            )
            self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        if self.strip is None:
            return
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
        self.strip.cleanup()
