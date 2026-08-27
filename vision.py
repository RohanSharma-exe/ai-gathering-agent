"""Local visual-observation boundary for the gathering-agent brain."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from config import ScreenRegions
from state import Target


@dataclass(frozen=True)
class BoundingBox:
    """A normalized x/y/width/height rectangle, all values in the 0..1 range."""

    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        values = (self.x, self.y, self.width, self.height)
        if any(value < 0 or value > 1 for value in values):
            raise ValueError("bounding-box values must be between 0 and 1")
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("bounding box must remain inside the screen")

    def to_pixels(self, screen_width: int, screen_height: int) -> tuple[int, int, int, int]:
        """Convert to integer x, y, width, height pixels."""
        if screen_width < 1 or screen_height < 1:
            raise ValueError("screen dimensions must be positive")
        return (
            round(self.x * screen_width),
            round(self.y * screen_height),
            round(self.width * screen_width),
            round(self.height * screen_height),
        )


@dataclass(frozen=True)
class Observation:
    """Structured information extracted from one visual observation."""

    area: str = ""
    area_type: str = "safe"
    inventory_percent: float = 0
    mounted: bool = False
    targets: tuple[Target, ...] = ()
    player_confidence: float = 0
    mounted_confidence: float = 0

    def __post_init__(self) -> None:
        if not 0 <= self.inventory_percent <= 100:
            raise ValueError("inventory_percent must be between 0 and 100")
        for name, value in (
            ("player_confidence", self.player_confidence),
            ("mounted_confidence", self.mounted_confidence),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")


class ObservationDetector(Protocol):
    """Convert a decoded screenshot into an Observation."""

    def detect(self, image: object) -> Observation:
        ...


class LocalPerceptionDetector:
    """Conservative local detector scaffold.

    It intentionally returns only high-confidence information that it can prove
    from the current implementation. It does not guess game objects from pixels.
    A real local detector can later implement this same interface.
    """

    def __init__(self, regions: ScreenRegions | None = None) -> None:
        self.regions = regions or ScreenRegions()

    def detect(self, image: object) -> Observation:
        if not hasattr(image, "size"):
            raise TypeError("detector expects an image with a size attribute")
        return Observation()


class VisionProvider:
    """Controlled observation provider used by the prototype and tests."""

    def __init__(self, observation: Observation) -> None:
        self._observation = observation

    def observe(self) -> Observation:
        return self._observation


class ScreenshotVisionProvider:
    """Load screenshots locally and delegate interpretation to a detector."""

    def __init__(self, screenshot_path: str | Path, detector: ObservationDetector) -> None:
        self._path = Path(screenshot_path)
        self._detector = detector

    def observe(self) -> Observation:
        if not self._path.is_file():
            raise FileNotFoundError(f"Screenshot not found: {self._path}")

        try:
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError(
                "Pillow is required for screenshot observation. Run `uv sync`."
            ) from exc

        with Image.open(self._path) as image:
            image.load()
            return self._detector.detect(image)
