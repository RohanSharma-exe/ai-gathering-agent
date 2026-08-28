"""Fast, local visual cues for the Albion Online client."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from observation import UIObservation
from resource_detector import LocalResourceDetector
from state import Target, TargetKind


@dataclass(frozen=True)
class AlbionPerceptionConfig:
    """Normalized regions for the current Albion 4:3 client layout."""

    skill_centers: tuple[tuple[float, float], ...] = (
        (0.282, 0.961), (0.330, 0.961), (0.381, 0.961), (0.434, 0.961),
        (0.483, 0.961), (0.535, 0.961), (0.584, 0.961), (0.633, 0.961),
        (0.683, 0.961), (0.735, 0.961),
    )
    inventory_bar_x: tuple[float, float] = (0.742, 0.950)
    inventory_bar_y: float = 0.454
    colored_skill_threshold: float = 0.60
    unmounted_slot_count: int = 3


class AlbionUIObserver:
    """Extract conservative Albion UI state from one game-client image."""

    _DETECTABLE_RESOURCES = frozenset({"wood", "fiber", "leather"})

    def __init__(self, config: AlbionPerceptionConfig | None = None, resource_detector: LocalResourceDetector | None = None) -> None:
        self.config = config or AlbionPerceptionConfig()
        self.resource_detector = resource_detector or LocalResourceDetector()

    @staticmethod
    def _mean_saturation(image: object, box: tuple[int, int, int, int]) -> float:
        hsv = image.convert("HSV").crop(box)
        pixels = hsv.get_flattened_data()
        if not pixels:
            return 0.0
        usable = [s / 255.0 for _, s, value in pixels if value > 45]
        return sum(usable) / len(usable) if usable else 0.0

    def _skill_state(self, image: object) -> tuple[bool, bool]:
        width, height = image.size
        radius = max(3, round(min(width, height) * 0.012))
        saturation = []
        for normalized_x, normalized_y in self.config.skill_centers:
            center_x = round(normalized_x * width)
            center_y = round(normalized_y * height)
            box = (max(0, center_x - radius), max(0, center_y - radius), min(width, center_x + radius + 1), min(height, center_y + radius + 1))
            saturation.append(self._mean_saturation(image, box))
        usable_slots = saturation[1:8]
        colored_slots = sum(value >= self.config.colored_skill_threshold for value in usable_slots)
        unmounted = colored_slots >= self.config.unmounted_slot_count
        return (not unmounted, unmounted)

    def _inventory_percent(self, image: object) -> float | None:
        """Estimate the load-bar fill from a stable horizontal scanline.

        The detector deliberately returns ``None`` when the configured region
        does not contain a convincing bar. It never converts uncertainty into
        a fake 0% or 100% value.
        """
        width, height = image.size
        left = round(self.config.inventory_bar_x[0] * width)
        right = round(self.config.inventory_bar_x[1] * width)
        center_y = round(self.config.inventory_bar_y * height)
        if right - left < 20 or not (0 <= center_y < height):
            return None

        # Search nearby rows for the strongest horizontal bar-like contrast.
        best: tuple[float, int] | None = None
        for y in range(max(0, center_y - 6), min(height, center_y + 7)):
            row = image.crop((left, y, right, y + 1)).convert("RGB").get_flattened_data()
            if len(row) < 20:
                continue
            # A real bar has a relatively stable right-side background and a
            # contiguous region on the left with a different appearance.
            split = max(5, len(row) // 5)
            ref = row[-split:]
            ref_luma = sum(0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in ref) / len(ref)
            ref_sat = sum(max(r, g, b) - min(r, g, b) for r, g, b in ref) / len(ref)
            scores = []
            for r, g, b in row:
                luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
                sat = max(r, g, b) - min(r, g, b)
                scores.append(min(1.0, abs(luma - ref_luma) / 35.0 + abs(sat - ref_sat) / 55.0))
            prefix = 0
            for score in scores:
                if score < 0.45:
                    break
                prefix += 1
            if prefix < 2:
                continue
            # Reject a uniformly different strip: a genuine partial bar needs
            # an unfilled tail comparable to the reference.
            if prefix >= len(scores) - 2:
                # It may be full, but only accept if the reference itself is
                # sufficiently distinct from the left side.
                left_luma = sum(0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in row[:split]) / split
                if abs(left_luma - ref_luma) < 25:
                    continue
                percent = 100.0
            else:
                percent = prefix / len(scores) * 100.0

            quality = min(1.0, abs(percent - 50.0) / 50.0) + scores[min(prefix, len(scores) - 1)]
            if best is None or quality > best[0]:
                best = (quality, round(percent))

        return None if best is None else float(max(0, min(100, best[1])))

    def _targets(self, image: object, resources: set[str] | None) -> tuple[Target, ...]:
        wanted = self._DETECTABLE_RESOURCES if resources is None else {item.strip().lower() for item in resources}
        wanted &= self._DETECTABLE_RESOURCES
        if not wanted:
            return ()
        detections = self.resource_detector.detect(image, resources=wanted)
        targets = []
        for detection in detections:
            screen_x = detection.box.x + detection.box.width / 2
            screen_y = detection.box.y + detection.box.height / 2
            distance = hypot(screen_x - 0.5, screen_y - 0.5)
            targets.append(Target(TargetKind.RESOURCE, detection.label, distance, screen_x, screen_y))
        return tuple(sorted(targets, key=lambda target: target.distance))

    def observe(self, image: object, *, resources: set[str] | None = None) -> UIObservation:
        if not hasattr(image, "size") or not hasattr(image, "convert"):
            raise TypeError("image must be Pillow-compatible")
        rgb = image.convert("RGB")
        mounted, skills_visible = self._skill_state(rgb)
        return UIObservation(
            mounted=mounted,
            inventory_percent=self._inventory_percent(rgb),
            city_present=False,
            chest_present=False,
            skills_visible=skills_visible,
            targets=self._targets(rgb, resources),
        )
