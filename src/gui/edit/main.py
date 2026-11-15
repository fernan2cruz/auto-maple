"""Allows the user to edit routines while viewing each Point's location on the minimap."""

from src.common import config, utils
import inspect
import tkinter as tk
from tkinter import ttk
from src.routine.components import Point, Command
from src.gui.edit.minimap import Minimap
from src.gui.edit.record import Record
from src.gui.edit.routine import Routine
from src.gui.edit.status import Status
from src.gui.interfaces import Tab, Frame, LabelFrame


class Edit(Tab):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, 'Edit', **kwargs)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(4, weight=1)

        self.record = Record(self)
        self.record.grid(row=2, column=3, sticky=tk.NSEW, padx=10, pady=10)

        self.minimap = Minimap(self)
        self.minimap.grid(row=0, column=3, sticky=tk.NSEW, padx=10, pady=10)

        self.status = Status(self)
        self.status.grid(row=1, column=3, sticky=tk.NSEW, padx=10, pady=10)

        self.routine = Routine(self)
        self.routine.grid(row=0, column=1, rowspan=3, sticky=tk.NSEW, padx=10, pady=10)

        self.editor = Editor(self)
        self.editor.grid(row=0, column=2, rowspan=3, sticky=tk.NSEW, padx=10, pady=10)


# Arguments edited with a drop-down instead of free text
ARGUMENT_CHOICES = {
    'direction': ('left', 'right', 'up', 'down'),
}

# Arguments that are names, never numbers, even if they look like one
TEXT_ARGUMENTS = {'label', 'target'}

SEARCH_PLACEHOLDER = 'Search for a component'


def _is_number(value):
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


class Editor(LabelFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, 'Editor', **kwargs)

        self.columnconfigure(0, minsize=350)

        self.vars = {}
        self.contents = None
        self.create_default_state()

    def reset(self):
        """Resets the Editor UI to its default state."""

        self.contents.destroy()
        self.create_default_state()

    def create_default_state(self):
        self.vars = {}

        self.contents = Frame(self)
        self.contents.grid(row=0, column=0, sticky=tk.EW, padx=5)

        self.create_title('Nothing selected')
        self.create_disabled_entry('Select a component or command to edit it, or press ➕ to add one.')

    def create_title(self, text):
        title = ttk.Label(self.contents, text=text, anchor=tk.CENTER, font=('Segoe UI', 10, 'bold'))
        title.pack(expand=True, fill='x', pady=(5, 4))

    def create_disabled_entry(self, text='This item has no arguments.'):
        hint = ttk.Label(self.contents, text=text, anchor=tk.CENTER, wraplength=320)
        hint.pack(expand=True, fill='x', pady=4)

    def create_entry(self, key, value):
        """
        Creates an input row for a single Component attribute. KEY is the name
        of the attribute while VALUE is its currently assigned value.
        """

        var = tk.StringVar(value=str(value))
        self.vars[key] = var

        row = Frame(self.contents, highlightthickness=0)
        row.pack(expand=True, fill='x', pady=1)

        label = ttk.Label(row, text=key, width=16, anchor=tk.W)
        label.pack(side=tk.LEFT)

        text = str(value).strip().lower()
        if isinstance(value, bool) or text in ('true', 'false'):
            var.set('True' if text == 'true' else 'False')
            check = ttk.Checkbutton(row, variable=var, onvalue='True', offvalue='False')
            check.pack(side=tk.LEFT)
        elif key in ARGUMENT_CHOICES:
            combo = ttk.Combobox(row, textvariable=var, values=ARGUMENT_CHOICES[key])
            combo.pack(side=tk.RIGHT, expand=True, fill='x')
        else:
            entry = tk.Entry(row, textvariable=var)
            entry.pack(side=tk.RIGHT, expand=True, fill='x')
            if key not in TEXT_ARGUMENTS and (isinstance(value, (int, float)) or _is_number(value)):
                normal_bg = entry.cget('bg')

                def check_number(*_):
                    entry.config(bg=normal_bg if _is_number(var.get()) else '#ef9a9a')
                var.trace_add('write', check_number)

    def create_edit_ui(self, arr, i, func):
        """
        Creates a UI to edit existing routine Components.
        :param arr:     List of Components to choose from.
        :param i:       The index to choose.
        :param func:    When called, creates a function that can be bound to the button.
        :return:        None
        """

        self.contents.destroy()
        self.vars = {}
        self.contents = Frame(self)
        self.contents.grid(row=0, column=0, sticky=tk.EW, padx=5)

        self.create_title(f"Editing {arr[i].__class__.__name__}")

        if len(arr[i].kwargs) > 0:
            for key, value in arr[i].kwargs.items():
                self.create_entry(key, value)
            button = tk.Button(self.contents, text='Save', command=func(arr, i, self.vars))
            button.pack(pady=5)
        else:
            self.create_disabled_entry()

    def create_add_prompt(self):
        """Creates a UI that asks the user to select a class to create."""

        self.contents.destroy()
        self.vars = {}
        self.contents = Frame(self)
        self.contents.grid(row=0, column=0, sticky=tk.EW, padx=5)

        self.create_title('Creating new ...')

        options = config.routine.get_all_components()
        var = tk.StringVar(value=tuple(options.keys()))

        def update_search(*_):
            value = '' if placeholder_active[0] else input_var.get().strip().lower()
            if value == '':
                var.set(tuple(options.keys()))
            else:
                new_options = []
                for key in options:
                    if key.lower().startswith(value):
                        new_options.append(key)
                var.set(new_options)

        def on_entry_return(e):
            if placeholder_active[0]:
                return
            value = e.widget.get().strip().lower()
            if value in options:
                self.create_add_ui(options[value], sticky=True)
            else:
                utils.report_error(f"'{value}' is not a valid component.")

        def on_entry_down(_):
            display.focus()
            display.selection_set(0)

        def on_display_submit(e):
            w = e.widget
            selects = w.curselection()
            if len(selects) > 0:
                value = w.get(int(selects[0]))
                if value in options:
                    self.create_add_ui(options[value], sticky=True)

        def on_display_up(e):
            selects = e.widget.curselection()
            if len(selects) > 0 and int(selects[0]) == 0:
                user_input.focus()

        # Search bar
        input_var = tk.StringVar()
        user_input = tk.Entry(self.contents, textvariable=input_var)
        user_input.pack(expand=True, fill='x')
        placeholder_active = [True]
        normal_fg = user_input.cget('fg')
        user_input.insert(0, SEARCH_PLACEHOLDER)
        user_input.config(fg='#9e9e9e')

        def clear_placeholder(e):
            # Cleared on the first typed character so the field can keep focus on open
            if placeholder_active[0] and e.keysym not in ('Return', 'Down', 'Up', 'Tab'):
                placeholder_active[0] = False
                user_input.delete(0, 'end')
                user_input.config(fg=normal_fg)

        user_input.bind('<Key>', clear_placeholder)
        user_input.bind('<Return>', on_entry_return)
        user_input.bind('<Down>', on_entry_down)
        input_var.trace('w', update_search)         # Show filtered results in real time
        user_input.focus()

        # Display search results
        results = Frame(self.contents)
        results.pack(expand=True, fill='both', pady=(1, 0))

        scroll = tk.Scrollbar(results)
        scroll.pack(side=tk.RIGHT, fill='both')

        display = tk.Listbox(results, listvariable=var,
                             activestyle='none',
                             yscrollcommand=scroll.set)
        display.bind('<Double-1>', on_display_submit)
        display.bind('<Return>', on_display_submit)
        display.bind('<Up>', on_display_up)
        display.pack(side=tk.LEFT, expand=True, fill='both')

        scroll.config(command=display.yview)

    def create_add_ui(self, component, sticky=False, kwargs=None):
        """
        Creates a UI that edits the parameters of a new COMPONENT instance, and allows
        the user to add this newly created Component to the current routine.
        :param component:   The class to create an instance of.
        :param sticky:      If True, prevents other UI elements from overwriting this one.
        :param kwargs:      Custom arguments for the new object.
        :return:            None
        """

        # Prevent Components and Commands from overwriting this UI
        if sticky:
            routine = self.parent.routine
            routine.components.unbind_select()
            routine.commands.unbind_select()

        self.contents.destroy()
        self.vars = {}
        self.contents = Frame(self)
        self.contents.grid(row=0, column=0, sticky=tk.EW, padx=5)

        title = tk.Entry(self.contents, justify=tk.CENTER)
        title.pack(expand=True, fill='x', pady=(5, 2))
        title.insert(0, f"Creating new {component.__name__}")
        title.config(state=tk.DISABLED)

        sig = inspect.getfullargspec(component.__init__)
        if sig.defaults is None:
            diff = len(sig.args)
        else:
            diff = len(sig.args) - len(sig.defaults)

        # Populate args
        if kwargs is None:
            kwargs = {}
        for i in range(diff):
            arg = sig.args[i]
            if arg != 'self' and arg not in kwargs:
                kwargs[sig.args[i]] = ''

        # Populate kwargs
        for i in range(diff, len(sig.args)):
            kwargs[sig.args[i]] = sig.defaults[i-diff]

        if len(kwargs) > 0:
            for key, value in kwargs.items():
                self.create_entry(key, value)
        else:
            self.create_disabled_entry()

        controls = Frame(self.contents)
        controls.pack(expand=True, fill='x')

        add_button = tk.Button(controls, text='Add', command=self.add(component))
        if sticky:          # Only create 'cancel' button if stickied
            add_button.pack(side=tk.RIGHT, pady=5)
            cancel_button = tk.Button(controls, text='Cancel', command=self.cancel, takefocus=False)
            cancel_button.pack(side=tk.LEFT, pady=5)
        else:
            add_button.pack(pady=5)

    def cancel(self):
        """Button callback that exits the current Component creation UI."""

        routine = self.parent.routine
        routine.components.bind_select()
        routine.commands.bind_select()
        self.update_display()

    def add(self, component):
        """Returns a Button callback that appends the current Component to the routine."""

        def f():
            new_kwargs = {k: v.get() for k, v in self.vars.items()}
            selects = self.parent.routine.components.listbox.curselection()

            try:
                obj = component(**new_kwargs)
                if isinstance(obj, Command):
                    if len(selects) > 0:
                        index = int(selects[0])
                        if isinstance(config.routine[index], Point):
                            config.routine.append_command(index, obj)
                            self.parent.routine.commands.update_display()
                            self.cancel()
                        else:
                            utils.report_error('Cannot add the command: the selected component is not a Point.')
                    else:
                        utils.report_error('Cannot add the command: select a Point first.')
                else:
                    config.routine.append_component(obj)
                    self.cancel()
            except (ValueError, TypeError) as e:
                utils.report_error(f"Invalid arguments for '{component.__name__}': {e}")
        return f

    def update_display(self):
        """
        Displays an edit UI for the currently selected Command if there is one, otherwise
        displays an edit UI for the current Component. If nothing is selected, displays the
        default UI.
        """

        routine = self.parent.routine
        components = routine.components.listbox.curselection()
        commands = routine.commands.listbox.curselection()
        if len(components) > 0:
            p_index = int(components[0])
            if len(commands) > 0:
                c_index = int(commands[0])
                self.create_edit_ui(config.routine[p_index].commands, c_index,
                                    routine.commands.update_obj)
            else:
                self.create_edit_ui(config.routine, p_index,
                                    routine.components.update_obj)
        else:
            self.contents.destroy()
            self.create_default_state()
