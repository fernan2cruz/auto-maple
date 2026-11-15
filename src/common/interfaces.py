import os
import pickle
from src.common import safe_pickle


class Configurable:
    TARGET = 'default_configurable'
    DIRECTORY = '.settings'
    DEFAULT_CONFIG = {          # Must be overridden by subclass
        'Default configuration': 'None'
    }

    def __init__(self, target, directory='.settings'):
        assert self.DEFAULT_CONFIG != Configurable.DEFAULT_CONFIG, 'Must override Configurable.DEFAULT_CONFIG'
        self.TARGET = target
        self.DIRECTORY = directory
        self.config = self.DEFAULT_CONFIG.copy()        # Shallow copy, should only contain primitives
        self.load_config()

    def load_config(self):
        path = os.path.join(self.DIRECTORY, self.TARGET)
        if os.path.isfile(path):
            try:
                with open(path, 'rb') as file:
                    loaded = safe_pickle.load(file)
                if not isinstance(loaded, dict):
                    raise pickle.UnpicklingError('expected a dictionary')
            except Exception as e:      # Corrupted or tampered file: keep the defaults
                print(f"\n[!] Could not read settings file '{path}', using defaults: {e}")
                return
            self.config = {key: loaded.get(key, default) for key, default in self.DEFAULT_CONFIG.items()}
        else:
            self.save_config()

    def save_config(self):
        path = os.path.join(self.DIRECTORY, self.TARGET)
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(path, 'wb') as file:
            pickle.dump(self.config, file)
