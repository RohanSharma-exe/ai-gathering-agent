"""Visual observation models for offline screenshot analysis.

The observation layer describes what a vision backend sees. It deliberately
contains no input/control logic, so it can be tested independently from any
runtime integration.
"""

from dataclasses import dataclass

from state import Target


@dataclass(frozen=True)
class UIObservation:
    """High-level state cues that can be extracted from a screenshot."""

    mounted: bool | None = None
    inventory_percent: float | None = None
    city_present: bool = False
    chest_present: bool = False
    skills_visible: bool = False
    targets: tuple[Target, ...] = ()

    def __post_init__(self) -> None:
        if self.inventory_percent is not None and self.inventory_percent < 0:
            raise ValueError("inventory_percent cannot be negative")

    @property
    def inventory_full(self) -> bool:
        return self.inventory_percent is not None and self.inventory_percent >= 100

    @property
    def can_use_skill_bar(self) -> bool:
        """Whether the observation indicates an unmounted character."""
        return self.mounted is False and self.skills_visible

    @property
    def storage_destination_visible(self) -> bool:
        """Whether a city storage/chest cue is visible."""
        return self.city_present and self.chest_present


def should_prepare_for_storage(observation: UIObservation) -> bool:
    """Return true when capacity is full or a storage destination is visible."""
    return observation.inventory_full or observation.storage_destination_visible
