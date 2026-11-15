"""Interfaces that are used by various GUI pages."""

import tkinter as tk
from tkinter import ttk
from src.common import utils
from src.common.interfaces import Configurable


# Tk keysyms whose name differs from the name used by the 'keyboard' library
_KEYSYM_TO_KEY = {
    'prior': 'page up', 'next': 'page down', 'return': 'enter', 'escape': 'esc',
    'control_l': 'ctrl', 'control_r': 'ctrl', 'shift_l': 'shift', 'shift_r': 'shift',
    'alt_l': 'alt', 'alt_r': 'alt', 'win_l': 'windows', 'win_r': 'windows',
    'caps_lock': 'caps lock', 'num_lock': 'num lock', 'scroll_lock': 'scroll lock',
    'comma': ',', 'period': '.', 'minus': '-', 'equal': '=', 'semicolon': ';',
    'apostrophe': "'", 'slash': '/', 'backslash': '\\', 'bracketleft': '[',
    'bracketright': ']', 'grave': '`', 'quoteleft': '`', 'quoteright': "'",
}


def tk_event_to_key(event):
    # Converts a Tk key event into the key name used by the 'keyboard' library
    keysym = event.keysym.lower()
    if keysym in _KEYSYM_TO_KEY:
        return _KEYSYM_TO_KEY[keysym]
    if keysym.startswith('kp_'):
        return keysym[3:]
    return keysym


def enable_arrow_navigation(listbox):
    """Lets Up/Down move the selection of LISTBOX and notify its <<ListboxSelect>> handlers."""

    def step(delta):
        size = listbox.size()
        if size == 0:
            return 'break'
        selects = listbox.curselection()
        index = selects[0] + delta if selects else 0
        index = max(0, min(size - 1, index))
        listbox.selection_clear(0, 'end')
        listbox.selection_set(index)
        listbox.activate(index)
        listbox.see(index)
        listbox.event_generate('<<ListboxSelect>>')
        return 'break'

    listbox.bind('<Up>', lambda e: step(-1))
    listbox.bind('<Down>', lambda e: step(1))


class Tooltip:
    """Shows TEXT in a small popup while the mouse rests on WIDGET."""

    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._job = None
        self._popup = None
        widget.bind('<Enter>', self._schedule, add='+')
        widget.bind('<Leave>', self._hide, add='+')
        widget.bind('<ButtonPress>', self._hide, add='+')

    def _schedule(self, _):
        self._hide()
        self._job = self.widget.after(self.delay, self._show)

    def _show(self):
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._popup = tk.Toplevel(self.widget)
        self._popup.wm_overrideredirect(True)
        self._popup.wm_geometry(f'+{x}+{y}')
        tk.Label(self._popup, text=self.text, bg='#333333', fg='#ffffff',
                 padx=6, pady=3, font=('Segoe UI', 9)).pack()

    def _hide(self, _=None):
        if self._job is not None:
            self.widget.after_cancel(self._job)
            self._job = None
        if self._popup is not None:
            self._popup.destroy()
            self._popup = None


class Frame(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.parent = parent


class LabelFrame(ttk.LabelFrame):
    def __init__(self, parent, name, **kwargs):
        kwargs['text'] = name
        kwargs['labelanchor'] = tk.N
        super().__init__(parent, **kwargs)
        self.parent = parent


class Tab(Frame):
    def __init__(self, parent, name, **kwargs):
        super().__init__(parent, **kwargs)
        parent.add(self, text=name)


class MenuBarItem(tk.Menu):
    def __init__(self, parent, label, **kwargs):
        super().__init__(parent, **kwargs)
        parent.add_cascade(label=label, menu=self)


class KeyBindings(LabelFrame):
    def __init__(self, parent, label, target, **kwargs):
        super().__init__(parent, label, **kwargs)
        if target is not None:
            assert isinstance(target, Configurable)
        self.target = target
        self.long = False

        self.displays = {}          # Holds each action's display variable
        self.forward = {}           # Maps actions to keys
        self.backward = {}          # Maps keys to actions

        self.contents = None
        self.container = None
        self.canvas = None
        self.scrollbar = None
        self.reset = None
        self.save = None
        self.create_edit_ui()

    def create_edit_ui(self):
        self.displays = {}
        self.forward = {}
        self.backward = {}

        if self.target is None:
            self.contents = Frame(self)
            self.create_disabled_entry()
            self.contents.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
            return

        if len(self.target.config) > 27:
            self.long = True
            self.container = Frame(self, width=354, height=650)
            self.container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=(5, 0))
            self.container.pack_propagate(False)
            self.canvas = tk.Canvas(self.container, bd=0, highlightthickness=0)
            self.scrollbar = tk.Scrollbar(self.container, command=self.canvas.yview)
            self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.contents = Frame(self.canvas)
            self.contents.bind(
                '<Configure>',
                lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            )
            self.canvas.create_window((0, 0), window=self.contents, anchor=tk.NW)
            self.canvas.configure(yscrollcommand=self.scrollbar.set)
        else:
            self.contents = Frame(self)
            self.contents.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        for action, key in self.target.config.items():
            self.forward[action] = key
            self.backward[key] = action
            self.create_entry(action, key)
        self.focus()

        self.reset = tk.Button(self, text='Reset', command=self.refresh_edit_ui, takefocus=False)
        self.reset.pack(side=tk.LEFT, padx=5, pady=5)
        self.save = tk.Button(self, text='Save', command=self.save_keybindings, takefocus=False)
        self.save.pack(side=tk.RIGHT, padx=5, pady=5)

    def refresh_edit_ui(self):
        self.destroy_contents()
        self.create_edit_ui()

    def destroy_contents(self):
        self.contents.destroy()
        self.reset.destroy()
        self.save.destroy()
        if self.long:
            self.container.destroy()
            self.canvas.destroy()
            self.scrollbar.destroy()

    @utils.run_if_disabled('\n[!] Cannot save key bindings while Auto Maple is enabled')
    def save_keybindings(self):
        unbound = [action for action, key in self.forward.items() if key == '']
        if unbound:
            # Saving now would keep the old key on these actions and duplicate a binding
            utils.report_error('Nothing was saved. Assign a key to: ' + ', '.join(unbound))
            return

        for action, key in self.forward.items():
            self.target.config[action] = key
        self.target.save_config()
        utils.report_info(f"Saved key bindings to '{self.target.TARGET}'.")
        self.refresh_edit_ui()

    def create_entry(self, action, key):
        """
        Creates an input row for a single key bind. ACTION is assigned to KEY.
        """

        display_var = tk.StringVar(value=key)
        self.displays[action] = display_var

        row = Frame(self.contents, highlightthickness=0)
        row.pack(expand=True, fill='x')

        label = tk.Entry(row)
        label.grid(row=0, column=0, sticky=tk.EW)
        label.insert(0, action)
        label.config(state=tk.DISABLED)

        def on_key_press(e):
            k = tk_event_to_key(e)
            if k == self.forward[action]:
                return 'break'
            prev_key = self.forward[action]
            self.backward.pop(prev_key, None)
            if k in self.backward:
                prev_action = self.backward[k]
                self.forward[prev_action] = ''
                self.displays[prev_action].set('')
                utils.report_error(f"'{k}' was taken from '{prev_action}', assign it a new key before saving.")
            display_var.set(k)
            self.forward[action] = k
            self.backward[k] = action
            return 'break'

        def validate(d):
            """Blocks user insertion, but allows StringVar set()."""

            if d == '-1':
                return True
            return False

        reg = (self.register(validate), '%d')
        entry = tk.Entry(row, textvariable=display_var,
                         validate='key', validatecommand=reg,
                         takefocus=False)
        entry.bind('<KeyPress>', on_key_press)
        entry.grid(row=0, column=1, sticky=tk.EW)

    def create_disabled_entry(self):
        row = Frame(self.contents, highlightthickness=0)
        row.pack(expand=True, fill='x')

        label = tk.Entry(row)
        label.grid(row=0, column=0, sticky=tk.EW)
        label.config(state=tk.DISABLED)

        entry = tk.Entry(row)
        entry.grid(row=0, column=1, sticky=tk.EW)
        entry.config(state=tk.DISABLED)
