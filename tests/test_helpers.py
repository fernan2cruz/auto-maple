"""Tests for pure helper functions used by capture and the keybinding editor."""

from types import SimpleNamespace
import numpy as np
from src.common import utils
from src.gui.interfaces import tk_event_to_key


def key(keysym):
    return tk_event_to_key(SimpleNamespace(keysym=keysym))


def test_tk_keysyms_map_to_keyboard_library_names():
    assert key('a') == 'a'
    assert key('F6') == 'f6'
    assert key('Insert') == 'insert'
    assert key('Prior') == 'page up'
    assert key('Control_L') == 'ctrl'
    assert key('space') == 'space'
    assert key('comma') == ','
    assert key('KP_5') == '5'


def test_match_score_finds_template_and_rejects_noise():
    rng = np.random.default_rng(0)
    frame = rng.integers(0, 255, (60, 80, 3), dtype=np.uint8)
    template = frame[10:20, 30:45, 0].copy()
    gray_frame = np.repeat(frame[:, :, :1], 3, axis=2)       # Gray image stored as BGR
    assert utils.match_score(gray_frame, template) > 0.99

    other = rng.integers(0, 255, (60, 80, 3), dtype=np.uint8)
    assert utils.match_score(other, template) < 0.6


def test_match_score_with_template_larger_than_frame():
    frame = np.zeros((5, 5, 3), dtype=np.uint8)
    template = np.zeros((10, 10), dtype=np.uint8)
    assert utils.match_score(frame, template) == -1.0


def test_start_stop_runs_once_for_simultaneous_requests_and_held_key(monkeypatch):
    import threading
    import time
    import types
    import src.modules.listener as listener_module
    from src.common import config

    calls = []

    def slow_toggle():
        calls.append(1)
        config.enabled = not config.enabled
        time.sleep(0.2)

    monkeypatch.setattr(listener_module.Listener, '_toggle_enabled', staticmethod(slow_toggle))
    threads = [threading.Thread(target=listener_module.Listener.toggle_enabled) for _ in range(5)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(calls) == 1

    calls.clear()
    monkeypatch.setattr(listener_module, 'kb', types.SimpleNamespace(is_pressed=lambda k: k == 'insert'))
    listener = listener_module.Listener.__new__(listener_module.Listener)
    listener.config = {'Start/stop': 'insert', 'Reload routine': 'f6', 'Record position': 'f7'}
    listener.enabled, listener.block_time, listener.ready = True, 0, False
    threading.Thread(target=listener._main, daemon=True).start()
    time.sleep(1.0)                     # Key held down the whole time
    listener.enabled = False
    assert len(calls) == 1
    config.enabled = False
