import pytest
from PIL import Image, ImageDraw

from resource_detector import LocalResourceDetector, ResourceCandidateConfig


def test_detector_finds_a_clear_green_fiber_candidate() -> None:
    image = Image.new("RGB", (320, 240), (30, 30, 30))
    draw = ImageDraw.Draw(image)
    draw.ellipse((145, 105, 175, 135), fill=(45, 180, 70))

    detections = LocalResourceDetector().detect(image, resources={"fiber"})

    assert detections
    assert detections[0].label == "fiber"
    assert detections[0].confidence >= 0.65
    assert 0 <= detections[0].box.x <= 1
    assert 0 <= detections[0].box.y <= 1


def test_detector_does_not_propose_dark_background() -> None:
    image = Image.new("RGB", (320, 240), (15, 15, 15))
    assert LocalResourceDetector().detect(image, resources={"fiber", "wood", "leather"}) == ()


def test_detector_ignores_resource_like_colour_outside_play_area() -> None:
    image = Image.new("RGB", (320, 240), (30, 30, 30))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 220, 80, 239), fill=(45, 180, 70))

    assert LocalResourceDetector().detect(image, resources={"fiber"}) == ()


def test_detector_rejects_unknown_resource() -> None:
    with pytest.raises(ValueError):
        LocalResourceDetector().detect(Image.new("RGB", (64, 64)), resources={"gold"})


def test_detector_rejects_invalid_component_limits() -> None:
    with pytest.raises(ValueError):
        ResourceCandidateConfig(min_component_pixels=10, max_component_pixels=5)


def test_detector_handles_component_touching_top_left_edge() -> None:
    image = Image.new("RGB", (64, 64), (30, 30, 30))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 7, 7), fill=(45, 180, 70))

    detections = LocalResourceDetector().detect(image, resources={"fiber"})

    assert detections
    assert detections[0].box.x == 0
    assert detections[0].box.y == 0
    assert 0 <= detections[0].box.width <= 1
    assert 0 <= detections[0].box.height <= 1
