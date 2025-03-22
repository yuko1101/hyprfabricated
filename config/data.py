import os
import json
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib  # noqa: E402
from fabric.utils.helpers import get_relative_path  # noqa: E402


gi.require_version("Gtk", "3.0")

APP_NAME = "hyprfabricated"
APP_NAME_CAP = "hyprfabricated"

CACHE_DIR = str(GLib.get_user_cache_dir()) + f"/{APP_NAME}"

USERNAME = os.getlogin()
HOSTNAME = os.uname().nodename
HOME_DIR = os.path.expanduser("~")

CONFIG_DIR = os.path.expanduser(f"~/.config/{APP_NAME}")

screen = Gdk.Screen.get_default()
CURRENT_WIDTH = screen.get_width()
CURRENT_HEIGHT = screen.get_height()

# Rename to match what's being imported in config.py
WALLPAPERS_DIR_DEFAULT = get_relative_path("../assets/wallpapers_example")
CONFIG_FILE = get_relative_path('../config.json')
WAL_CONFIG = get_relative_path('../config/config.json')

if os.path.exists(CONFIG_FILE) and os.path.exists(WAL_CONFIG):
    with open(WAL_CONFIG, "r") as f:
        configwal = json.load(f)
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
    WALLPAPERS_DIR = configwal.get('wallpapers_dir', WALLPAPERS_DIR_DEFAULT)
    VERTICAL = config.get('vertical', False)  # Use saved value or False as default
else:
    WALLPAPERS_DIR = WALLPAPERS_DIR_DEFAULT
    VERTICAL = False  # Default value when no config exists

DOCK_ICON_SIZE = 28
