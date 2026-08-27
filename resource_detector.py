"""Fast, conservative resource-candidate detection from Albion screenshots.

This module deliberately detects *candidates*, not certainty. It uses only Pillow
and coarse colour/shape signals, ignores configured HUD regions, and emits a
candidate only when the visual evidence clears the configured confidence gate.
It never sends game input.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from config import PerceptionConfig, ScreenRegions, SUPPORTED_RESOURCES
from detector import Detection
from vision import BoundingBox


@dataclass(frozen=True)
class ResourceCandidateConfig:
    """Thresholds for the lightweight resource candidate detector."""

    minimum_confidence: float = 0.65
    sample_size: int = 320
    min_component_pixels: int = 8
    max_component_pixels: int = 6000

    def __post_init__(self) -> None:
        if not 0 <= self.minimum_confidence <= 1:
            raise ValueError("minimum_confidence must be between 0 and 1")
        if self.sample_size < 32:
            raise ValueError("sample_size must be at least 32")
        if self.min_component_pixels < 1:
            raise ValueError("min_component_pixels must be positive")
        if self.max_component_pixels < self.min_component_pixels:
            raise ValueError("max_component_pixels must be >= min_component_pixels")


class LocalResourceDetector:
    """Detect coarse resource-like colour blobs in the playable area.

    The detector is intentionally conservative. It is useful as a first-pass
    target proposal layer; downstream planning must still verify the target
    before interacting with it.
    """

    _HUE_RANGES = {
        "fiber": ((0.20, 0.46),),
        "wood": ((0.04, 0.16),),
        "leather": ((0.02, 0.10),),
    }

    def __init__(
        self,
        regions: ScreenRegions | None = None,
        perception: PerceptionConfig | None = None,
        config: ResourceCandidateConfig | None = None,
    ) -> None:
        self.regions = regions or ScreenRegions()
        self.perception = perception or PerceptionConfig()
        self.config = config or ResourceCandidateConfig(
            minimum_confidence=self.perception.minimum_confidence
        )

    def detect(
        self,
        image: object,
        *,
        resources: set[str] | None = None,
    ) -> tuple[Detection, ...]:
        if not hasattr(image, "convert") or not hasattr(image, "size"):
            raise TypeError("image must provide Pillow-compatible convert and size")

        wanted = {item.strip().lower() for item in (resources or set(SUPPORTED_RESOURCES))}
        unknown = wanted - set(SUPPORTED_RESOURCES)
        if unknown:
            raise ValueError(f"unsupported resources: {sorted(unknown)}")

        rgb = image.convert("RGB")
        scale = min(1.0, self.config.sample_size / max(rgb.width, rgb.height))
        if scale < 1:
            rgb = rgb.resize(
                (max(1, round(rgb.width * scale)), max(1, round(rgb.height * scale)))
            )

        play = self.regions.play_area
        x0 = round(play[0] * rgb.width)
        y0 = round(play[1] * rgb.height)
        x1 = min(rgb.width, round((play[0] + play[2]) * rgb.width))
        y1 = min(rgb.height, round((play[1] + play[3]) * rgb.height))
        if x1 <= x0 or y1 <= y0:
            return ()

        # Work on a compact pixel grid. This is intentionally not an OCR or
        # object-recognition system: only broad colour clusters are proposed.
        hsv = rgb.convert("HSV")
        width = rgb.width
        pixels = hsv.load()
        candidates: list[Detection] = []
        for resource in wanted:
            if resource not in self._HUE_RANGES:
                continue
            mask = self._build_mask(pixels, width, x0, y0, x1, y1, resource)
            for component in self._components(mask, x1 - x0, y1 - y0):
                if not self.config.min_component_pixels <= len(component) <= self.config.max_component_pixels:
                    continue
                detection = self._component_detection(
                    component, resource, x0, y0, rgb.width, rgb.height
                )
                if detection.confidence >= self.config.minimum_confidence:
                    candidates.append(detection)

        return tuple(sorted(candidates, key=lambda item: item.confidence, reverse=True))

    def _build_mask(self, pixels, width, x0, y0, x1, y1, resource: str) -> bytearray:
        size = (x1 - x0) * (y1 - y0)
        mask = bytearray(size)
        ranges = self._HUE_RANGES[resource]
        for y in range(y0, y1):
            row = (y - y0) * (x1 - x0)
            for x in range(x0, x1):
                h, s, v = pixels[x, y]
                hue = h / 255.0
                # Resource candidates need visible colour, while very dark
                # pixels are rejected to avoid most terrain/UI shadows.
                in_hue = any(low <= hue <= high for low, high in ranges)
                coloured = s >= 55 and v >= 45
                mask[row + (x - x0)] = 1 if in_hue and coloured else 0
        return mask

    @staticmethod
    def _components(mask: bytearray, width: int, height: int) -> list[list[tuple[int, int]]]:
        seen = bytearray(len(mask))
        result: list[list[tuple[int, int]]] = []
        for y in range(height):
            for x in range(width):
                start = y * width + x
                if not mask[start] or seen[start]:
                    continue
                stack = [(x, y)]
                seen[start] = 1
                component: list[tuple[int, int]] = []
                while stack:
                    cx, cy = stack.pop()
                    component.append((cx, cy))
                    for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                        if 0 <= nx < width and 0 <= ny < height:
                            index = ny * width + nx
                            if mask[index] and not seen[index]:
                                seen[index] = 1
                                stack.append((nx, ny))
                result.append(component)
        return result

    def _component_detection(
        self,
        component: list[tuple[int, int]],
        resource: str,
        x_offset: int,
        y_offset: int,
        width: int,
        height: int,
    ) -> Detection:
        xs = [point[0] for point in component]
        ys = [point[1] for point in component]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        box_width = max_x - min_x + 1
        box_height = max_y - min_y + 1
        area = box_width * box_height
        fill = len(component) / area
        compactness = min(1.0, len(component) / 120.0)
        shape = 1.0 - min(1.0, abs(box_width - box_height) / max(box_width, box_height, 1))
        confidence = min(0.99, 0.45 + 0.30 * fill + 0.15 * compactness + 0.10 * shape)

        # Distance is intentionally a normalized visual proxy, not game-world
        # distance. The planner should treat it only as a ranking signal.
        center_x = x_offset + (min_x + max_x) / 2
        center_y = y_offset + (min_y + max_y) / 2
        distance = hypot(center_x - width / 2, center_y - height / 2) / hypot(width, height)
        return Detection(
            resource,
            confidence,
            BoundingBox(
                center_x / width - (box_width / width) / 2,
                center_y / height - (box_height / height) / 2,
                box_width / width,
                box_height / height,
            ),
            source="local-resource-cv",
        )
