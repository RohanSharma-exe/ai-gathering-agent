from planner import DecisionKind, decide, planner_state_for
from state import AgentState, GameState, Objective, Target, TargetKind


def test_leather_objective_targets_nearest_animal():
    state = GameState(
        objective=Objective("leather"),
        nearby_targets=[
            Target(TargetKind.ANIMAL, "leather", 25),
            Target(TargetKind.ANIMAL, "leather", 10),
            Target(TargetKind.RESOURCE, "fiber", 3),
        ],
    )
    decision = decide(state)
    assert decision.kind is DecisionKind.TARGET
    assert decision.target.distance == 10


def test_everything_can_target_nearest_compatible_resource():
    state = GameState(
        objective=Objective("everything"),
        nearby_targets=[
            Target(TargetKind.RESOURCE, "ore", 20),
            Target(TargetKind.ANIMAL, "leather", 8),
        ],
    )
    decision = decide(state)
    assert decision.kind is DecisionKind.TARGET
    assert decision.target.distance == 8


def test_full_inventory_returns_before_targeting():
    state = GameState(
        objective=Objective("leather"),
        inventory_percent=90,
        nearby_targets=[Target(TargetKind.ANIMAL, "leather", 1)],
    )
    assert decide(state).kind is DecisionKind.RETURN


def test_no_target_explores():
    state = GameState(objective=Objective("leather"))
    assert decide(state).kind is DecisionKind.EXPLORE


def test_forbidden_area_never_produces_target_decision():
    state = GameState(
        objective=Objective("leather"),
        area_type="forbidden",
        nearby_targets=[Target(TargetKind.ANIMAL, "leather", 1)],
    )
    decision = decide(state)
    assert decision.kind is DecisionKind.EXPLORE


def test_animal_target_enters_combat_state():
    state = GameState(
        objective=Objective("leather"),
        nearby_targets=[Target(TargetKind.ANIMAL, "leather", 5)],
    )
    decision = decide(state)
    assert planner_state_for(decision) is AgentState.COMBAT


def test_resource_target_enters_gathering_state():
    state = GameState(
        objective=Objective("fiber"),
        nearby_targets=[Target(TargetKind.RESOURCE, "fiber", 5)],
    )
    decision = decide(state)
    assert planner_state_for(decision) is AgentState.GATHERING
