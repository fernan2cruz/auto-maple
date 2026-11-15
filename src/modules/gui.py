"""User friendly GUI to interact with Auto Maple."""

import os
import time
import queue
import threading
import traceback
import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import askyesnocancel
from src.common import config, settings
from src.common.interfaces import Configurable
from src.gui import Menu, View, Edit, Settings
from src.gui.interfaces import Tooltip
from src.gui.menu.file import File

try:
    import sv_ttk       # Optional modern ttk theme with light and dark variants
except ImportError:
    sv_ttk = None


# Colors applied to classic Tk widgets (Listbox, Entry, Text, Label) for each theme
PALETTES = {
    'light': dict(background='#fafafa', foreground='#1c1c1c', activeBackground='#e5e5e5',
                  activeForeground='#1c1c1c', selectBackground='#005fb8', selectForeground='#ffffff',
                  insertBackground='#1c1c1c', highlightColor='#005fb8', disabledForeground='#9e9e9e',
                  troughColor='#e5e5e5'),
    'dark': dict(background='#1c1c1c', foreground='#fafafa', activeBackground='#2f2f2f',
                 activeForeground='#fafafa', selectBackground='#2f60d8', selectForeground='#ffffff',
                 insertBackground='#fafafa', highlightColor='#57c8ff', disabledForeground='#7a7a7a',
                 troughColor='#2f2f2f'),
}


class Appearance(Configurable):
    DEFAULT_CONFIG = {
        'Dark theme': False
    }


class GUI:
    DISPLAY_FRAME_RATE = 30
    QUEUE_POLL_MS = 15
    STATE_POLL_MS = 200
    INFO_MESSAGE_MS = 8000
    RESOLUTIONS = {
        'DEFAULT': '800x800',
        'Edit': '1400x800'
    }

    def __init__(self):
        config.gui = self
        self._tasks = queue.Queue()         # Callables posted by worker threads
        self._clear_message_job = None

        self.root = tk.Tk()
        self.root.title('Auto Maple')
        icon = tk.PhotoImage(file='assets/icon.png')
        self.root.iconphoto(False, icon)
        self.root.geometry(GUI.RESOLUTIONS['DEFAULT'])
        self.root.minsize(760, 600)
        self._auto_size = None          # Last size set automatically; None once the user resizes
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)

        # Initialize GUI variables
        self.routine_var = tk.StringVar()
        self.appearance = Appearance('appearance')
        self.dark_theme = tk.BooleanVar(value=bool(self.appearance.config['Dark theme']))

        # Build the GUI
        self.menu = Menu(self.root)
        self.root.config(menu=self.menu)
        view_menu = tk.Menu(self.menu, tearoff=0)
        view_menu.add_checkbutton(label='Dark theme', variable=self.dark_theme,
                                  command=self._on_theme_toggle)
        self.menu.add_cascade(label='View', menu=view_menu)

        self._build_status_bar()
        self.apply_theme(self.dark_theme.get())

        self.navigation = ttk.Notebook(self.root)

        self.view = View(self.navigation)
        self.edit = Edit(self.navigation)
        self.settings = Settings(self.navigation)

        self.navigation.pack(expand=True, fill='both')
        self.navigation.bind('<<NotebookTabChanged>>', self._resize_window)
        self._bind_shortcuts()
        self.update_title()
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

    #############################
    #       Status bar          #
    #############################
    def _build_status_bar(self):
        bar = ttk.Frame(self.root, padding=(8, 4))
        bar.pack(side=tk.BOTTOM, fill='x')
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(side=tk.BOTTOM, fill='x')

        self.state_label = tk.Label(bar, text='', width=10, anchor=tk.W, font=('Segoe UI', 9, 'bold'))
        self.state_label.pack(side=tk.LEFT)

        self.toggle_button = ttk.Button(bar, text='Start', width=8, command=self.toggle_bot)
        self.toggle_button.pack(side=tk.LEFT, padx=(4, 12))
        Tooltip(self.toggle_button, 'Start or stop the bot (same as the Start/stop hotkey)')

        self.message_label = tk.Label(bar, text='Ready', anchor=tk.W)
        self.message_label.pack(side=tk.LEFT, fill='x', expand=True)
        self._default_fg = self.message_label.cget('fg')
        self._shown_state = None

    def apply_theme(self, dark):
        """Applies the light or dark theme to both ttk and classic Tk widgets."""

        name = 'dark' if dark else 'light'
        if sv_ttk is not None:
            sv_ttk.set_theme(name, root=self.root)
        self.root.tk_setPalette(**PALETTES[name])
        self._default_fg = PALETTES[name]['foreground']
        if self.message_label.cget('fg') != '#c62828':      # Keep error messages red
            self.message_label.config(fg=self._default_fg)
        self._shown_state = None        # Repaint the Running/Stopped indicator

    def _on_theme_toggle(self):
        dark = self.dark_theme.get()
        self.apply_theme(dark)
        self.appearance.config['Dark theme'] = dark
        self.appearance.save_config()

    def show_message(self, message, level='info'):
        """Shows MESSAGE in the status bar. Errors stay visible, info messages fade out."""

        colors = {'error': '#c62828', 'info': self._default_fg}
        self.message_label.config(text=message, fg=colors.get(level, self._default_fg))
        if self._clear_message_job is not None:
            self.root.after_cancel(self._clear_message_job)
            self._clear_message_job = None
        if level != 'error':
            self._clear_message_job = self.root.after(
                GUI.INFO_MESSAGE_MS, lambda: self.message_label.config(text='')
            )

    def _refresh_state(self):
        """Keeps the Running/Stopped indicator in sync with the bot."""

        enabled = config.enabled
        if enabled != self._shown_state:
            self._shown_state = enabled
            if enabled:
                self.state_label.config(text='● Running', fg='#2e7d32')
                self.toggle_button.config(text='Stop')
            else:
                self.state_label.config(text='● Stopped', fg='#757575')
                self.toggle_button.config(text='Start')
        self.root.after(GUI.STATE_POLL_MS, self._refresh_state)

    def toggle_bot(self):
        """Starts or stops the bot, like the Start/stop hotkey."""

        if not config.enabled and (config.bot is None or config.bot.command_book is None):
            self.show_message('Load a command book and a routine before starting.', 'error')
            return
        if not config.enabled and len(config.routine) == 0:
            self.show_message('The routine is empty. Load or create a routine before starting.', 'error')
            return
        # Toggling recalibrates the minimap and beeps, which takes a moment: keep the UI responsive
        from src.modules.listener import Listener
        threading.Thread(target=Listener.toggle_enabled, daemon=True).start()

    #################################
    #       Title and shortcuts     #
    #################################
    def update_title(self):
        routine = config.routine
        name = os.path.basename(routine.path) if routine is not None and routine.path else 'untitled'
        dirty = '*' if routine is not None and routine.dirty else ''
        self.root.title(f'Auto Maple - {name}{dirty}')

    def _bind_shortcuts(self):
        def bind(sequence, action):
            def handler(_):
                action()
                return 'break'
            self.root.bind_all(sequence, handler)

        bind('<Control-s>', File.save_routine)
        bind('<Control-S>', File.save_routine_as)       # Ctrl+Shift+S
        bind('<Control-o>', File.load_routine)
        bind('<Control-n>', File.new_routine)

    def on_close(self):
        """Asks to save unsaved routine changes before closing the window."""

        if config.routine is not None and config.routine.dirty:
            answer = askyesnocancel(title='Quit Auto Maple',
                                    message='The current routine has unsaved changes. '
                                            'Do you want to save them before quitting?',
                                    icon='warning')
            if answer is None:
                return
            if answer and not File.save_routine():
                return
        self.root.destroy()

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
        self.update_title()

    def _resize_window(self, e):
        """Callback to resize entire Tkinter window every time a new Page is selected."""

        nav = e.widget
        curr_id = nav.select()
        nav.nametowidget(curr_id).focus()      # Focus the current Tab
        page = nav.tab(curr_id, 'text')
        if self.root.state() == 'zoomed':
            return
        width, height = map(int, GUI.RESOLUTIONS.get(page, GUI.RESOLUTIONS['DEFAULT']).split('x'))
        self.root.update_idletasks()
        current = (self.root.winfo_width(), self.root.winfo_height())
        if self._auto_size is not None and current != self._auto_size:
            # The user resized the window: only grow it if the page needs more room
            width, height = max(width, current[0]), max(height, current[1])
        if (width, height) != current:
            self.root.geometry(f'{width}x{height}')
            self.root.update_idletasks()
        self._auto_size = (self.root.winfo_width(), self.root.winfo_height())

    def start(self):
        """Starts the GUI as well as any scheduled functions."""

        layout_thread = threading.Thread(target=self._save_layout)
        layout_thread.daemon = True
        layout_thread.start()

        self.root.after(0, self._process_tasks)
        self.root.after(0, self._display_minimap)
        self.root.after(0, self._refresh_state)
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
