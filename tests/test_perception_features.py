from PIL import Image

from perception import LocalFeatureExtractor
from vision import BoundingBox


def test_feature_extractor_returns_region_dimensions() -> None:
    image = Image.new("RGB", (100, 80), (100, 100, 100))
    features = LocalFeatureExtractor().region_features(
        image, BoundingBox(0.0, 0.0, 0.5, 0.5)
    )

    assert features.width == 50
    assert features.height == 40
    assert features.mean_luminance == 100
    assert features.edge_density == 0


def test_feature_extractor_detects_bright_pixels() -> None:
    image = Image.new("RGB", (20, 20), (0, 0, 0))
    image.putpixel((10, 10), (255, 255, 255))

    features = LocalFeatureExtractor().region_features(
        image, BoundingBox(0, 0, 1, 1)
    )

    assert features.bright_fraction > 0
    assert features.edge_density > 0


def test_feature_extractor_rejects_invalid_image() -> None:
    try:
        LocalFeatureExtractor().region_features("not-an-image", BoundingBox(0, 0, 1, 1))
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError")
