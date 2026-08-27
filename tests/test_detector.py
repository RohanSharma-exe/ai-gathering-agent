import pytest
from PIL import Image

from detector import Detection, EmptyDetector, filter_detections
from vision import BoundingBox


def detection(label: str, confidence: float) -> Detection:
    return Detection(label, confidence, BoundingBox(0.1, 0.2, 0.2, 0.2))


def test_detection_normalizes_label_and_source() -> None:
    item = Detection("  Animal ", 0.9, BoundingBox(0.1, 0.2, 0.2, 0.2), " Local-CV ")
    assert item.label == "animal"
    assert item.source == "local-cv"


def test_filter_by_confidence() -> None:
    items = (detection("animal", 0.9), detection("resource", 0.4))
    assert filter_detections(items, minimum_confidence=0.5) == (items[0],)


def test_filter_by_labels_is_case_insensitive() -> None:
    items = (detection("animal", 0.9), detection("resource", 0.9))
    assert filter_detections(items, labels={"ANIMAL"}) == (items[0],)


def test_filter_without_labels_keeps_all_confident_detections() -> None:
    items = (detection("animal", 0.8), detection("resource", 0.7))
    assert filter_detections(items, minimum_confidence=0.5) == items


def test_invalid_confidence_is_rejected() -> None:
    with pytest.raises(ValueError):
        detection("animal", 1.1)


def test_empty_detector_is_deterministic() -> None:
    assert EmptyDetector().detect(Image.new("RGB", (32, 32))) == ()


def test_empty_detector_rejects_non_image_like_input() -> None:
    with pytest.raises(TypeError):
        EmptyDetector().detect(object())
