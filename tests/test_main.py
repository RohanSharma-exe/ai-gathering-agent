from actions import ActionKind, ActionResult
from main import run_step
from state import Objective, Target, TargetKind
from vision import Observation


class RecordingExecutor:
    def __init__(self):
        self.actions = []

    def propose(self, action):
        self.actions.append(action)
        return ActionResult(accepted=True, action=action, message="recorded")


def test_run_step_observes_plans_and_proposes_nearest_leather_target():
    observation = Observation(
        area="forest",
        area_type="safe",
        inventory_percent=20,
        mounted=True,
        targets=(Target(TargetKind.ANIMAL, "leather", 12),),
    )
    executor = RecordingExecutor()

    result = run_step(Objective("leather"), observation, executor)

    assert result.decision.target.distance == 12
    assert executor.actions[0].kind is ActionKind.INTERACT
    assert result.verified is True


def test_run_step_proposes_return_when_inventory_is_full():
    observation = Observation(area="forest", inventory_percent=95)
    executor = RecordingExecutor()

    result = run_step(Objective("leather"), observation, executor)

    assert executor.actions[0].kind is ActionKind.RETURN_TO_STORAGE
    assert result.verified is True
