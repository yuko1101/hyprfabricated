import setproctitle
import os
import json
from fabric import Application
from fabric.utils import get_relative_path
from config.config import open_config, ensure_fonts
from datetime import datetime
import gi
import warnings


gi.require_version("Gtk", "3.0")
from gi.repository import Gdk

screen = Gdk.Screen.get_default()
CURRENT_WIDTH = screen.get_width()
CURRENT_HEIGHT = screen.get_height()

warnings.filterwarnings("ignore", category=DeprecationWarning)
config_path = os.path.expanduser("~/.config/hyprfabricated/config/config.json")

fonts_updated_file = os.path.expanduser("~/.cache/hyprfabricated/fonts_updated")
cache_dir = os.path.expanduser("~/.cache/hyprfabricated/")

hyprconf = os.path.expanduser("~/.config/hyprfabricated/config.json")
def load_config():
    with open(hyprconf, 'r') as f:
        return json.load(f)

if __name__ == "__main__":
    setproctitle.setproctitle("hyprfabricated")
    current_date = datetime.now()
    target_date = datetime(2025, 2, 25)

    if current_date > target_date and not os.path.exists(fonts_updated_file):
        tabler_icons_path = os.path.expanduser("~/.fonts/tabler-icons")
        if os.path.exists(tabler_icons_path):
            import shutil

            try:
                shutil.rmtree(tabler_icons_path)
                print(f"Removed directory: {tabler_icons_path}")
            except Exception as e:
                print(f"Error removing {tabler_icons_path}: {e}")
        ensure_fonts()
        os.makedirs(cache_dir, exist_ok=True)
        with open(fonts_updated_file, "w") as f:
            f.write("Fonts updated after February 25, 2025")

    if not os.path.isfile(hyprconf):
        open_config()

    config = load_config()

    lin = []
    if config["Basic"]["corners"]:
        from modules.corners import Corners
        corners = Corners()
        lin.append(corners)
    if config["Basic"]["bar"]:
        from modules.bar import Bar
        bar = Bar()
        lin.append(bar)
    if config["Basic"]["notch"]:
        from modules.notch import Notch
        notch = Notch()
        bar.notch = notch
        notch.bar = bar
        lin.append(notch)
    if config["Basic"]["widgets"]:
        if config["widgetstyle"] == "full":
            from modules.deskwidgets import Deskwidgetsfull
            widgets = Deskwidgetsfull()
            lin.append(widgets)
            pass
        elif config["widgetstyle"] == "basic":
            from modules.deskwidgets import Deskwidgetsbasic
            widgets = Deskwidgetsbasic()
            lin.append(widgets)
            pass


    app = Application("hyprfabricated", *lin)

    def set_css():
        app.set_stylesheet_from_file(
            get_relative_path("main.css"),
            exposed_functions={
                "overview_width": lambda: f"min-width: {CURRENT_WIDTH * 0.1 * 5 + 92}px;",
                "overview_height": lambda: f"min-height: {CURRENT_HEIGHT * 0.1 * 2 + 32}px;",
            },
        )

    app.set_css = set_css

    app.set_css()
    app.run()

