"""
D2R Vault — global hotkey listener.

Listens for configured hotkeys (default F9/F10/F11/F12) system-wide so
they work while D2R has focus, WITHOUT requiring D2R to lose focus and
WITHOUT sending any input into the game window. This only *reads*
keyboard events; it never simulates clicks or keypresses into D2R.
"""
from __future__ import annotations

import threading
from typing import Callable

# Maps our friendly hotkey names ("F9") to pynput Key objects lazily,
# so this module can be imported/tested without pynput installed.
_KEY_NAME_MAP = {f"F{i}": f"f{i}" for i in range(1, 13)}


class HotkeyListener:
    """Wraps pynput's global keyboard listener. Call `register` for each
    action before `start`. Runs on a background thread; callbacks fire
    on that thread, so GUI callbacks should marshal back to the Qt
    event loop (e.g. via a Qt signal) rather than touching widgets
    directly.
    """

    def __init__(self):
        self._callbacks: dict[str, Callable[[], None]] = {}
        self._listener = None
        self._paused = False
        self._lock = threading.Lock()

    def register(self, hotkey_name: str, callback: Callable[[], None]) -> None:
        """hotkey_name like 'F9'."""
        self._callbacks[hotkey_name.upper()] = callback

    def pause(self) -> None:
        with self._lock:
            self._paused = True

    def resume(self) -> None:
        with self._lock:
            self._paused = False

    @property
    def is_paused(self) -> bool:
        with self._lock:
            return self._paused

    def _on_press(self, key) -> None:
        if self.is_paused:
            return
        try:
            name = key.name.upper() if hasattr(key, "name") else None
        except AttributeError:
            name = None
        if name and name in self._callbacks:
            self._callbacks[name]()

    def start(self) -> None:
        from pynput import keyboard

        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None


class MockHotkeyListener:
    """Test double: lets tests fire a hotkey callback directly without a
    real global keyboard hook (which requires a display/OS hook and
    isn't available in CI)."""

    def __init__(self):
        self._callbacks: dict[str, Callable[[], None]] = {}
        self._paused = False

    def register(self, hotkey_name: str, callback: Callable[[], None]) -> None:
        self._callbacks[hotkey_name.upper()] = callback

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    @property
    def is_paused(self) -> bool:
        return self._paused

    def fire(self, hotkey_name: str) -> None:
        if self._paused:
            return
        cb = self._callbacks.get(hotkey_name.upper())
        if cb:
            cb()

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass
