from pathlib import Path

from PIL import Image

from actions import ActionExecutor, ActionKind, ActionResult
from live_control import LiveControlConfig, LiveControlRuntime
from state import Objective, Target, TargetKind
from vision import Observation


class FakeSource:
    def __init__(self) -> None:
        self.calls = 0

    def screenshot(self, path=None):
        self.calls += 1
        image = Image.new("RGB", (1920, 1080), "black")
        if path is not None:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            image.save(path)
        return image


class RecordingExecutor(ActionExecutor):
    def __init__(self, accepted=True):
        self.accepted = accepted
        self.actions = []

    def execute(self, action):
        self.actions.append(action)
        return ActionResult(self.accepted, action, "recorded")


def test_live_runtime_dismounts_before_gathering_when_mounted():
    source = FakeSource()
    executor = RecordingExecutor()
    observations = iter(
        [
            Observation(mounted=True, mounted_confidence=1.0),
            Observation(
                mounted=False,
                mounted_confidence=1.0,
                targets=(Target(TargetKind.RESOURCE, "fiber", 0.1, 0.52, 0.48),),
            ),
        ]
    )

    runtime = LiveControlRuntime(
        source,
        lambda image: next(observations),
        executor,
        Objective("fiber"),
        LiveControlConfig(max_frames=2, dry_run=False, dismount_key="a"),
        sleep=lambda _: None,
    )

    assert runtime.run() == 2
    assert [action.kind for action in executor.actions] == [ActionKind.PRESS_KEY, ActionKind.GATHER]
    assert executor.actions[0].key == "a"
    assert (executor.actions[1].x, executor.actions[1].y) == (998, 518)


def test_live_runtime_dry_run_never_sends_real_input():
    source = FakeSource()
    executor = RecordingExecutor()
    observation = Observation(
        mounted=False,
        targets=(Target(TargetKind.RESOURCE, "fiber", 0.1, 0.5, 0.5),),
    )

    runtime = LiveControlRuntime(
        source,
        lambda image: observation,
        executor,
        Objective("fiber"),
        LiveControlConfig(max_frames=1, dry_run=True),
        sleep=lambda _: None,
    )

    assert runtime.run() == 1
    assert executor.actions == []


def test_live_runtime_stops_when_dismount_key_is_missing():
    source = FakeSource()
    executor = RecordingExecutor()
    runtime = LiveControlRuntime(
        source,
        lambda image: Observation(mounted=True, mounted_confidence=1.0),
        executor,
        Objective("fiber"),
        LiveControlConfig(max_frames=5, dry_run=False, dismount_key=None),
        sleep=lambda _: None,
    )

    assert runtime.run() == 1
    assert executor.actions == []


def test_live_runtime_stops_after_rejected_action():
    source = FakeSource()
    executor = RecordingExecutor(accepted=False)
    observation = Observation(
        mounted=False,
        targets=(Target(TargetKind.RESOURCE, "fiber", 0.1, 0.5, 0.5),),
    )
    runtime = LiveControlRuntime(
        source,
        lambda image: observation,
        executor,
        Objective("fiber"),
        LiveControlConfig(max_frames=5, dry_run=False),
        sleep=lambda _: None,
    )

    assert runtime.run() == 1
    assert len(executor.actions) == 1
