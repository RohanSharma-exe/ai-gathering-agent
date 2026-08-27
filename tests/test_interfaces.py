from actions import Action, ActionExecutor, ActionKind, ActionResult
from state import Target, TargetKind
from vision import Observation, VisionProvider


def test_observation_contains_only_current_visual_state():
    target = Target(TargetKind.ANIMAL, "leather", 10)
    observation = Observation(
        area="forest",
        area_type="safe",
        inventory_percent=20,
        mounted=True,
        targets=(target,),
    )
    assert observation.area == "forest"
    assert observation.targets == (target,)


def test_safe_action_executor_returns_a_test_result_without_side_effects():
    executor = ActionExecutor()
    result = executor.propose(Action(ActionKind.GATHER))
    assert isinstance(result, ActionResult)
    assert result.accepted is True
    assert result.action.kind is ActionKind.GATHER


def test_vision_provider_returns_an_observation():
    observation = Observation(area="forest", area_type="safe")
    provider = VisionProvider(observation)
    assert provider.observe() == observation
