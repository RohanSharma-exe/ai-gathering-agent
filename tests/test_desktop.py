from pathlib import Path

from desktop import Desktop


def test_dry_run_does_not_send_mouse_or_keyboard_input():
    desktop = Desktop(dry_run=True)

    assert desktop.click(100, 200) is False
    assert desktop.press("space") is False
    assert desktop.move_to(100, 200) is False


def test_screenshot_saves_image(monkeypatch, tmp_path: Path):
    class FakeImage:
        def save(self, path):
            Path(path).write_bytes(b"fake-image")

    class FakeGUI:
        def screenshot(self):
            return FakeImage()

    desktop = Desktop(dry_run=True)
    monkeypatch.setattr(desktop, "_load", lambda: FakeGUI())

    output = tmp_path / "screen.png"
    image = desktop.screenshot(output)

    assert image is not None
    assert output.read_bytes() == b"fake-image"
