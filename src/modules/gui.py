"""User friendly GUI to interact with Auto Maple."""

import time
import queue
import threading
import traceback
import tkinter as tk
from tkinter import ttk
from src.common import config, settings
from src.gui import Menu, View, Edit, Settings


class GUI:
    DISPLAY_FRAME_RATE = 30
    QUEUE_POLL_MS = 15
    RESOLUTIONS = {
        'DEFAULT': '800x800',
        'Edit': '1400x800'
    }

    def __init__(self):
        config.gui = self
        self._tasks = queue.Queue()         # Callables posted by worker threads

        self.root = tk.Tk()
        self.root.title('Auto Maple')
        icon = tk.PhotoImage(file='assets/icon.png')
        self.root.iconphoto(False, icon)
        self.root.geometry(GUI.RESOLUTIONS['DEFAULT'])
        self.root.resizable(False, False)

        # Initialize GUI variables
        self.routine_var = tk.StringVar()

        # Build the GUI
        self.menu = Menu(self.root)
        self.root.config(menu=self.menu)

        self.navigation = ttk.Notebook(self.root)

        self.view = View(self.navigation)
        self.edit = Edit(self.navigation)
        self.settings = Settings(self.navigation)

        self.navigation.pack(expand=True, fill='both')
        self.navigation.bind('<<NotebookTabChanged>>', self._resize_window)
        self.root.focus()

    #################################
    #       Thread-safe access      #
    #################################
    def post(self, func, *args, **kwargs):
        """
        Runs FUNC on the Tk main thread. Called directly when already on the main thread,
        otherwise queued and executed by the main loop. Safe to call from any thread.
        """

        if threading.current_thread() is threading.main_thread():
            func(*args, **kwargs)
        else:
            self._tasks.put((func, args, kwargs))

    def _process_tasks(self):
        """Executes every queued task on the main thread, then reschedules itself."""

        try:
            while True:
                func, args, kwargs = self._tasks.get_nowait()
                try:
                    func(*args, **kwargs)
                except Exception:
                    print('\n[!] Error while updating the GUI:')
                    traceback.print_exc()
        except queue.Empty:
            pass
        self.root.after(GUI.QUEUE_POLL_MS, self._process_tasks)

    def set_routine(self, arr):
        self.routine_var.set(arr)

    def clear_routine_info(self):
        """
        Clears information in various GUI elements regarding the current routine.
        Does not clear Listboxes containing routine Components, as that is handled by Routine.
        """

        self.view.details.clear_info()
        self.view.status.set_routine('')

        self.edit.minimap.redraw()
        self.edit.routine.commands.clear_contents()
        self.edit.routine.commands.update_display()
        self.edit.editor.reset()

    def _resize_window(self, e):
        """Callback to resize entire Tkinter window every time a new Page is selected."""

        nav = e.widget
        curr_id = nav.select()
        nav.nametowidget(curr_id).focus()      # Focus the current Tab
        page = nav.tab(curr_id, 'text')
        if self.root.state() != 'zoomed':
            if page in GUI.RESOLUTIONS:
                self.root.geometry(GUI.RESOLUTIONS[page])
            else:
                self.root.geometry(GUI.RESOLUTIONS['DEFAULT'])

    def start(self):
        """Starts the GUI as well as any scheduled functions."""

        layout_thread = threading.Thread(target=self._save_layout)
        layout_thread.daemon = True
        layout_thread.start()

        self.root.after(0, self._process_tasks)
        self.root.after(0, self._display_minimap)
        self.root.mainloop()

    def _display_minimap(self):
        """Redraws the live minimap on the main thread at DISPLAY_FRAME_RATE."""

        try:
            self.view.minimap.display_minimap()
        except Exception:
            traceback.print_exc()
        self.root.after(1000 // GUI.DISPLAY_FRAME_RATE, self._display_minimap)

    def _save_layout(self):
        """Periodically saves the current Layout object when it has unsaved points."""

        while True:
            layout = config.layout
            if layout is not None and settings.record_layout and getattr(layout, 'changed', True):
                layout.save()
            time.sleep(5)


if __name__ == '__main__':
    gui = GUI()
    gui.start()
