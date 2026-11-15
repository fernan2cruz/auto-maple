import os
import tkinter as tk
from src.common import config, utils
from src.gui.interfaces import MenuBarItem
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter.messagebox import askyesno, askyesnocancel


class File(MenuBarItem):
    ROUTINE_ENTRIES = ('New Routine', 'Save Routine', 'Save Routine As...', 'Load Routine')

    def __init__(self, parent, **kwargs):
        super().__init__(parent, 'File', **kwargs)

        self.add_command(label='New Routine', command=File.new_routine,
                         accelerator='Ctrl+N', state=tk.DISABLED)
        self.add_command(label='Save Routine', command=File.save_routine,
                         accelerator='Ctrl+S', state=tk.DISABLED)
        self.add_command(label='Save Routine As...', command=File.save_routine_as,
                         accelerator='Ctrl+Shift+S', state=tk.DISABLED)
        self.add_separator()
        self.add_command(label='Load Command Book', command=File.load_commands)
        self.add_command(label='Load Routine', command=File.load_routine,
                         accelerator='Ctrl+O', state=tk.DISABLED)

    def enable_routine_state(self):
        for label in File.ROUTINE_ENTRIES:
            self.entryconfig(label, state=tk.NORMAL)

    @staticmethod
    def routine_actions_available():
        """Routine actions need a loaded command book; reports why when they are not available."""

        if config.bot is None or config.bot.command_book is None:
            utils.report_error('Load a command book first (File > Load Command Book).')
            return False
        return True

    @staticmethod
    def confirm_discard(title):
        """
        Asks what to do with unsaved changes. Returns True if it is safe to continue
        (changes saved or discarded), False if the user cancelled.
        """

        if not config.routine.dirty:
            return True
        answer = askyesnocancel(title=title,
                                message='The current routine has unsaved changes. '
                                        'Do you want to save them first?',
                                icon='warning')
        if answer is None:
            return False
        if answer:
            return bool(File.save_routine())
        return True

    @staticmethod
    @utils.run_if_disabled('Cannot create a new routine while Auto Maple is enabled.')
    def new_routine():
        if not File.routine_actions_available() or not File.confirm_discard('New Routine'):
            return
        config.routine.clear()

    @staticmethod
    @utils.run_if_disabled('Cannot save routines while Auto Maple is enabled.')
    def save_routine():
        """Saves to the routine's current file, or asks for one. Returns True if it was saved."""

        if not File.routine_actions_available():
            return False
        if config.routine.path:
            return File._save_to(config.routine.path)
        return File._ask_and_save()

    @staticmethod
    @utils.run_if_disabled('Cannot save routines while Auto Maple is enabled.')
    def save_routine_as():
        if File.routine_actions_available():
            File._ask_and_save()

    @staticmethod
    def _ask_and_save():
        file_path = asksaveasfilename(initialdir=get_routines_dir(),
                                      title='Save routine',
                                      filetypes=[('*.csv', '*.csv')],
                                      defaultextension='*.csv')
        if not file_path:
            return False
        return File._save_to(file_path)

    @staticmethod
    def _save_to(file_path):
        try:
            config.routine.save(file_path)
            return True
        except OSError as e:
            utils.report_error(f"Could not save routine: {e}")
            return False

    @staticmethod
    @utils.run_if_disabled('Cannot load routines while Auto Maple is enabled.')
    def load_routine():
        if not File.routine_actions_available() or not File.confirm_discard('Load Routine'):
            return
        file_path = askopenfilename(initialdir=get_routines_dir(),
                                    title='Select a routine',
                                    filetypes=[('*.csv', '*.csv')])
        if file_path:
            config.routine.load(file_path)

    @staticmethod
    @utils.run_if_disabled('Cannot load command books while Auto Maple is enabled.')
    def load_commands():
        if config.routine.dirty:
            if not askyesno(title='Load Command Book',
                            message='Loading a new command book will discard the current routine, '
                                    'which has unsaved changes. Would you like to proceed anyways?',
                            icon='warning'):
                return
        file_path = askopenfilename(initialdir=os.path.join(config.RESOURCES_DIR, 'command_books'),
                                    title='Select a command book',
                                    filetypes=[('*.py', '*.py')])
        if file_path:
            config.bot.load_commands(file_path)


def get_routines_dir():
    target = os.path.join(config.RESOURCES_DIR, 'routines', config.bot.command_book.name)
    if not os.path.exists(target):
        os.makedirs(target)
    return target
