from state import AgentState, GameState, Objective, Target, TargetKind


def test_game_state_defaults_to_idle_with_empty_inventory():
    state = GameState(objective=Objective(resource="leather"))
    assert state.agent_state is AgentState.IDLE
    assert state.inventory_percent == 0
    assert state.current_target is None


def test_inventory_threshold_is_true_at_or_above_threshold():
    state = GameState(
        objective=Objective(resource="leather"),
        inventory_percent=90,
    )
    assert state.inventory_needs_return(90) is True


def test_target_identifies_animal_as_leather_source():
    target = Target(kind=TargetKind.ANIMAL, resource="leather", distance=12.0)
    assert target.is_compatible_with(Objective(resource="leather")) is True
