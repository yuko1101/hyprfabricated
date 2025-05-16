import os
import shutil
import sys
from pathlib import Path

from fabric import Application

# Use relative imports now that 'config' is a package
from .data import APP_NAME, APP_NAME_CAP
from .settings_utils import load_bind_vars # bind_vars is managed within settings_utils
from .settings_gui import HyprConfGUI

# The sys.path.insert for data.py is no longer needed here
# as direct relative imports like `from .data import ...` will work.

def open_config():
    """
    Entry point for opening the configuration GUI using Fabric Application.
    """
    # Load initial settings into settings_utils.bind_vars
    load_bind_vars()

    # Determine if checkboxes for Hyprlock/Hypridle should be shown
    # This logic remains similar, checking for existing user configs
    # and copying defaults if they don't exist.
    show_lock_checkbox = True
    dest_lock = os.path.expanduser("~/.config/hypr/hyprlock.conf")
    src_lock = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/hyprlock.conf")
    if not os.path.exists(dest_lock) and os.path.exists(src_lock):
        try:
            os.makedirs(os.path.dirname(dest_lock), exist_ok=True)
            shutil.copy(src_lock, dest_lock)
            # If we just copied the default, no need to ask to replace it again immediately
            # However, the GUI might still offer it if the user wants to re-apply.
            # For simplicity, let's assume if we copy it, the user might want to manage it.
            # The original logic set show_lock_checkbox = False. Let's stick to that.
            show_lock_checkbox = False 
            print(f"Copied default hyprlock config to {dest_lock}")
        except Exception as e:
            print(f"Error copying default hyprlock config: {e}")
            show_lock_checkbox = os.path.exists(src_lock) # Fallback if copy fails

    show_idle_checkbox = True
    dest_idle = os.path.expanduser("~/.config/hypr/hypridle.conf")
    src_idle = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/hypridle.conf")
    if not os.path.exists(dest_idle) and os.path.exists(src_idle):
        try:
            os.makedirs(os.path.dirname(dest_idle), exist_ok=True)
            shutil.copy(src_idle, dest_idle)
            show_idle_checkbox = False # Same logic as for lock
            print(f"Copied default hypridle config to {dest_idle}")
        except Exception as e:
            print(f"Error copying default hypridle config: {e}")
            show_idle_checkbox = os.path.exists(src_idle) # Fallback

    app = Application(f"{APP_NAME}-settings")
    window = HyprConfGUI(
        show_lock_checkbox=show_lock_checkbox,
        show_idle_checkbox=show_idle_checkbox,
        application=app,
        on_destroy=lambda *_: app.quit()
    )
    app.add_window(window)

    window.show_all() # Ensure the window is shown
    app.run()


if __name__ == "__main__":
    # This allows running the config GUI directly for development/testing
    # Ensure that if this is run, the context for relative imports is correct.
    # If run as `python -m config.config`, relative imports work.
    # If run as `python config/config.py` from project root, they also work.
    open_config()
