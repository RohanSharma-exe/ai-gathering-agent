from PIL import Image

from perception import FrameComparator


def test_identical_frames_have_zero_change():
    image = Image.new("RGB", (100, 80), (20, 30, 40))

    result = FrameComparator().compare(image, image.copy())

    assert result.changed is False
    assert result.change_score == 0.0


def test_small_pixel_change_is_below_threshold():
    previous = Image.new("RGB", (100, 80), (20, 30, 40))
    current = previous.copy()
    current.putpixel((50, 40), (21, 31, 41))

    result = FrameComparator(threshold=0.05).compare(previous, current)

    assert result.changed is False
    assert 0.0 < result.change_score < 0.05


def test_large_region_change_is_detected():
    previous = Image.new("RGB", (100, 80), (20, 30, 40))
    current = Image.new("RGB", (100, 80), (220, 220, 220))

    result = FrameComparator(threshold=0.05).compare(previous, current)

    assert result.changed is True
    assert result.change_score > 0.05


def test_different_dimensions_are_rejected():
    previous = Image.new("RGB", (100, 80), (20, 30, 40))
    current = Image.new("RGB", (120, 80), (20, 30, 40))

    try:
        FrameComparator().compare(previous, current)
    except ValueError as exc:
        assert "dimensions" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError for different dimensions")
