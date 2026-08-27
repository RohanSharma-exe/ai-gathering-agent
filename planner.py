"""Deterministic planner for the gathering-agent brain."""

from dataclasses import dataclass
from enum import Enum

from config import ALLOWED_AREA_TYPES, DEFAULT_INVENTORY_RETURN_THRESHOLD
from state import AgentState, GameState, Target


class DecisionKind(Enum):
    TARGET = "target"
    EXPLORE = "explore"
    RETURN = "return"
    COMBAT = "combat"
    GATHER = "gather"
    RECOVER = "recover"


@dataclass(frozen=True)
class Decision:
    kind: DecisionKind
    target: Target | None = None
    reason: str = ""


def decide(
    state: GameState,
    inventory_threshold: float = DEFAULT_INVENTORY_RETURN_THRESHOLD,
) -> Decision:
    if state.inventory_needs_return(inventory_threshold):
        return Decision(DecisionKind.RETURN, reason="inventory threshold reached")

    if state.area_type not in ALLOWED_AREA_TYPES:
        return Decision(DecisionKind.EXPLORE, reason="current area is not allowed")

    candidates = [
        target
        for target in state.nearby_targets
        if target.is_compatible_with(state.objective)
    ]
    if not candidates:
        return Decision(DecisionKind.EXPLORE, reason="no compatible target nearby")

    target = min(candidates, key=lambda item: item.distance)
    return Decision(DecisionKind.TARGET, target=target, reason="nearest compatible target")


def planner_state_for(decision: Decision) -> AgentState:
    """Map a high-level decision to the next deterministic agent state."""
    if decision.kind is DecisionKind.RETURN:
        return AgentState.RETURNING
    if decision.kind is DecisionKind.EXPLORE:
        return AgentState.EXPLORING
    if decision.kind is DecisionKind.RECOVER:
        return AgentState.RECOVERING
    if decision.kind is DecisionKind.TARGET and decision.target is not None:
        if decision.target.kind.value == "animal":
            return AgentState.COMBAT
        return AgentState.GATHERING
    if decision.kind is DecisionKind.COMBAT:
        return AgentState.COMBAT
    if decision.kind is DecisionKind.GATHER:
        return AgentState.GATHERING
    return AgentState.SEARCHING
