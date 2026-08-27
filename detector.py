"""Model-agnostic local visual detection interfaces.

The detector produces observations only; it has no game-input or automation
responsibilities. A local CV/object-detection backend can implement the
protocol without changing downstream consumers.
"""

from dataclasses import dataclass
from typing import Protocol

from vision import BoundingBox


@dataclass(frozen=True)
class Detection:
    """One detected visual object in normalized screen coordinates."""

    label: str
    confidence: float
    box: BoundingBox
    source: str = "local"

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("label cannot be empty")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(self, "label", self.label.strip().lower())
        object.__setattr__(self, "source", self.source.strip().lower() or "local")


class Detector(Protocol):
    """Protocol implemented by a local visual detector backend."""

    def detect(self, image: object) -> tuple[Detection, ...]:
        ...


def filter_detections(
    detections: tuple[Detection, ...],
    *,
    labels: set[str] | None = None,
    minimum_confidence: float = 0.5,
) -> tuple[Detection, ...]:
    """Return valid detections matching optional labels and confidence."""
    if not 0 <= minimum_confidence <= 1:
        raise ValueError("minimum_confidence must be between 0 and 1")

    normalized_labels = {label.strip().lower() for label in labels} if labels is not None else None
    return tuple(
        detection
        for detection in detections
        if detection.confidence >= minimum_confidence
        and (normalized_labels is None or detection.label in normalized_labels)
    )


class EmptyDetector:
    """Deterministic detector useful until a real local backend is selected."""

    def detect(self, image: object) -> tuple[Detection, ...]:
        if not hasattr(image, "size"):
            raise TypeError("detector expects an image with a size attribute")
        return ()
