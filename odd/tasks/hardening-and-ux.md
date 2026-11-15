Objective: fix logic gaps, harden runtime/security, and improve the Tkinter UI/UX of auto-maple.
Branch: feat/hardening-and-ux. Delivery: ask-on-risk. Test runner: pytest (tests/), run from a scratch venv.

## Specs

- S1 (Phase 1, core logic): Labels/Jumps stay correct after any routine mutation (insert, move, delete, edit); `routine.index` stays valid after delete/move; `Routine.load(None)` does not crash; commands before the first Point are reported, not silently dropped; new keybinding keys fall back to their default.
- S2 (Phase 1, GUI bugs): Update menu opens the right submodule; Record keeps at most 20 entries; stealing a key from another action never leaves two actions bound to the same key.
- S3 (Phase 1, silent failures): clear messages and no infinite hang when the TF model is missing, the MapleStory window is not found, minimap calibration fails, or a command book raises any exception.
- S4 (Phase 2, threading): all Tk widget work runs on the Tk main thread.
- S5 (Phase 2, security/deps): pinned requirements and Python version; submodules are not auto-updated at startup and `stash clear` is not used; pickle loading is restricted.
- S6 (Phase 2, tests): pytest coverage for Routine and Layout.shortest_path.
- S7 (Phase 3, UX feedback): in-GUI status/log bar, bot enabled indicator and Start/Stop button.
- S8 (Phase 3, data safety): close guard for unsaved changes, Save vs Save As, Ctrl+S/O/N shortcuts, dirty `*` in title, confirm before delete.
- S9 (Phase 3, layout/theme): resizable window, theme with dark mode, tooltips, arrow-key navigation.
- S10 (Phase 3, editor): typed/validated editor fields, non-blocking key capture, search placeholder fix.

Assumption: pickle stays as the on-disk format (with a restricted unpickler) instead of JSON, to remain compatible with the community layouts in the auto-maple-resources submodule.

## Tasks

| ID | Specs | Route | Status | Commit |
|----|-------|-------|--------|--------|
| T1 | S1, S6 | inline | done | 3235fa1 |
| T2 | S2, S3 | inline | done | 2076396 |
| T3 | S4 | inline | done | 0987f08 |
| T4 | S5, S6 | inline | done | 1c288d4, 1d62c92 |
| T5 | S7, S8 | inline | done | 8dd7961 |
| T6 | S9, S10 | inline | done | ac68bf9 |

## Log

- L1 (2026-11-15): "ahora análiza el repositorio, y recomiendame mejoras y busca huecos lógicos. tambien si se podria mejorar el ui/ux. haz la propuesta." → proposal delivered in 3 phases.
- L2 (2026-11-15): "procede con las 3 fases"
- L3 (2026-11-15): T1-T6 implemented on feat/hardening-and-ux. pytest: 33 passed (scratch venv, Python 3.12). RED observed for T1 tests against base. GUI smoke tests (real Tk window, scratch copy) passed for T3, T5, T6.
- L4 (2026-11-15): T4 (security, item 2): user granted native review, but the reviewer could not run ("Claude Code cannot be launched inside another Claude Code session"). Independent verifier: S5 PASS, S6 PASS, no blockers; advisories A (offline fetch) and C (clone option injection) fixed in 1d62c92.
- L5 (2026-11-15): Not verified: running against the real game (MapleStory window, TensorFlow model, rune solving). Minimap canvases still have a fixed 400x300 size. Restricted unpickler checked against the one layout in auto-maple-resources.
