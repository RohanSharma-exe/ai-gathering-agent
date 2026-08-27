from PIL import Image, ImageDraw

from albion_perception import AlbionUIObserver


def _frame(*, colored_skills: bool, load_fraction: float | None = None) -> Image.Image:
    image = Image.new("RGB", (1024, 768), (225, 145, 70))
    draw = ImageDraw.Draw(image)

    # Albion-like skill slots near the bottom-center of the game viewport.
    centers = [289, 338, 390, 444, 494, 548, 598, 648, 699, 753]
    for index, x in enumerate(centers):
        if colored_skills and 1 <= index <= 6:
            colors = [(30, 180, 70), (230, 100, 20), (40, 130, 220), (150, 50, 220)]
            fill = colors[index % len(colors)]
        else:
            fill = (105, 105, 105)
        draw.ellipse((x - 16, 719, x + 16, 751), fill=fill, outline=(45, 45, 45), width=2)

    if load_fraction is not None:
        # Inventory load bar: dark border with a variable filled interior.
        left, right = 758, 970
        top, bottom = 345, 350
        draw.rectangle((left, top, right, bottom), outline=(110, 85, 65), width=1)
        fill_right = left + round((right - left - 2) * load_fraction)
        if fill_right > left + 1:
            draw.rectangle((left + 1, top + 1, fill_right, bottom - 1), fill=(125, 75, 45))

    return image


def test_detects_mounted_when_skill_slots_are_grey() -> None:
    observation = AlbionUIObserver().observe(_frame(colored_skills=False))

    assert observation.mounted is True
    assert observation.skills_visible is False


def test_detects_unmounted_when_skill_slots_are_colored() -> None:
    observation = AlbionUIObserver().observe(_frame(colored_skills=True))

    assert observation.mounted is False
    assert observation.skills_visible is True
    assert observation.can_use_skill_bar is True


def test_detects_inventory_load_from_visible_load_bar() -> None:
    observation = AlbionUIObserver().observe(_frame(colored_skills=False, load_fraction=0.75))

    assert observation.inventory_percent >= 70
    assert observation.inventory_percent <= 80


def test_inventory_is_unknown_when_panel_is_not_visible() -> None:
    observation = AlbionUIObserver().observe(_frame(colored_skills=False))

    assert observation.inventory_percent is None
