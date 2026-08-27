"""Guarded live input control for the Albion gathering prototype."""

from __future__ import annotations

from dataclasses import dataclass

from desktop import Desktop


@dataclass(frozen=True)
class ControlConfig:
    """Keyboard bindings used by the guarded controller."""

    mount_key: str = "a"
    gather_key: str = "e"
    stop_key: str = "esc"


class LiveController:
    """Small, explicit input boundary; disabled unless explicitly enabled."""

    def __init__(self, desktop: Desktop, config: ControlConfig | None = None) -> None:
        self.desktop = desktop
        self.config = config or ControlConfig()

    @property
    def enabled(self) -> bool:
        return not self.desktop.dry_run

    def mount_or_dismount(self) -> bool:
        """Toggle mount state through the configured Albion mount key."""
        return self.desktop.press(self.config.mount_key)

    def gather(self) -> bool:
        """Send the gather/interact key; caller must verify the state first."""
        return self.desktop.press(self.config.gather_key)

    def stop(self) -> bool:
        """Send the configured emergency-stop key."""
        return self.desktop.press(self.config.stop_key)
