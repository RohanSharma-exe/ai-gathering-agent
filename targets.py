"""Candidate-target detection and objective filtering primitives.

This module intentionally does not identify game objects from pixels. A local
CV/model adapter can emit TargetCandidate objects later without changing the
planner contract.
"""

from dataclasses import dataclass
from math import hypot

from state import Objective, Target, TargetKind
from vision import BoundingBox


@dataclass(frozen=True)
class TargetCandidate:
    """A visually detected candidate before objective filtering."""

    kind: TargetKind
    resource: str
    box: BoundingBox
    confidence: float
    available: bool = True

    def __post_init__(self) -> None:
        if not self.resource.strip():
            raise ValueError("resource cannot be empty")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(self, "resource", self.resource.strip().lower())

    @property
    def center(self) -> tuple[float, float]:
        return (self.box.x + self.box.width / 2, self.box.y + self.box.height / 2)

    def estimated_distance(self, origin: tuple[float, float] = (0.5, 0.5)) -> float:
        """Estimate screen-space distance from an origin, not world distance."""
        x, y = self.center
        return hypot(x - origin[0], y - origin[1])

    def to_target(self, origin: tuple[float, float] = (0.5, 0.5)) -> Target:
        return Target(
            kind=self.kind,
            resource=self.resource,
            distance=self.estimated_distance(origin),
        )


class TargetDetector:
    """Adapter boundary for a future local visual detector."""

    def detect(self, image: object) -> tuple[TargetCandidate, ...]:
        if not hasattr(image, "size"):
            raise TypeError("target detector expects an image with a size attribute")
        return ()


def filter_candidates(
    candidates: tuple[TargetCandidate, ...],
    objective: Objective,
    minimum_confidence: float = 0.5,
) -> tuple[TargetCandidate, ...]:
    """Keep available, sufficiently confident candidates matching the objective."""
    if not 0 <= minimum_confidence <= 1:
        raise ValueError("minimum_confidence must be between 0 and 1")

    return tuple(
        candidate
        for candidate in candidates
        if candidate.available
        and candidate.confidence >= minimum_confidence
        and (objective.resource == "everything" or candidate.resource == objective.resource)
    )


def choose_nearest(
    candidates: tuple[TargetCandidate, ...],
    origin: tuple[float, float] = (0.5, 0.5),
) -> TargetCandidate | None:
    """Select the closest candidate in normalized screen space."""
    if not candidates:
        return None
    return min(candidates, key=lambda candidate: candidate.estimated_distance(origin))
