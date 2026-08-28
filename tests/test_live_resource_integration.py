from PIL import Image, ImageDraw

from actions import ActionExecutor
from live_control import LiveControlConfig, LiveControlRuntime
from live_run import _desktop_targets, observe_factory
from state import Objective, Target, TargetKind
from vision import Observation


class FakeSource:
    def __init__(self, image: Image.Image) -> None:
        self.image = image
        self.calls = 0

    def screenshot(self):
        self.calls += 1
        return self.image.copy()


class RecordingExecutor(ActionExecutor):
    def __init__(self) -> None:
        self.actions = []

    def execute(self, action):
        self.actions.append(action)
        return super().execute(action)


def _wood_frame() -> Image.Image:
    image = Image.new("RGB", (320, 240), (30, 30, 30))
    draw = ImageDraw.Draw(image)
    draw.ellipse((135, 80, 185, 145), fill=(120, 80, 40))
    return image


def test_live_observer_maps_visible_wood_to_a_gather_target(monkeypatch) -> None:
    # observe_factory normally crops a real Albion window. This unit/integration
    # fixture is already a client-sized image, so keep it unchanged even when
    # Albion happens to be open on the test machine.
    monkeypatch.setattr("live_run.crop_albion_client", lambda image: image)
    _, observe = observe_factory("wood")

    observation = observe(_wood_frame())

    assert observation.targets
    assert observation.targets[0].resource == "wood"
    assert observation.targets[0].screen_x is not None
    assert observation.targets[0].screen_y is not None


def test_live_runner_maps_client_coordinates_to_desktop_coordinates(monkeypatch) -> None:
    monkeypatch.setattr(
        "live_run.albion_client_rect",
        lambda: (100, 50, 900, 650),
    )
    target = Target(TargetKind.RESOURCE, "wood", 0.1, 0.5, 0.4)

    mapped = _desktop_targets((target,), Image.new("RGB", (1000, 800)))

    assert mapped[0].screen_x == 0.5
    assert mapped[0].screen_y == 0.3625


def test_live_runtime_stops_before_input_when_inventory_is_full() -> None:
    source = FakeSource(_wood_frame())
    executor = RecordingExecutor()
    observation = Observation(
        mounted=True,
        inventory_percent=99.0,
        targets=(),
        mounted_confidence=1.0,
    )

    runtime = LiveControlRuntime(
        source,
        lambda image: observation,
        executor,
        Objective("wood"),
        LiveControlConfig(max_frames=5, dry_run=False, inventory_return_threshold=90),
        sleep=lambda _: None,
    )

    assert runtime.run() == 1
    assert executor.actions == []
