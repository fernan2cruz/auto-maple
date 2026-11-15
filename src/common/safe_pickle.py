"""
Restricted pickle loading. Settings and layout files are pickles, and a plain pickle.load()
runs arbitrary code from a tampered file. This loader only rebuilds the classes it is told
to allow and refuses everything else.
"""

import pickle


class RestrictedUnpickler(pickle.Unpickler):
    """An Unpickler that only resolves classes listed in ALLOWED."""

    def __init__(self, file, allowed):
        """
        :param file:        A binary file object to read from.
        :param allowed:     A dict mapping (module, name) to the class to use.
        """

        super().__init__(file)
        self.allowed = allowed

    def find_class(self, module, name):
        cls = self.allowed.get((module, name))
        if cls is None:
            raise pickle.UnpicklingError(f"Refusing to load '{module}.{name}' from a pickle file.")
        return cls


def load(file, allowed=None):
    """
    Loads a pickle from the binary FILE object, only allowing the classes in ALLOWED.
    Plain data (dict, list, str, int, float, bool, None, tuple) never needs to be allowed.
    """

    return RestrictedUnpickler(file, allowed or {}).load()
