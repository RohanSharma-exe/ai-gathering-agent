"""Small, local configuration for visual perception and planning."""

from dataclasses import dataclass

DEFAULT_INVENTORY_RETURN_THRESHOLD = 90
ALLOWED_AREA_TYPES = frozenset({"safe", "low-risk"})
SUPPORTED_RESOURCES = frozenset({"leather", "fiber", "ore", "wood", "stone"})


@dataclass(frozen=True)
class ScreenRegions:
    """Normalized screen regions (0..1), independent of resolution."""

    play_area: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 0.88)
    inventory: tuple[float, float, float, float] = (0.70, 0.55, 0.30, 0.45)
    status: tuple[float, float, float, float] = (0.0, 0.0, 0.35, 0.20)


@dataclass(frozen=True)
class PerceptionConfig:
    """Thresholds for cheap local perception."""

    minimum_confidence: float = 0.65
    max_detection_size: int = 1280

    def __post_init__(self) -> None:
        if not 0 <= self.minimum_confidence <= 1:
            raise ValueError("minimum_confidence must be between 0 and 1")
        if self.max_detection_size < 1:
            raise ValueError("max_detection_size must be positive")
