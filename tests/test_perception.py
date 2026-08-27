from PIL import Image

from state import TargetKind
from vision import (
    BoundingBox,
    LocalPerceptionDetector,
    Observation,
    ScreenRegions,
)


def test_bounding_box_uses_normalized_coordinates() -> None:
    box = BoundingBox(0.25, 0.5, 0.5, 0.25)

    assert box.to_pixels(1920, 1080) == (480, 540, 960, 270)


def test_bounding_box_rejects_values_outside_screen() -> None:
    try:
        BoundingBox(0.0, 0.0, 1.1, 0.5)
    except ValueError:
        return
    raise AssertionError("BoundingBox should reject normalized values > 1")


def test_local_detector_returns_empty_observation_without_false_positives() -> None:
    image = Image.new("RGB", (640, 360), "black")
    detector = LocalPerceptionDetector(ScreenRegions())

    observation = detector.detect(image)

    assert isinstance(observation, Observation)
    assert observation.targets == ()
    assert observation.inventory_percent == 0


def test_observation_can_carry_confidence_and_target_kind() -> None:
    observation = Observation(
        targets=(),
        player_confidence=0.9,
        mounted_confidence=0.8,
    )

    assert observation.player_confidence == 0.9
    assert observation.mounted_confidence == 0.8
    assert TargetKind.ANIMAL.value == "animal"
