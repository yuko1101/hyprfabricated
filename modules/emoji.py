import operator
from collections.abc import Iterator
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.entry import Entry
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.utils import idle_add, remove_handler
from gi.repository import GLib, Gdk
import modules.icons as icons
import os
import subprocess
import ijson

class EmojiPicker(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="emoji",
            visible=False,
            all_visible=False,
            **kwargs,
        )

        self.notch = kwargs["notch"]
        self.selected_index = -1  # Track the selected item index

        self._arranger_handler: int = 0
        self._all_emojis = self._load_emoji_data()

        self.viewport = Box(name="viewport", spacing=4, orientation="v")
        self.search_entry = Entry(
            name="search-entry",
            placeholder="Search Emojis...",
            h_expand=True,
            notify_text=lambda entry, *_: self.arrange_viewport(entry.get_text()),
            on_activate=lambda entry, *_: self.on_search_entry_activate(entry.get_text()),
            on_key_press_event=self.on_search_entry_key_press,  # Handle key presses
        )
        self.search_entry.props.xalign = 0.5
        self.scrolled_window = ScrolledWindow(
            name="scrolled-window",
            spacing=10,
            min_content_size=(450, 105), # Adjusted size, can be tweaked
            max_content_size=(450, 105), # Adjusted size, can be tweaked
            child=self.viewport,
        )

        self.header_box = Box(
            name="header_box",
            spacing=10,
            orientation="h",
            children=[
                self.search_entry,
                Button(
                    name="close-button",
                    child=Label(name="close-label", markup=icons.cancel),
                    tooltip_text="Exit",
                    on_clicked=lambda *_: self.close_picker()
                ),
            ],
        )

        self.picker_box = Box(
            name="picker-box",
            spacing=10,
            h_expand=True,
            orientation="v",
            children=[
                self.header_box,
                self.scrolled_window,
            ],
        )

        self.resize_viewport()

        self.add(self.picker_box)
        self.show_all()

    def _load_emoji_data(self):
        emoji_data = {}
        emoji_file_path = os.path.expanduser("~/.config/Ax-Shell/assets/emoji.json")
        if not os.path.exists(emoji_file_path):
            print(f"Emoji JSON file not found at: {emoji_file_path}")
            return {}

        with open(emoji_file_path, 'r') as f:
            for emoji_char, emoji_info in ijson.kvitems(f, ''):
                emoji_data[emoji_char] = emoji_info
        return emoji_data

    def close_picker(self):
        self.viewport.children = []
        self.selected_index = -1  # Reset selection
        self.notch.close_notch()

    def open_picker(self):
        self.search_entry.set_text("") # Clear search when opening
        # self.show()
        self.arrange_viewport()
        self.search_entry.grab_focus() # Focus on entry when opening

    def arrange_viewport(self, query: str = ""):
        remove_handler(self._arranger_handler) if self._arranger_handler else None
        self.viewport.children = []
        self.selected_index = -1  # Clear selection when viewport changes

        filtered_emojis_iter = iter(
            [
                (emoji_char, emoji_info)
                for emoji_char, emoji_info in self._all_emojis.items()
                if query.casefold() in (emoji_info.get("name", "") + " " + emoji_info.get("group", "")).casefold()
            ]
        )
        should_resize = operator.length_hint(filtered_emojis_iter) == len(self._all_emojis)

        self._arranger_handler = idle_add(
            lambda emojis_iter: self.add_next_emoji(emojis_iter) or self.handle_arrange_complete(should_resize, query),
            filtered_emojis_iter,
            pin=True,
        )

    def handle_arrange_complete(self, should_resize, query):
        if should_resize:
            self.resize_viewport()
        # Only auto-select first item if query exists
        if query.strip() != "" and self.viewport.get_children():
            self.update_selection(0)
        return False

    def add_next_emoji(self, emojis_iter: Iterator[tuple[str, dict]]):
        if not (emoji_item := next(emojis_iter, None)):
            return False
        emoji_char, emoji_info = emoji_item
        self.viewport.add(self.bake_emoji_slot(emoji_char, emoji_info))
        return True

    def resize_viewport(self):
        self.scrolled_window.set_min_content_width(
            self.viewport.get_allocation().width  # type: ignore
        )
        return False

    def bake_emoji_slot(self, emoji_char: str, emoji_info: dict, **kwargs) -> Button:
        button = Button(
            name="emoji-slot-button",
            child=Box(
                name="emoji-slot-box",
                orientation="h", # Changed to vertical for emoji and name
                spacing=5,
                children=[
                    Label(
                        name="emoji-char-label",
                        label=emoji_char,
                        use_markup=True,
                        v_align="center",
                        h_align="center",
                        css_name="emoji-char-label" # For CSS styling of emoji size
                    ),
                    Label(
                        name="emoji-name-label",
                        label=emoji_info.get("name", "Unknown"),
                        ellipsization="end",
                        v_align="center",
                        h_align="center",
                        css_name="emoji-name-label" # For CSS styling of emoji name
                    ),
                ],
            ),
            tooltip_text=emoji_info.get("name", "Unknown"),
            on_clicked=lambda *_: (self.copy_emoji_to_clipboard(emoji_char), self.close_picker()), # Copy emoji and close
            **kwargs,
        )
        return button

    def update_selection(self, new_index: int):
        # Unselect current
        if self.selected_index != -1 and self.selected_index < len(self.viewport.get_children()):
            current_button = self.viewport.get_children()[self.selected_index]
            current_button.get_style_context().remove_class("selected")
        # Select new
        if new_index != -1 and new_index < len(self.viewport.get_children()):
            new_button = self.viewport.get_children()[new_index]
            new_button.get_style_context().add_class("selected")
            self.selected_index = new_index
            self.scroll_to_selected(new_button)
        else:
            self.selected_index = -1

    def scroll_to_selected(self, button):
        def scroll():
            adj = self.scrolled_window.get_vadjustment()
            alloc = button.get_allocation()
            if alloc.height == 0:
                return False  # Retry if allocation isn't ready

            y = alloc.y
            height = alloc.height
            page_size = adj.get_page_size()
            current_value = adj.get_value()

            # Calculate visible boundaries
            visible_top = current_value
            visible_bottom = current_value + page_size

            if y < visible_top:
                # Item above viewport - align to top
                adj.set_value(y)
            elif y + height > visible_bottom:
                # Item below viewport - align to bottom
                new_value = y + height - page_size
                adj.set_value(new_value)
            # No action if already fully visible
            return False
        GLib.idle_add(scroll)

    def on_search_entry_activate(self, text):
        children = self.viewport.get_children()
        if children:
            if self.selected_index != -1:
                children[self.selected_index].clicked()
            elif children and text.strip() != "": # if there are results and enter pressed with search
                children[0].clicked() # select first one if available

    def on_search_entry_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Down:
            self.move_selection(1)
            return True
        elif event.keyval == Gdk.KEY_Up:
            self.move_selection(-1)
            return True
        elif event.keyval == Gdk.KEY_Escape:
            self.close_picker()
            return True
        return False

    def move_selection(self, delta: int):
        children = self.viewport.get_children()
        if not children:
            return
        # Allow starting selection from nothing when empty
        if self.selected_index == -1 and delta == 1:
            new_index = 0
        else:
            new_index = self.selected_index + delta
        new_index = max(0, min(new_index, len(children) - 1))
        self.update_selection(new_index)

    def copy_emoji_to_clipboard(self, emoji_char: str):
        try:
            subprocess.run(["wl-copy"], input=emoji_char.encode('utf-8'), check=True)
        except subprocess.CalledProcessError as e:
            print(f"Clipboard copy failed: {e}")
