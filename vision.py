"""Visual observation boundary for the gathering-agent brain."""

from dataclasses import dataclass

from state import Target


@dataclass(frozen=True)
class Observation:
    area: str = ""
    area_type: str = "safe"
    inventory_percent: float = 0
    mounted: bool = False
    targets: tuple[Target, ...] = ()


class VisionProvider:
    """Controlled observation provider used by the prototype and tests."""

    def __init__(self, observation: Observation) -> None:
        self._observation = observation

    def observe(self) -> Observation:
        return self._observation
