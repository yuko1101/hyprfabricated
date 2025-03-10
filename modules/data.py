import os
import json
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk

USERNAME = os.getlogin()
HOSTNAME = os.uname().nodename
HOME_DIR = os.path.expanduser("~")

screen = Gdk.Screen.get_default()
CURRENT_WIDTH = screen.get_width()
CURRENT_HEIGHT = screen.get_height()

default_wallpapers_dir = os.path.expanduser("~/.config/Ax-Shell/assets/wallpapers_example")
json_config_path = os.path.expanduser('~/.config/Ax-Shell/config/config.json')

if os.path.exists(json_config_path):
    with open(json_config_path, 'r') as f:
        config = json.load(f)
    WALLPAPERS_DIR = config.get('wallpapers_dir', default_wallpapers_dir)
else:
    WALLPAPERS_DIR = default_wallpapers_dir
