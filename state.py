"""Typed state models used by the gathering-agent planner."""

from dataclasses import dataclass, field
from enum import Enum


class AgentState(Enum):
    IDLE = "idle"
    SEARCHING = "searching"
    TARGETING = "targeting"
    TRAVELING = "traveling"
    COMBAT = "combat"
    GATHERING = "gathering"
    EXPLORING = "exploring"
    RETURNING = "returning"
    STORING = "storing"
    RECOVERING = "recovering"


class TargetKind(Enum):
    ANIMAL = "animal"
    RESOURCE = "resource"


@dataclass(frozen=True)
class Objective:
    resource: str

    def __post_init__(self) -> None:
        resource = self.resource.strip().lower()
        if not resource:
            raise ValueError("resource cannot be empty")
        object.__setattr__(self, "resource", resource)


@dataclass(frozen=True)
class Target:
    kind: TargetKind
    resource: str
    distance: float

    def __post_init__(self) -> None:
        if self.distance < 0:
            raise ValueError("distance cannot be negative")
        object.__setattr__(self, "resource", self.resource.strip().lower())

    def is_compatible_with(self, objective: Objective) -> bool:
        return objective.resource == "everything" or self.resource == objective.resource


@dataclass
class GameState:
    objective: Objective
    agent_state: AgentState = AgentState.IDLE
    inventory_percent: float = 0
    current_target: Target | None = None
    current_area: str = ""
    area_type: str = "safe"
    mounted: bool = False
    nearby_targets: list[Target] = field(default_factory=list)
    last_action: str | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.inventory_percent <= 100:
            raise ValueError("inventory_percent must be between 0 and 100")

    def inventory_needs_return(self, threshold: float) -> bool:
        if not 0 <= threshold <= 100:
            raise ValueError("threshold must be between 0 and 100")
        return self.inventory_percent >= threshold
