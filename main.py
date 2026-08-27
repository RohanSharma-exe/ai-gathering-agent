"""Small observe-decide-propose-verify loop for the gathering-agent brain."""

from dataclasses import dataclass

from actions import Action, ActionExecutor, ActionKind
from planner import Decision, DecisionKind, decide
from state import GameState, Objective
from vision import Observation


@dataclass(frozen=True)
class StepResult:
    state: GameState
    decision: Decision
    action: Action
    verified: bool


def state_from_observation(objective: Objective, observation: Observation) -> GameState:
    return GameState(
        objective=objective,
        inventory_percent=observation.inventory_percent,
        current_area=observation.area,
        area_type=observation.area_type,
        mounted=observation.mounted,
        nearby_targets=list(observation.targets),
    )


def action_for_decision(decision: Decision) -> Action:
    if decision.kind is DecisionKind.RETURN:
        return Action(ActionKind.RETURN_TO_STORAGE)
    if decision.kind is DecisionKind.EXPLORE:
        return Action(ActionKind.CHANGE_AREA)
    if decision.kind is DecisionKind.TARGET and decision.target is not None:
        if decision.target.kind.value == "animal":
            return Action(ActionKind.INTERACT)
        return Action(ActionKind.GATHER)
    if decision.kind is DecisionKind.COMBAT:
        return Action(ActionKind.ATTACK)
    if decision.kind is DecisionKind.GATHER:
        return Action(ActionKind.GATHER)
    return Action(ActionKind.WAIT)


def run_step(
    objective: Objective,
    observation: Observation,
    executor: ActionExecutor,
) -> StepResult:
    state = state_from_observation(objective, observation)
    decision = decide(state)
    action = action_for_decision(decision)
    result = executor.propose(action)
    return StepResult(
        state=state,
        decision=decision,
        action=action,
        verified=result.accepted,
    )
