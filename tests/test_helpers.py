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
