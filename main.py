import setproctitle
import os
import json
from fabric import Application
from fabric.utils import get_relative_path
from config.config import open_config
from datetime import datetime
import gi
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)


gi.require_version("Gtk", "3.0")
from gi.repository import Gdk

screen = Gdk.Screen.get_default()
CURRENT_WIDTH = screen.get_width()
CURRENT_HEIGHT = screen.get_height()
fonts_updated_file = os.path.expanduser("~/.cache/hyprfabricated/fonts_updated")
cache_dir = os.path.expanduser("~/.cache/hyprfabricated/")
hyprconf = get_relative_path("config.json")


def load_config():
    with open(hyprconf, "r") as f:
        return json.load(f)


if __name__ == "__main__":
    setproctitle.setproctitle("hyprfabricated")

    if not os.path.isfile(hyprconf):
        open_config()

    config = load_config()

    assets = []
    if config["Basic"]["corners"]:
        from modules.corners import Corners

        corners = Corners()
        assets.append(corners)
    if config["Basic"]["bar"]:
        from modules.bar import Bar

        bar = Bar()
        assets.append(bar)
    if config["Basic"]["notch"]:
        from modules.notch import Notch

        notch = Notch()
        bar.notch = notch
        notch.bar = bar
        assets.append(notch)
    if config["Basic"]["widgets"]:
        if config["widgetstyle"] == "full":
            from modules.deskwidgets import Deskwidgetsfull

            widgets = Deskwidgetsfull()
            assets.append(widgets)
            pass
        elif config["widgetstyle"] == "basic":
            from modules.deskwidgets import Deskwidgetsbasic

            widgets = Deskwidgetsbasic()
            assets.append(widgets)
            pass

    app = Application("hyprfabricated", *assets)

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
