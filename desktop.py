"""Desktop I/O boundary for the local gathering-agent prototype."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class Desktop:
    """Small PyAutoGUI-backed desktop adapter.

    The adapter is deliberately explicit: ``dry_run=True`` never sends input.
    """

    def __init__(self, dry_run: bool = True, pause: float = 0.03) -> None:
        self.dry_run = dry_run
        self.pause = pause
        self._gui: Any | None = None

    def _load(self) -> Any:
        if self._gui is None:
            import pyautogui

            pyautogui.PAUSE = self.pause
            self._gui = pyautogui
        return self._gui

    def screenshot(self, path: str | Path | None = None) -> Any:
        """Capture the current screen; optionally save it to ``path``."""
        image = self._load().screenshot()
        if path is not None:
            destination = Path(path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            image.save(destination)
        return image

    def click(self, x: int, y: int) -> bool:
        if self.dry_run:
            return False
        self._load().click(x, y)
        return True

    def press(self, key: str) -> bool:
        if self.dry_run:
            return False
        self._load().press(key)
        return True

    def move_to(self, x: int, y: int, duration: float = 0.0) -> bool:
        if self.dry_run:
            return False
        self._load().moveTo(x, y, duration=max(0.0, duration))
        return True
