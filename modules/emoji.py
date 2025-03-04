import operator
from collections.abc import Iterator
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.entry import Entry
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.image import Image
from fabric.utils import DesktopApp, get_desktop_applications, idle_add, remove_handler, exec_shell_command_async
from gi.repository import GLib, Gdk
import modules.icons as icons
import modules.data as data
import json
import os
import re
import math
import subprocess
import ijson
from fabric.utils import remove_handler, get_relative_path
from typing import Generator, List

class Emojipicker(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="app-launcher",
            visible=False,
            all_visible=False,
            **kwargs,
        )

        self.notch = kwargs["notch"]
        self.selected_index = -1  # Track the selected item index

        self._arranger_handler: int = 0
        self._all_apps = get_desktop_applications()

        # Calculator history initialization
        self.calc_history_path = os.path.expanduser("~/.cache/hyprfabricated/calc.json")
        if os.path.exists(self.calc_history_path):
            with open(self.calc_history_path, "r") as f:
                self.calc_history = json.load(f)
        else:
            self.calc_history = []
        self.emoji_file_path = get_relative_path("../assets/resource/emoji.json")

        self.viewport = Box(name="viewport", spacing=4, orientation="v")
        self.search_entry = Entry(
            name="search-entry",
            placeholder="Search Emoji...",
            h_expand=True,
            notify_text=lambda entry, *_: (
                self.update_calculator_viewport() if entry.get_text().startswith("=")
                else self.arrange_viewport(entry.get_text())
            ),
            # on_activate=lambda entry, *_: self.on_search_entry_activate(entry.get_text()),
            # on_key_press_event=self.on_search_entry_key_press,  # Handle key presses
        )
        self.search_entry.props.xalign = 0.5
        self.scrolled_window = ScrolledWindow(
            name="scrolled-window",
            spacing=10,
            min_content_size=(450, 105),
            max_content_size=(450, 105),
            child=self.viewport,
        )

        self.header_box = Box(
            name="header_box",
            spacing=10,
            orientation="h",
            children=[
                Button(
                    name="config-button",
                    child=Label(name="config-label", markup=icons.config),
                    on_clicked=lambda *_: (exec_shell_command_async(f"python {data.HOME_DIR}/.config/hyprfabricated/config/config.py"), self.close_launcher()),
                ),
                self.search_entry,
                Button(
                    name="close-button",
                    child=Label(name="close-label", markup=icons.cancel),
                    tooltip_text="Exit",
                    on_clicked=lambda *_: self.close_launcher()
                ),
            ],
        )

        self.launcher_box = Box(
            name="launcher-box",
            spacing=10,
            h_expand=True,
            orientation="v",
            children=[
                self.header_box,
                self.scrolled_window,
            ],
        )

        # self.resize_viewport()

        self.add(self.launcher_box)
        self.show_all()

    def close_launcher(self):
        self.viewport.children = []
        self.selected_index = -1  # Reset selection
        self.notch.close_notch()

    def open_launcher(self):
        self._all_apps = get_desktop_applications()
        self.arrange_viewport()


    def copy_emoji(self, emoji: tuple):
        subprocess.run(["wl-copy"], input=emoji[0].encode(), check=True)
        self.launcher.close_launcher()

    def load_emojis(self) -> Generator[tuple, None, None]:
        try:
            with open(self.emoji_file_path, "r") as file:
                for emoji_str, item in ijson.kvitems(file, ""):
                    yield emoji_str, item.get("name", ""), item.get("slug", ""), item.get("group", "")
        except (ijson.JSONError, KeyError, OSError) as e:
            print(f"Error loading emojis: {e}")
            return

    def query_emojis(self, query: str) -> List[tuple]:
        query = query.lower().strip()
        result = []
        try:
            for emoji_str, name, slug, group in self.load_emojis():
                search_fields = " ".join([name, slug, group]).lower()
                if query in search_fields:
                    result.append((emoji_str, name, slug, group))
                if len(result) >= 48:
                    break
        except Exception as e:
            print(f"Error querying emojis: {e}")
        return result



