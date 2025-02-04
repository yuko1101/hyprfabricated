import setproctitle
import os
from fabric import Application
from fabric.utils import get_relative_path
from modules.bar import Bar
from modules.notch import Notch
from modules.corners import Corners
from config.config import open_config

config_path = os.path.expanduser("~/.config/Ax-Shell/config/config.json")

if __name__ == "__main__":
    setproctitle.setproctitle("ax-shell")
    if not os.path.isfile(config_path):
        open_config()
    corners = Corners()
    bar = Bar()
    notch = Notch()
    bar.notch = notch
    app = Application("ax-shell", bar, notch)
    app.set_stylesheet_from_file(get_relative_path("main.css"))

    app.run()
