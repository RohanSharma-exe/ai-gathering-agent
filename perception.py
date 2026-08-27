"""Cheap, local image features used before any learned detector."""

from dataclasses import dataclass

from vision import BoundingBox


@dataclass(frozen=True)
class RegionFeatures:
    """Small numerical summary of a screen region."""

    width: int
    height: int
    mean_luminance: float
    edge_density: float
    bright_fraction: float


class LocalFeatureExtractor:
    """Extract inexpensive image statistics with Pillow only.

    These features are deliberately generic. They are useful for deciding
    whether a UI region changed enough to inspect, without invoking an LLM or
    a heavyweight model on every frame.
    """

    def __init__(self, resize_max: int = 1280) -> None:
        if resize_max < 1:
            raise ValueError("resize_max must be positive")
        self.resize_max = resize_max

    def region_features(self, image: object, box: BoundingBox) -> RegionFeatures:
        if not hasattr(image, "convert") or not hasattr(image, "crop"):
            raise TypeError("image must provide Pillow-compatible convert and crop")

        rgb = image.convert("RGB")
        if max(rgb.size) > self.resize_max:
            scale = self.resize_max / max(rgb.size)
            rgb = rgb.resize((max(1, round(rgb.width * scale)), max(1, round(rgb.height * scale))))

        x, y, width, height = box.to_pixels(rgb.width, rgb.height)
        width = max(1, min(width, rgb.width - x))
        height = max(1, min(height, rgb.height - y))
        crop = rgb.crop((x, y, x + width, y + height))

        pixels = list(crop.get_flattened_data())
        if not pixels:
            return RegionFeatures(crop.width, crop.height, 0.0, 0.0, 0.0)

        luminance = [0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in pixels]
        mean_luminance = sum(luminance) / len(luminance)
        bright_fraction = sum(value >= 210 for value in luminance) / len(luminance)

        # A tiny horizontal/vertical gradient estimate. This avoids OpenCV and
        # is sufficient as a cheap change/texture signal.
        edge_hits = 0
        comparisons = 0
        for row in range(crop.height):
            for col in range(crop.width):
                index = row * crop.width + col
                if col + 1 < crop.width:
                    edge_hits += abs(luminance[index] - luminance[index + 1]) >= 28
                    comparisons += 1
                if row + 1 < crop.height:
                    edge_hits += abs(luminance[index] - luminance[index + crop.width]) >= 28
                    comparisons += 1

        edge_density = edge_hits / comparisons if comparisons else 0.0
        return RegionFeatures(crop.width, crop.height, mean_luminance, edge_density, bright_fraction)


@dataclass(frozen=True)
class FrameChange:
    """Result of comparing two same-sized screenshots."""

    changed: bool
    change_score: float


class FrameComparator:
    """Cheap normalized pixel-difference comparator.

    The score is in the 0..1 range and represents the mean RGB difference
    normalized to the full 8-bit channel range. It is intended as a gate for
    deeper local perception, not as a semantic understanding of the scene.
    """

    def __init__(self, threshold: float = 0.05) -> None:
        if not 0 <= threshold <= 1:
            raise ValueError("threshold must be between 0 and 1")
        self.threshold = threshold

    def compare(self, previous: object, current: object) -> FrameChange:
        if not hasattr(previous, "size") or not hasattr(current, "size"):
            raise TypeError("frames must be Pillow-compatible images")
        if previous.size != current.size:
            raise ValueError("frames must have identical dimensions")

        first = previous.convert("RGB")
        second = current.convert("RGB")
        pixel_count = first.width * first.height
        if pixel_count == 0:
            return FrameChange(changed=False, change_score=0.0)

        total_difference = 0.0
        for left, right in zip(first.get_flattened_data(), second.get_flattened_data()):
            total_difference += sum(abs(a - b) for a, b in zip(left, right)) / (3 * 255)

        score = total_difference / pixel_count
        return FrameChange(changed=score >= self.threshold, change_score=score)
