"""Local visual-observation boundary for the gathering-agent brain."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from state import Target


@dataclass(frozen=True)
class Observation:
    """Structured information extracted from one visual observation."""

    area: str = ""
    area_type: str = "safe"
    inventory_percent: float = 0
    mounted: bool = False
    targets: tuple[Target, ...] = ()


class ObservationDetector(Protocol):
    """Convert a decoded screenshot into an Observation."""

    def detect(self, image: object) -> Observation:
        ...


class VisionProvider:
    """Controlled observation provider used by the prototype and tests."""

    def __init__(self, observation: Observation) -> None:
        self._observation = observation

    def observe(self) -> Observation:
        return self._observation


class ScreenshotVisionProvider:
    """Load screenshots locally and delegate interpretation to a detector.

    The detector is intentionally injected so the project can start with cheap,
    deterministic CV and later swap in a local object detector without changing
    the planner/state-machine code. No network or API call is made here.
    """

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
