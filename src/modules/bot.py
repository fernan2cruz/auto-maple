"""An interpreter that reads and executes user-created routines."""

import os
import threading
import time
import git
import cv2
import inspect
import importlib
import traceback
from os.path import splitext, basename
from src.common import config, utils
from src.detection import detection
from src.routine import components
from src.routine.routine import Routine
from src.command_book.command_book import CommandBook
from src.routine.components import Point
from src.common.vkeys import press, click
from src.common.interfaces import Configurable


# The rune's buff icon
RUNE_BUFF_TEMPLATE = cv2.imread('assets/rune_buff_template.jpg', 0)


class Bot(Configurable):
    """A class that interprets and executes user-defined routines."""

    DEFAULT_CONFIG = {
        'Interact': 'y',
        'Feed pet': '9'
    }

    def __init__(self):
        """Loads a user-defined routine on start up and initializes this Bot's main thread."""

        super().__init__('keybindings')
        config.bot = self

        self.rune_active = False
        self.rune_pos = (0, 0)
        self.rune_closest_pos = (0, 0)      # Location of the Point closest to rune
        self.submodules = []
        self.command_book = None            # CommandBook instance
        # self.module_name = None
        # self.buff = components.Buff()

        # self.command_book = {}
        # for c in (components.Wait, components.Walk, components.Fall,
        #           components.Move, components.Adjust, components.Buff):
        #     self.command_book[c.__name__.lower()] = c

        config.routine = Routine()

        self.ready = False
        self.thread = threading.Thread(target=self._main)
        self.thread.daemon = True

    def start(self):
        """
        Starts this Bot object's thread.
        :return:    None
        """

        self.init_submodules()
        print('\n[~] Started main bot loop')
        self.thread.start()

    def _main(self):
        """
        The main body of Bot that executes the user's routine.
        :return:    None
        """

        print('\n[~] Initializing detection algorithm:\n')
        try:
            model = detection.load_model()
            print('\n[~] Initialized detection algorithm')
        except Exception as e:      # Usually the model folder was not downloaded
            model = None
            utils.report_error(
                'Rune solver disabled: could not load the TensorFlow model from '
                "'assets/models'. Download it as described in the README. "
                f'Details: {e.__class__.__name__}: {e}'
            )

        self.ready = True
        config.listener.enabled = True
        last_fed = time.time()
        while True:
            if config.enabled and len(config.routine) > 0:
                # Buff and feed pets
                self.command_book.buff.main()
                pet_settings = config.gui.settings.pets.pet_settings
                auto_feed = pet_settings.get('Auto-feed')
                num_pets = max(1, int(pet_settings.get('Num pets') or 1))
                now = time.time()
                if auto_feed and now - last_fed > 1200 / num_pets:
                    press(self.config['Feed pet'], 1)
                    last_fed = now

                # Execute next Point in the routine
                with config.routine.lock:
                    element = config.routine.current()
                    index = config.routine.index
                if element is None:
                    continue

                # Highlight the current Point
                utils.gui_call(config.gui.view.routine.select, index)
                utils.gui_call(config.gui.view.details.display_info, index)

                if self.rune_active and isinstance(element, Point) \
                        and element.location == self.rune_closest_pos:
                    self._solve_rune(model)
                element.execute()
                config.routine.step()
            else:
                time.sleep(0.01)

    @utils.run_if_enabled
    def _solve_rune(self, model):
        """
        Moves to the position of the rune and solves the arrow-key puzzle.
        :param model:   The TensorFlow model to classify with.
        :param sct:     The mss instance object with which to take screenshots.
        :return:        None
        """

        if model is None:
            print('\n[!] Skipping rune: the rune solver model is not loaded.')
            self.rune_active = False
            return

        move = self.command_book['move']
        move(*self.rune_pos).execute()
        adjust = self.command_book['adjust']
        adjust(*self.rune_pos).execute()
        time.sleep(0.2)
        press(self.config['Interact'], 1, down_time=0.2)        # Inherited from Configurable

        print('\nSolving rune:')
        inferences = []
        for _ in range(15):
            frame = config.capture.frame
            solution = detection.merge_detection(model, frame)
            if solution:
                print(', '.join(solution))
                if solution in inferences:
                    print('Solution found, entering result')
                    for arrow in solution:
                        press(arrow, 1, down_time=0.1)
                    time.sleep(1)
                    for _ in range(3):
                        time.sleep(0.3)
                        frame = config.capture.frame
                        rune_buff = utils.multi_match(frame[:frame.shape[0] // 8, :],
                                                      RUNE_BUFF_TEMPLATE,
                                                      threshold=0.9)
                        if rune_buff:
                            rune_buff_pos = min(rune_buff, key=lambda p: p[0])
                            target = (
                                round(rune_buff_pos[0] + config.capture.window['left']),
                                round(rune_buff_pos[1] + config.capture.window['top'])
                            )
                            click(target, button='right')
                    self.rune_active = False
                    break
                elif len(solution) == 4:
                    inferences.append(solution)

    def load_commands(self, file):
        try:
            self.command_book = CommandBook(file)
        except ValueError:
            utils.report_error(f"Command book '{basename(file)}' was not loaded, see console for details.")
            return False
        utils.gui_call(config.gui.settings.update_class_bindings)
        utils.report_info(f"Loaded command book '{self.command_book.name}'.")
        return True

    @staticmethod
    def read_submodules():
        """Returns a list of (path, url) tuples declared in .gitmodules."""

        result = []
        if not os.path.isfile('.gitmodules'):
            return result
        with open('.gitmodules', 'r') as file:
            lines = file.readlines()
        i = 0
        while i < len(lines):
            if lines[i].startswith('[') and i < len(lines) - 2:
                path = lines[i + 1].split('=')[1].strip()
                url = lines[i + 2].split('=')[1].strip()
                result.append((path, url))
                i += 3
            else:
                i += 1
        return result

    def init_submodules(self):
        """
        Downloads submodules that are missing. Existing submodules are never changed on start-up,
        so local edits are safe and no remote code is pulled without the user asking for it.
        Use the 'Update' menu to update them.
        """

        utils.print_separator()
        print('[~] Checking submodules:')
        self.submodules = []
        for path, url in Bot.read_submodules():
            self.submodules.append(path)
            if os.path.isdir(path) and os.listdir(path):
                print(f" -  Found submodule '{path}' (use the Update menu to update it)")
                continue
            try:
                git.Git('.').clone('--', url, path)
                print(f" -  Initialized submodule '{path}'")
            except git.exc.GitCommandError as e:
                utils.report_error(f"Could not download submodule '{path}': {e}")

    def update_submodules(self, force=False):
        """
        Pulls updates from the submodule repositories. If FORCE is True,
        rebuilds submodules by overwriting all local changes. Otherwise local changes
        to tracked files are re-applied on top of the update.
        """

        utils.print_separator()
        print('[~] Retrieving latest submodules:')
        self.submodules = []
        for path, url in Bot.read_submodules():
            self.submodules.append(path)
            if not (os.path.isdir(path) and os.listdir(path)):
                try:
                    git.Git('.').clone('--', url, path)     # First time loading submodule
                    print(f" -  Initialized submodule '{path}'")
                except git.exc.GitCommandError as e:
                    utils.report_error(f"Could not download submodule '{path}': {e}")
                continue

            sub_repo = git.Repo(path)
            keep_changes = not force and sub_repo.is_dirty()
            try:
                sub_repo.git.fetch('origin', 'main')        # Fetch first: nothing changes if offline
            except git.exc.GitCommandError as e:
                utils.report_error(f"Could not update submodule '{path}': {e}")
                continue
            if keep_changes:
                sub_repo.git.stash('push', '-m', 'auto-maple update')
            sub_repo.git.reset('--hard', 'FETCH_HEAD')
            if force:
                print(f" -  Rebuilt submodule '{path}'")
            elif keep_changes:
                try:        # Local versions of modified files win over the update
                    sub_repo.git.checkout('stash@{0}', '--', '.')
                    sub_repo.git.stash('drop')
                    print(f" -  Updated submodule '{path}', restored local changes")
                except git.exc.GitCommandError:
                    print(f" !  Updated submodule '{path}', but could not restore local changes. "
                          f"They are kept in 'git stash list' inside '{path}'.")
            else:
                print(f" -  Updated submodule '{path}'")
