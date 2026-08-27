"""Controlled action boundary for the gathering-agent brain.

The executor supports a dry-run mode for safe testing and a real PyAutoGUI
mode for local input automation.  Higher-level planning remains independent
of the input mechanism.
"""

from dataclasses import dataclass
from enum import Enum


class ActionKind(Enum):
    MOVE = "move"
    INTERACT = "interact"
    ATTACK = "attack"
    GATHER = "gather"
    WAIT = "wait"
    CHANGE_AREA = "change_area"
    RETURN_TO_STORAGE = "return_to_storage"
    PRESS_KEY = "press_key"
    CLICK = "click"


@dataclass(frozen=True)
class Action:
    kind: ActionKind
    target_id: str | None = None
    x: int | None = None
    y: int | None = None
    key: str | None = None
    duration: float = 0.0


@dataclass(frozen=True)
class ActionResult:
    accepted: bool
    action: Action
    message: str = ""


class ActionExecutor:
    """No-op executor used by the planner and unit tests."""

    def propose(self, action: Action) -> ActionResult:
        return ActionResult(accepted=True, action=action, message="action proposed")

    def execute(self, action: Action) -> ActionResult:
        return self.propose(action)


class PyAutoGUIExecutor(ActionExecutor):
    """Execute primitive mouse/keyboard actions through PyAutoGUI.

    ``dry_run=True`` is the default so importing and testing this class never
    sends input to the desktop.  Real input requires an explicit
    ``dry_run=False``.
    """

    def __init__(self, dry_run: bool = True, pause: float = 0.03) -> None:
        self.dry_run = dry_run
        self.pause = pause
        self._pyautogui = None

    def _input(self):
        if self._pyautogui is None:
            import pyautogui

            pyautogui.PAUSE = self.pause
            self._pyautogui = pyautogui
        return self._pyautogui

    def execute(self, action: Action) -> ActionResult:
        if self.dry_run:
            return ActionResult(True, action, "dry-run: input not sent")

        try:
            gui = self._input()

            if action.kind is ActionKind.CLICK:
                if action.x is None or action.y is None:
                    return ActionResult(False, action, "click requires x and y")
                gui.click(action.x, action.y)

            elif action.kind is ActionKind.PRESS_KEY:
                if not action.key:
                    return ActionResult(False, action, "press_key requires key")
                gui.press(action.key)

            elif action.kind is ActionKind.MOVE:
                if action.x is None or action.y is None:
                    return ActionResult(False, action, "move requires x and y")
                gui.moveTo(action.x, action.y, duration=max(0.0, action.duration))

            else:
                return ActionResult(
                    False,
                    action,
                    f"real input is not implemented for {action.kind.value} yet",
                )

            return ActionResult(True, action, "input executed")
        except Exception as exc:
            return ActionResult(False, action, f"input failed: {exc}")
