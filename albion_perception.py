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
        """Estimate load-bar fill using color distance from its unfilled tail."""
        width, height = image.size
        left = round(self.config.inventory_bar_x[0] * width)
        right = round(self.config.inventory_bar_x[1] * width)
        center_y = round(self.config.inventory_bar_y * height)
        if right - left < 20 or not (0 <= center_y < height):
            return None

        best: tuple[float, float] | None = None
        for y in range(max(0, center_y - 6), min(height, center_y + 7)):
            row = image.crop((left, y, right + 1, y + 1)).convert("RGB").get_flattened_data()
            if len(row) < 20:
                continue
            tail_n = max(8, len(row) // 5)
            tail = row[-tail_n:]
            ref = tuple(sum(p[channel] for p in tail) / len(tail) for channel in range(3))
            distances = [sum((p[channel] - ref[channel]) ** 2 for channel in range(3)) ** 0.5 for p in row]
            contrast = max(distances)
            if contrast < 25:
                continue

            threshold = max(18.0, contrast * 0.30)
            prefix = 0
            for distance in distances:
                if distance < threshold:
                    break
                prefix += 1

            if prefix < 2:
                continue

            # A genuine partial bar has a clear transition to the unfilled
            # tail. Estimate its fill from that transition. For a full bar,
            # require the left side to differ strongly from the right-side UI.
            if prefix >= len(row) - 2:
                left_mean = tuple(sum(p[channel] for p in row[:tail_n]) / tail_n for channel in range(3))
                left_right_distance = sum((left_mean[channel] - ref[channel]) ** 2 for channel in range(3)) ** 0.5
                if left_right_distance < 25:
                    continue
                percent = 100.0
            else:
                percent = prefix / len(row) * 100.0

            # Prefer a substantial, clean prefix over incidental UI contrast.
            score = min(contrast / 100.0, 2.0) + min(prefix / len(row), 1.0)
            if best is None or score > best[0]:
                best = (score, percent)

        if best is None:
            return None
        return float(round(max(0.0, min(100.0, best[1]))))

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
