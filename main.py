"""The central program that ties all the modules together."""

import sys
import time
from src.modules.bot import Bot
from src.modules.capture import Capture
from src.modules.notifier import Notifier
from src.modules.listener import Listener
from src.modules.gui import GUI


def wait_until_ready(module, name):
    """Waits for MODULE to be ready, exiting with a clear message if its thread dies first."""

    while not module.ready:
        if not module.thread.is_alive():
            print(f'\n[!] {name} stopped during start-up, see the error above. Exiting.')
            sys.exit(1)
        time.sleep(0.01)


bot = Bot()
capture = Capture()
notifier = Notifier()
listener = Listener()

bot.start()
wait_until_ready(bot, 'The main bot loop')

capture.start()      # Not awaited: the GUI opens even before the game window is found

notifier.start()
wait_until_ready(notifier, 'The notifier')

listener.start()
wait_until_ready(listener, 'The keyboard listener')

print('\n[~] Successfully initialized Auto Maple')

gui = GUI()
gui.start()
