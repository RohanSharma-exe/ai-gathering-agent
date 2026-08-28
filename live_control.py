"""Guarded live-control runtime for the Albion gathering prototype."""

from __future__ import annotations

from dataclasses import dataclass
from time import sleep as default_sleep
from typing import Callable, Protocol

from actions import Action, ActionExecutor, ActionKind
from config import DEFAULT_INVENTORY_RETURN_THRESHOLD
from state import Objective
from vision import Observation


class ScreenshotSource(Protocol):
    def screenshot(self, path=None):
        ...


@dataclass(frozen=True)
class LiveControlConfig:
    """Safety and input settings for the live controller."""

    max_frames: int = 100
    dry_run: bool = True
    dismount_key: str | None = "a"
    gather_cooldown: float = 0.25
    min_mount_confidence: float = 0.8
    inventory_return_threshold: float = DEFAULT_INVENTORY_RETURN_THRESHOLD
    max_gathers: int | None = None
    dismount_only: bool = False

    def __post_init__(self) -> None:
        if self.max_frames < 1:
            raise ValueError("max_frames must be positive")
        if not 0 <= self.min_mount_confidence <= 1:
            raise ValueError("min_mount_confidence must be between 0 and 1")
        if self.gather_cooldown < 0:
            raise ValueError("gather_cooldown cannot be negative")
        if not 0 <= self.inventory_return_threshold <= 100:
            raise ValueError("inventory_return_threshold must be between 0 and 100")
        if self.max_gathers is not None and self.max_gathers < 1:
            raise ValueError("max_gathers must be positive when provided")


class LiveControlRuntime:
    """Observe the game and execute only conservative, verified actions."""

    def __init__(self, source: ScreenshotSource, observe: Callable[[object], Observation], executor: ActionExecutor, objective: Objective, config: LiveControlConfig | None = None, sleep: Callable[[float], None] = default_sleep) -> None:
        self.source = source
        self.observe = observe
        self.executor = executor
        self.objective = objective
        self.config = config or LiveControlConfig()
        self.sleep = sleep

    def _execute(self, action: Action) -> bool:
        if self.config.dry_run:
            return True
        return self.executor.execute(action).accepted

    def run(self) -> int:
        frames = 0
        dismount_requested = False
        gathers = 0

        while frames < self.config.max_frames:
            image = self.source.screenshot()
            observation = self.observe(image)
            frames += 1

            if observation.mounted_confidence < self.config.min_mount_confidence:
                break
            if observation.inventory_percent >= self.config.inventory_return_threshold:
                break

            if observation.mounted:
                if not dismount_requested:
                    if not self.config.dismount_key:
                        break
                    if not self._execute(Action(kind=ActionKind.PRESS_KEY, key=self.config.dismount_key)):
                        break
                    dismount_requested = True
                if self.config.gather_cooldown:
                    self.sleep(self.config.gather_cooldown)
                continue

            dismount_requested = False
            if self.config.dismount_only:
                break
            if self.config.max_gathers is not None and gathers >= self.config.max_gathers:
                break

            target = next((candidate for candidate in observation.targets if candidate.is_compatible_with(self.objective) and candidate.screen_x is not None and candidate.screen_y is not None), None)
            if target is None:
                continue

            width, height = image.size
            x = round(target.screen_x * width)
            y = round(target.screen_y * height)
            action = Action(kind=ActionKind.GATHER, target_id=target.resource, x=x, y=y)
            if not self._execute(action):
                break
            gathers += 1
            if self.config.max_gathers is not None and gathers >= self.config.max_gathers:
                break
            if self.config.gather_cooldown:
                self.sleep(self.config.gather_cooldown)

        return frames


@dataclass(frozen=True)
class ControlConfig:
    mount_key: str = "a"
    gather_key: str = "e"
    stop_key: str = "esc"


class LiveController:
    def __init__(self, desktop, config: ControlConfig | None = None) -> None:
        self.desktop = desktop
        self.config = config or ControlConfig()

    @property
    def enabled(self) -> bool:
        return not self.desktop.dry_run

    def mount_or_dismount(self) -> bool:
        return self.desktop.press(self.config.mount_key)

    def gather(self) -> bool:
        return self.desktop.press(self.config.gather_key)

    def stop(self) -> bool:
        return self.desktop.press(self.config.stop_key)
