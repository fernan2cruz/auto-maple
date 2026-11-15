"""Tests for Routine label/jump linking, execution index handling, and compilation."""

import pytest
from src.common import config, settings
from src.common.interfaces import Configurable
from src.routine import components
from src.routine.components import Point, Label, Jump
from src.routine.routine import Routine


class FakeBot:
    def __init__(self):
        self.command_book = {'wait': components.Wait, 'walk': components.Walk}


@pytest.fixture(autouse=True)
def routine():
    config.gui = None
    config.enabled = False
    config.bot = FakeBot()
    config.routine = Routine()
    yield config.routine
    config.routine = None
    config.bot = None


def build(routine, *items):
    for item in items:
        routine.append_component(item)
    return routine


def test_jump_follows_label_after_component_before_it_is_deleted(routine):
    build(routine, Point(0.1, 0.1), Label('start'), Point(0.2, 0.2), Jump('start'))
    routine.delete_component(0)
    jump = routine[2]
    assert routine.labels['start'].index == 0
    assert jump.link is routine[0]
    assert jump.link.index == 0


def test_jump_follows_label_after_move(routine):
    build(routine, Label('a'), Point(0.1, 0.1), Jump('a'))
    routine.move_component_down(0)
    assert routine.labels['a'].index == 1
    assert routine[2].link.index == 1


def test_jump_added_after_its_label_is_bound_without_reload(routine):
    build(routine, Label('loop'), Point(0.1, 0.1))
    routine.append_component(Jump('loop'))
    assert routine[2].link is routine[0]


def test_jump_added_before_its_label_is_bound_once_label_exists(routine):
    build(routine, Jump('later'), Point(0.1, 0.1))
    assert routine[0].link is None
    routine.append_component(Label('later'))
    assert routine[0].link is routine[2]


def test_deleted_label_is_removed_and_its_jumps_are_unbound(routine):
    build(routine, Label('x'), Point(0.1, 0.1), Jump('x'))
    routine.delete_component(0)
    assert 'x' not in routine.labels
    assert routine[1].link is None
    routine.append_component(Label('x'))        # The name can be reused
    assert routine[1].link is routine[2]


def test_jump_to_deleted_label_does_not_move_index(routine):
    build(routine, Label('x'), Point(0.1, 0.1), Jump('x'))
    routine.delete_component(0)
    config.enabled = True
    routine.index = 1
    routine[1].main()
    assert routine.index == 1


def test_duplicate_label_is_rejected(routine):
    build(routine, Label('dup'))
    with pytest.raises(ValueError):
        routine.append_component(Label('dup'))
    assert len(routine) == 1


def test_label_can_be_edited_with_same_name(routine):
    build(routine, Label('same'), Jump('same'))
    assert routine.update_component(0, {'label': 'same'}) is True
    assert routine[1].link is routine[0]


def test_label_rename_rebinds_jumps_with_new_name(routine):
    build(routine, Label('old'), Jump('new'))
    assert routine.update_component(0, {'label': 'new'}) is True
    assert routine.labels == {'new': routine[0]}
    assert routine[1].link is routine[0]


def test_label_rename_to_existing_name_is_rejected(routine):
    build(routine, Label('a'), Label('b'))
    assert routine.update_component(1, {'label': 'a'}) is False
    assert routine[1].label == 'b'


def test_edited_jump_stays_bound(routine):
    build(routine, Label('a'), Jump('a'))
    assert routine.update_component(1, {'label': 'a', 'frequency': '2'}) is True
    assert routine[1].link is routine[0]


def test_delete_before_current_keeps_index_on_same_element(routine):
    build(routine, Point(0.1, 0.1), Point(0.2, 0.2), Point(0.3, 0.3))
    routine.index = 2
    current = routine[2]
    routine.delete_component(0)
    assert routine.current() is current


def test_delete_last_current_element_wraps_index(routine):
    build(routine, Point(0.1, 0.1), Point(0.2, 0.2))
    routine.index = 1
    routine.delete_component(1)
    assert routine.index == 0
    assert routine.current() is routine[0]


def test_current_on_empty_routine_is_none(routine):
    assert routine.current() is None


def test_move_keeps_index_on_same_element(routine):
    build(routine, Point(0.1, 0.1), Point(0.2, 0.2))
    routine.index = 0
    current = routine[0]
    routine.move_component_down(0)
    assert routine.current() is current
    routine.move_component_up(1)
    assert routine.current() is current


def test_step_wraps(routine):
    build(routine, Point(0.1, 0.1), Point(0.2, 0.2))
    config.enabled = True
    routine.index = 1
    routine.step()
    assert routine.index == 0


def test_load_without_file_and_without_previous_path_returns_false(routine):
    assert routine.load(None) is False


def test_compile_links_jumps_and_reports_orphan_command(routine, tmp_path, capsys):
    path = tmp_path / 'r.csv'
    path.write_text('wait, 1\n@, label=top\n*, x=0.5, y=0.5\n    wait, 0.1\n>, label=top\n')
    errors = routine.compile(str(path))
    routine.relink()
    out = capsys.readouterr().out
    assert errors == 1
    assert 'appears before any Point' in out
    assert len(routine) == 3
    assert len(routine[1].commands) == 1
    assert routine[2].link is routine[0]


def test_compile_rejects_duplicate_labels(routine, tmp_path, capsys):
    path = tmp_path / 'r.csv'
    path.write_text('@, label=a\n@, label=a\n')
    errors = routine.compile(str(path))
    assert errors == 1
    assert len(routine) == 1


def test_save_round_trip(routine, tmp_path):
    build(routine, Label('a'), Point(0.5, 0.25))
    routine.append_command(1, components.Wait(0.5))
    path = tmp_path / 'out.csv'
    routine.save(str(path))
    assert routine.path == str(path)
    assert routine.dirty is False

    other = Routine()
    config.routine = other
    assert other.compile(str(path)) == 0
    assert other.encode() == routine.encode()


def test_positive_int_validator():
    assert settings.validate_positive_int('3') == 3
    with pytest.raises(ValueError):
        settings.validate_positive_int('0')
    assert settings.validate_nonnegative_int is settings.validate_positive_int


def test_new_config_keys_fall_back_to_defaults(tmp_path):
    class Old(Configurable):
        DEFAULT_CONFIG = {'a': '1'}

    class New(Configurable):
        DEFAULT_CONFIG = {'a': '1', 'b': '2'}

    old = Old('cfg', directory=str(tmp_path))
    old.config['a'] = 'x'
    old.save_config()
    new = New('cfg', directory=str(tmp_path))
    assert new.config == {'a': 'x', 'b': '2'}
