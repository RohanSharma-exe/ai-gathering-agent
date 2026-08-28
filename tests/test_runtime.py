from pathlib import Path

from PIL import Image

from observation import UIObservation
from runtime import ObservationRuntime, RuntimeConfig


class FakeSource:
    def __init__(self) -> None:
        self.paths: list[Path | None] = []

    def screenshot(self, path=None):
        self.paths.append(Path(path) if path is not None else None)
        image = Image.new("RGB", (8, 8), "black")
        if path is not None:
            image.save(path)
        return image


def test_runtime_captures_requested_number_of_frames(tmp_path):
    source = FakeSource()
    seen = []
    runtime = ObservationRuntime(
        source,
        lambda image: UIObservation(mounted=False, skills_visible=True),
        RuntimeConfig(interval_seconds=0.01, max_frames=3, save_frames=True, output_dir=tmp_path),
        sleep=lambda _: None,
    )

    count = runtime.run(seen.append)

    assert count == 3
    assert [frame.index for frame in seen] == [0, 1, 2]
    assert all(frame.observation.can_use_skill_bar for frame in seen)
    assert len(list(tmp_path.glob("frame_*.png"))) == 3


def test_runtime_does_not_persist_frames_by_default(tmp_path):
    source = FakeSource()
    runtime = ObservationRuntime(
        source,
        lambda image: UIObservation(),
        RuntimeConfig(interval_seconds=0.01, max_frames=2, output_dir=tmp_path),
        sleep=lambda _: None,
    )

    assert runtime.run() == 2
    assert source.paths == [None, None]
    assert list(tmp_path.iterdir()) == []


def test_runtime_does_not_sleep_after_final_frame():
    source = FakeSource()
    sleeps = []
    runtime = ObservationRuntime(
        source,
        lambda image: UIObservation(),
        RuntimeConfig(interval_seconds=0.25, max_frames=1),
        sleep=sleeps.append,
    )

    assert runtime.run() == 1
    assert sleeps == []


def test_runtime_rejects_invalid_interval():
    try:
        RuntimeConfig(interval_seconds=0)
    except ValueError as exc:
        assert "positive" in str(exc)
    else:
        raise AssertionError("expected ValueError")
