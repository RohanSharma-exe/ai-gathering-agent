from pathlib import Path

import pytest

from state import Target, TargetKind
from vision import Observation, ScreenshotVisionProvider


class RecordingDetector:
    def __init__(self) -> None:
        self.seen_size: tuple[int, int] | None = None

    def detect(self, image: object) -> Observation:
        self.seen_size = image.size
        target = Target(TargetKind.ANIMAL, "leather", 12)
        return Observation(
            area="forest",
            area_type="safe",
            inventory_percent=35,
            mounted=True,
            targets=(target,),
        )


def test_screenshot_provider_loads_image_locally(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    from PIL import Image

    screenshot = tmp_path / "screen.png"
    Image.new("RGB", (320, 180), "black").save(screenshot)

    detector = RecordingDetector()
    observation = ScreenshotVisionProvider(screenshot, detector).observe()

    assert detector.seen_size == (320, 180)
    assert observation.area == "forest"
    assert observation.targets[0].resource == "leather"


def test_screenshot_provider_rejects_missing_file(tmp_path: Path) -> None:
    detector = RecordingDetector()

    with pytest.raises(FileNotFoundError):
        ScreenshotVisionProvider(tmp_path / "missing.png", detector).observe()
