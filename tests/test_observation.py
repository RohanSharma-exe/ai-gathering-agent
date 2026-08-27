import pytest

from observation import UIObservation, should_prepare_for_storage


def test_inventory_at_100_percent_is_full() -> None:
    observation = UIObservation(inventory_percent=100)
    assert observation.inventory_full is True
    assert should_prepare_for_storage(observation) is True


def test_inventory_above_100_percent_is_also_full() -> None:
    observation = UIObservation(inventory_percent=105)
    assert observation.inventory_full is True


def test_city_chest_is_storage_destination() -> None:
    observation = UIObservation(city_present=True, chest_present=True)
    assert observation.storage_destination_visible is True
    assert should_prepare_for_storage(observation) is True


def test_chest_without_city_is_not_storage_destination() -> None:
    observation = UIObservation(chest_present=True)
    assert observation.storage_destination_visible is False


def test_unmounted_character_can_use_visible_skill_bar() -> None:
    observation = UIObservation(mounted=False, skills_visible=True)
    assert observation.can_use_skill_bar is True


def test_mounted_character_does_not_report_skill_use_state() -> None:
    observation = UIObservation(mounted=True, skills_visible=True)
    assert observation.can_use_skill_bar is False


def test_unknown_mount_state_does_not_claim_skill_use() -> None:
    observation = UIObservation(skills_visible=True)
    assert observation.can_use_skill_bar is False


def test_negative_inventory_is_rejected() -> None:
    with pytest.raises(ValueError):
        UIObservation(inventory_percent=-1)
