"""Fast, local visual cues for the Albion Online client.

This module deliberately uses only Pillow. It does not send mouse or keyboard
input and does not attempt semantic game understanding. The first live pass
focuses on the three cues the controller needs immediately: mounted state,
usable unmounted skills, and visible inventory load.
"""

from __future__ import annotations

from dataclasses import dataclass

from observation import UIObservation


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

    def __init__(self, config: AlbionPerceptionConfig | None = None) -> None:
        self.config = config or AlbionPerceptionConfig()

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

        # The first and last slots are utility slots and are less reliable.
        usable_slots = saturation[1:8]
        colored_slots = sum(
            value >= self.config.colored_skill_threshold for value in usable_slots
        )
        unmounted = colored_slots >= self.config.unmounted_slot_count
        return (not unmounted, unmounted)

    def _inventory_percent(self, image: object) -> float | None:
        width, height = image.size
        left = round(self.config.inventory_bar_x[0] * width)
        right = round(self.config.inventory_bar_x[1] * width)
        center_y = round(self.config.inventory_bar_y * height)

        rows: list[tuple[int, float]] = []
        for y in range(max(0, center_y - 5), min(height, center_y + 6)):
            pixels = image.crop((left, y, right + 1, y + 1)).get_flattened_data()
            if not pixels:
                continue
            dark_fraction = sum(
                0.2126 * r + 0.7152 * g + 0.0722 * b < 125
                for r, g, b in pixels
            ) / len(pixels)
            rows.append((y, dark_fraction))

        # The load bar has dark horizontal borders above and below its fill.
        border_rows = [y for y, fraction in rows if fraction >= 0.90]
        for top in border_rows:
            for bottom in border_rows:
                if 3 <= bottom - top <= 5:
                    inner_y = (top + bottom) // 2
                    pixels = image.crop(
                        (left + 2, inner_y, max(left + 3, right - 1), inner_y + 1)
                    ).get_flattened_data()
                    if not pixels:
                        return None
                    dark_fraction = sum(
                        0.2126 * r + 0.7152 * g + 0.0722 * b < 125
                        for r, g, b in pixels
                    ) / len(pixels)
                    return float(round(max(0.0, min(100.0, dark_fraction * 100.0))))
        return None

    def observe(self, image: object) -> UIObservation:
        if not hasattr(image, "size") or not hasattr(image, "convert"):
            raise TypeError("image must be Pillow-compatible")

        mounted, skills_visible = self._skill_state(image)
        return UIObservation(
            mounted=mounted,
            inventory_percent=self._inventory_percent(image),
            city_present=False,
            chest_present=False,
            skills_visible=skills_visible,
        )
