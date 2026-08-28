"""Fast, local visual cues for the Albion Online client.

This module deliberately uses only Pillow. It does not send mouse or keyboard
input. The live pass extracts mounted state, usable unmounted skills, visible
inventory load, and conservative resource candidates for the controller.
"""

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
        (0.282, 0.961),
        (0.330, 0.961),
        (0.381, 0.961),
        (0.434, 0.961),
        (0.483, 0.961),
        (0.535, 0.961),
        (0.584, 0.961),
        (0.633, 0.961),
        (0.683, 0.961),
        (0.735, 0.961),
    )
    inventory_bar_x: tuple[float, float] = (0.742, 0.950)
    inventory_bar_y: float = 0.454
    colored_skill_threshold: float = 0.60
    unmounted_slot_count: int = 3


class AlbionUIObserver:
    """Extract conservative Albion UI state from one game-client image."""

    _DETECTABLE_RESOURCES = frozenset({"wood", "fiber", "leather"})

    def __init__(
        self,
        config: AlbionPerceptionConfig | None = None,
        resource_detector: LocalResourceDetector | None = None,
    ) -> None:
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
            box = (
                max(0, center_x - radius),
                max(0, center_y - radius),
                min(width, center_x + radius + 1),
                min(height, center_y + radius + 1),
            )
            saturation.append(self._mean_saturation(image, box))

        usable_slots = saturation[1:8]
        colored_slots = sum(
            value >= self.config.colored_skill_threshold for value in usable_slots
        )
        unmounted = colored_slots >= self.config.unmounted_slot_count
        return (not unmounted, unmounted)

    def _inventory_percent(self, image: object) -> float | None:
        """Estimate the load-bar fill, or return None when the bar is uncertain.

        The old implementation classified every dark pixel inside a candidate
        row as filled. That can mistake unrelated dark UI elements for a full
        load bar and produced false 100% readings in the live client. This
        version looks for a pair of horizontal borders and then compares the
        colored fill region against the unfilled right side of the same bar.
        """
        width, height = image.size
        left = round(self.config.inventory_bar_x[0] * width)
        right = round(self.config.inventory_bar_x[1] * width)
        center_y = round(self.config.inventory_bar_y * height)

        if right - left < 20:
            return None

        rows: list[tuple[int, float]] = []
        for y in range(max(0, center_y - 7), min(height, center_y + 8)):
            pixels = image.crop((left, y, right + 1, y + 1)).get_flattened_data()
            if not pixels:
                continue
            dark_fraction = sum(
                0.2126 * r + 0.7152 * g + 0.0722 * b < 125
                for r, g, b in pixels
            ) / len(pixels)
            rows.append((y, dark_fraction))

        border_pairs: list[tuple[int, int]] = []
        for index, (top, top_dark) in enumerate(rows):
            if top_dark < 0.80:
                continue
            for bottom, bottom_dark in rows[index + 1 :]:
                if 3 <= bottom - top <= 5 and bottom_dark >= 0.80:
                    border_pairs.append((top, bottom))

        if not border_pairs:
            return None

        top, bottom = border_pairs[0]
        inner_y = (top + bottom) // 2
        inner = image.crop((left + 2, inner_y, right - 1, inner_y + 1)).convert("HSV")
        pixels = inner.get_flattened_data()
        if len(pixels) < 20:
            return None

        # Use the rightmost 20% as the local unfilled reference. A candidate
        # must differ from that reference enough to avoid calling an unrelated
        # uniformly dark strip a 100% load bar.
        split = max(5, len(pixels) // 5)
        right_ref = pixels[-split:]
        ref_sat = sum(s for _, s, _ in right_ref) / len(right_ref)
        ref_value = sum(v for _, _, v in right_ref) / len(right_ref)

        scores: list[float] = []
        for saturation, value in ((s, v) for _, s, v in pixels):
            sat_delta = abs(saturation - ref_sat)
            value_delta = abs(value - ref_value)
            scores.append(min(1.0, (sat_delta / 45.0) + (value_delta / 90.0)))

        # Require a substantial left-to-right transition. If the whole bar is
        # visually uniform, its fill percentage is unknown rather than 100%.
        threshold = 0.35
        filled = [score >= threshold for score in scores]
        transition = next((i for i, value in enumerate(filled) if not value), None)
        if transition is None:
            # A genuinely full bar can have no transition, but only accept it
            # when the left side is also consistently different from the right.
            left_sample = scores[: max(5, len(scores) // 5)]
            if sum(left_sample) / len(left_sample) < threshold:
                return None
            return 100.0

        if transition == 0:
            return 0.0

        # The fill is expected to be contiguous from the left edge. If there
        # are too many alternating pixels, this is not a reliable load bar.
        contiguous = 0
        for value in filled:
            if not value:
                break
            contiguous += 1
        if contiguous < max(2, len(filled) // 100):
            return 0.0
        if any(filled[contiguous + 3 :]):
            return None

        percent = contiguous / len(filled) * 100.0
        return float(round(max(0.0, min(100.0, percent))))

    def _targets(
        self,
        image: object,
        resources: set[str] | None,
    ) -> tuple[Target, ...]:
        wanted = self._DETECTABLE_RESOURCES if resources is None else {
            item.strip().lower() for item in resources
        }
        wanted &= self._DETECTABLE_RESOURCES
        if not wanted:
            return ()

        detections = self.resource_detector.detect(image, resources=wanted)
        targets = []
        for detection in detections:
            screen_x = detection.box.x + detection.box.width / 2
            screen_y = detection.box.y + detection.box.height / 2
            distance = hypot(screen_x - 0.5, screen_y - 0.5)
            targets.append(
                Target(
                    TargetKind.RESOURCE,
                    detection.label,
                    distance,
                    screen_x,
                    screen_y,
                )
            )
        return tuple(sorted(targets, key=lambda target: target.distance))

    def observe(
        self,
        image: object,
        *,
        resources: set[str] | None = None,
    ) -> UIObservation:
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
