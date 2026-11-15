"""Tests for Layout path finding, persistence, and restricted pickle loading."""

import io
import os
import pickle
import pytest
from src.common import config, settings, safe_pickle
from src.common.interfaces import Configurable
from src.routine import layout as layout_module
from src.routine.layout import Layout, LAYOUT_PICKLE_CLASSES


@pytest.fixture(autouse=True)
def enabled():
    config.gui = None
    config.enabled = True       # Layout.add/save only run while the bot is enabled
    settings.reset()
    yield
    config.enabled = False


def horizontal_layout(y=0.5):
    layout = Layout('test')
    x = 0.1
    while x <= 0.9:
        layout.add(round(x, 3), y)
        x += 0.05
    return layout


def test_shortest_path_walks_towards_target_along_layout():
    layout = horizontal_layout()
    path = layout.shortest_path((0.1, 0.5), (0.9, 0.5))
    assert path[0] == (0.1, 0.5)
    assert path[-1] == (0.9, 0.5)
    xs = [p[0] for p in path]
    assert xs == sorted(xs)
    for a, b in zip(path, path[1:]):
        assert b[0] - a[0] <= settings.move_tolerance * 2 + 1e-9
    assert config.path == path


def test_shortest_path_without_points_goes_straight_to_target():
    path = Layout('empty').shortest_path((0.1, 0.1), (0.8, 0.8))
    assert path == [(0.1, 0.1), (0.8, 0.8)]


def test_shortest_path_when_already_at_target():
    layout = horizontal_layout()
    path = layout.shortest_path((0.5, 0.5), (0.52, 0.5))
    assert path == [(0.5, 0.5), (0.52, 0.5)]


def test_layout_round_trip_through_restricted_loader(tmp_path, monkeypatch):
    monkeypatch.setattr(layout_module, 'get_layouts_dir', lambda: str(tmp_path))
    layout = horizontal_layout()
    assert layout.changed is True
    layout.save()
    assert layout.changed is False

    loaded = Layout.load('routines/test.csv')
    assert isinstance(loaded, Layout)
    assert [tuple(n) for n in loaded.search(0, 1, 0, 1)] == [tuple(n) for n in layout.search(0, 1, 0, 1)]


def test_tampered_layout_is_rejected_and_file_kept(tmp_path, monkeypatch):
    monkeypatch.setattr(layout_module, 'get_layouts_dir', lambda: str(tmp_path))
    target = tmp_path / 'evil'
    payload = pickle.dumps(Exploit())
    target.write_bytes(payload)

    loaded = Layout.load('evil.csv')
    assert isinstance(loaded, Layout) and loaded.root is None
    assert target.read_bytes() == payload               # The original file is not overwritten


class Exploit:
    def __reduce__(self):
        return (os.system, ('echo pwned',))


def test_safe_pickle_refuses_code_execution():
    data = pickle.dumps(Exploit())
    with pytest.raises(pickle.UnpicklingError):
        safe_pickle.load(io.BytesIO(data))


def test_safe_pickle_loads_plain_data_and_allowed_classes():
    assert safe_pickle.load(io.BytesIO(pickle.dumps({'a': 1, 'b': [True, None]}))) == {'a': 1, 'b': [True, None]}
    layout = Layout('x')
    restored = safe_pickle.load(io.BytesIO(pickle.dumps(layout)), LAYOUT_PICKLE_CLASSES)
    assert restored.name == 'x'


def test_tampered_settings_file_falls_back_to_defaults(tmp_path):
    class Cfg(Configurable):
        DEFAULT_CONFIG = {'Start/stop': 'insert'}

    (tmp_path / 'cfg').write_bytes(pickle.dumps(Exploit()))
    assert Cfg('cfg', directory=str(tmp_path)).config == {'Start/stop': 'insert'}
