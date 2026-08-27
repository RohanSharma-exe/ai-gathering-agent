from state import Objective, TargetKind
from targets import TargetCandidate, TargetDetector, choose_nearest, filter_candidates
from vision import BoundingBox


def candidate(resource: str, x: float, y: float, confidence: float = 0.9, kind: TargetKind = TargetKind.RESOURCE) -> TargetCandidate:
    return TargetCandidate(kind, resource, BoundingBox(x, y, 0.1, 0.1), confidence)


def test_candidate_normalizes_resource_and_estimates_center() -> None:
    item = candidate("  Leather ", 0.2, 0.3, kind=TargetKind.ANIMAL)
    assert item.resource == "leather"
    assert item.center == (0.25, 0.35)
    assert item.estimated_distance() > 0


def test_filter_accepts_matching_resource() -> None:
    items = (candidate("leather", 0.2, 0.2), candidate("ore", 0.3, 0.3))
    result = filter_candidates(items, Objective("leather"))
    assert result == (items[0],)


def test_filter_everything_accepts_all_available_candidates() -> None:
    items = (
        candidate("leather", 0.2, 0.2),
        candidate("ore", 0.3, 0.3),
        candidate("fiber", 0.4, 0.4),
    )
    assert filter_candidates(items, Objective("everything")) == items


def test_filter_rejects_unavailable_and_low_confidence() -> None:
    unavailable = candidate("leather", 0.2, 0.2)
    unavailable = TargetCandidate(
        unavailable.kind, unavailable.resource, unavailable.box, unavailable.confidence, available=False
    )
    low = candidate("leather", 0.3, 0.3, confidence=0.4)
    assert filter_candidates((unavailable, low), Objective("leather")) == ()


def test_choose_nearest_uses_screen_space_distance() -> None:
    near = candidate("leather", 0.45, 0.45)
    far = candidate("leather", 0.0, 0.0)
    assert choose_nearest((far, near)) is near


def test_choose_nearest_returns_none_for_empty_input() -> None:
    assert choose_nearest(()) is None


def test_detector_is_safe_empty_scaffold() -> None:
    from PIL import Image

    assert TargetDetector().detect(Image.new("RGB", (10, 10))) == ()


def test_candidate_rejects_invalid_confidence() -> None:
    try:
        candidate("leather", 0.2, 0.2, confidence=1.1)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
