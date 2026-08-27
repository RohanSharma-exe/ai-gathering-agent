"""Controlled action boundary for the gathering-agent brain."""

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


@dataclass(frozen=True)
class Action:
    kind: ActionKind
    target_id: str | None = None


@dataclass(frozen=True)
class ActionResult:
    accepted: bool
    action: Action
    message: str = ""


class ActionExecutor:
    """No-op executor for controlled testing; it performs no external input."""

    def propose(self, action: Action) -> ActionResult:
        return ActionResult(accepted=True, action=action, message="action proposed")
