from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.entry import Entry
from fabric.widgets.image import Image
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.utils import idle_add, remove_handler, exec_shell_command_async
from fabric.utils.helpers import get_relative_path
from gi.repository import GLib, Gdk, GdkPixbuf
import subprocess
import base64
import io
import os
import re
import sys
import tempfile

import modules.icons as icons

class ClipHistory(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="clip-history",
            visible=False,
            all_visible=False,
            **kwargs,
        )

        # Create a temporary directory for image icons
        self.tmp_dir = tempfile.mkdtemp(prefix="cliphist-")
        
        self.notch = kwargs["notch"]
        self.selected_index = -1  # Track the selected item index
        self._arranger_handler = 0
        self.clipboard_items = []

        self.viewport = Box(name="viewport", spacing=4, orientation="v")
        self.search_entry = Entry(
            name="search-entry",
            placeholder="Search Clipboard History...",
            h_expand=True,
            notify_text=self.filter_items,
            on_activate=lambda entry, *_: self.use_selected_item(),
            on_key_press_event=self.on_search_entry_key_press,
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
                    name="clear-button",
                    child=Label(name="clear-label", markup=icons.trash),
                    on_clicked=lambda *_: self.clear_history(),
                ),
                self.search_entry,
                Button(
                    name="close-button",
                    child=Label(name="close-label", markup=icons.cancel),
                    tooltip_text="Exit",
                    on_clicked=lambda *_: self.close()
                ),
            ],
        )

        self.history_box = Box(
            name="launcher-box",  # Reuse launcher styling
            spacing=10,
            h_expand=True,
            orientation="v",
            children=[
                self.header_box,
                self.scrolled_window,
            ],
        )

        self.add(self.history_box)
        self.show_all()

    def close(self):
        """Close the clipboard history panel"""
        self.viewport.children = []
        self.selected_index = -1  # Reset selection
        self.notch.close_notch()

    def open(self):
        """Open the clipboard history panel and load items"""
        GLib.timeout_add(300, self.load_clipboard_items)
        self.search_entry.set_text("")  # Clear search
        self.search_entry.grab_focus()

    def load_clipboard_items(self):
        """Load clipboard history items using cliphist"""
        try:
            # Get all clipboard items
            result = subprocess.run(
                ["cliphist", "list"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            # Parse the output
            lines = result.stdout.strip().split('\n')
            self.clipboard_items = []
            
            for line in lines:
                if not line or "<meta http-equiv" in line:
                    continue  # Skip empty lines and browser meta content
                
                # Store the raw line which contains the cliphist ID
                self.clipboard_items.append(line)
            
            # Display items
            self.display_clipboard_items()
        except subprocess.CalledProcessError as e:
            print(f"Error loading clipboard history: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)

    def display_clipboard_items(self, filter_text=""):
        """Display clipboard items in the viewport"""
        remove_handler(self._arranger_handler) if self._arranger_handler else None
        self.viewport.children = []
        self.selected_index = -1  # Reset selection
        
        # Filter items if search text is provided
        filtered_items = []
        for item in self.clipboard_items:
            # Extract just the content part (after the first tab)
            content = item.split('\t', 1)[1] if '\t' in item else item
            if filter_text.lower() in content.lower():
                filtered_items.append(item)
        
        # Display items
        for item in filtered_items:
            self.viewport.add(self.create_clipboard_item(item))
        
        # Auto-select first item if we have filter text
        if filter_text and self.viewport.get_children():
            self.update_selection(0)

    def create_clipboard_item(self, item):
        """Create a button for a clipboard item"""
        # Extract ID and content
        parts = item.split('\t', 1)
        item_id = parts[0] if len(parts) > 1 else "0"
        content = parts[1] if len(parts) > 1 else item
        
        # Truncate content for display
        display_text = content.strip()
        if len(display_text) > 100:
            display_text = display_text[:97] + "..."
        
        # Check if this is an image by examining the content
        is_image = self.is_image_data(content)
        
        button = None
        
        if is_image:
            # For images, create item with image preview
            try:
                # Get image preview and save to temp file for icon
                pixbuf = self.get_image_preview(item_id, save_to_file=True)
                image_widget = Image(name="clip-icon", pixbuf=pixbuf, h_align="start")
                
                button = Button(
                    name="slot-button",
                    child=Box(
                        name="slot-box",
                        orientation="h",
                        spacing=10,
                        children=[
                            image_widget,
                            Label(
                                name="clip-label",
                                label="[Image]",
                                ellipsization="end",
                                v_align="center",
                                h_align="start",
                                h_expand=True,
                            ),
                        ],
                    ),
                    tooltip_text="Image in clipboard",
                    on_clicked=lambda *_, id=item_id: self.paste_item(id),
                )
            except Exception as e:
                # Fallback if image preview fails
                print(f"Error creating image preview: {e}", file=sys.stderr)
                button = self.create_text_item_button(item_id, "[Image data]")
        else:
            # For text, create regular item
            button = self.create_text_item_button(item_id, display_text)
        
        # Add key press event handler for Enter key
        button.connect("key-press-event", lambda widget, event, id=item_id: self.on_item_key_press(widget, event, id))
        
        # Make sure button can receive focus and key events
        button.set_can_focus(True)
        button.add_events(Gdk.EventMask.KEY_PRESS_MASK)
            
        return button

    def create_text_item_button(self, item_id, display_text):
        """Create a button for a text clipboard item"""
        button = Button(
            name="slot-button",
            child=Box(
                name="slot-box",
                orientation="h",
                spacing=10,
                children=[
                    # No icon for text items
                    Label(
                        name="clip-label",
                        label=display_text,
                        ellipsization="end",
                        v_align="center",
                        h_align="start",
                        h_expand=True,
                    ),
                ],
            ),
            tooltip_text=display_text,
            on_clicked=lambda *_: self.paste_item(item_id),
        )
        return button

    def is_image_data(self, content):
        """Determine if clipboard content is likely an image"""
        # Various heuristics to detect image data:
        # - Base64 image data often starts with specific patterns
        # - Binary data has unusual characters
        # - Image content often has specific keywords
        
        # Check for common image data patterns
        return (
            content.startswith("data:image/") or
            content.startswith("\x89PNG") or
            content.startswith("GIF8") or
            content.startswith("\xff\xd8\xff") or  # JPEG
            re.match(r'^\s*<img\s+', content) is not None or  # HTML image tag
            "binary" in content.lower() and any(ext in content.lower() for ext in ["jpg", "jpeg", "png", "bmp", "gif"])
        )

    def get_image_preview(self, item_id, save_to_file=False):
        """Get a preview image for clipboard item"""
        try:
            # Use cliphist to get the raw image data
            result = subprocess.run(
                ["cliphist", "decode", item_id],
                capture_output=True,
                check=True
            )
            
            # Create pixbuf from the raw data
            loader = GdkPixbuf.PixbufLoader()
            loader.write(result.stdout)
            loader.close()
            pixbuf = loader.get_pixbuf()
            
            # Resize for a reasonable thumbnail
            width, height = pixbuf.get_width(), pixbuf.get_height()
            max_size = 24  # Same as app icons
            
            if width > height:
                new_width = max_size
                new_height = int(height * (max_size / width))
            else:
                new_height = max_size
                new_width = int(width * (max_size / height))
                
            scaled_pixbuf = pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.BILINEAR)
            
            # Save to a temporary file if requested
            if save_to_file:
                # Determine file extension based on image type
                if pixbuf.get_property("has-alpha"):
                    ext = "png"
                else:
                    ext = "jpg"
                
                # Create the filename
                filepath = os.path.join(self.tmp_dir, f"{item_id}.{ext}")
                
                # Save the full image for better quality
                pixbuf.savev(filepath, ext, [], [])
            
            return scaled_pixbuf
            
        except Exception as e:
            print(f"Error getting image preview: {e}", file=sys.stderr)
            # Return a placeholder image
            return GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 24, 24)

    def paste_item(self, item_id):
        """Copy the selected item to the clipboard and close"""
        try:
            # More reliable way to decode and copy
            decode_proc = subprocess.Popen(
                ["cliphist", "decode", item_id],
                stdout=subprocess.PIPE
            )
            copy_proc = subprocess.Popen(
                ["wl-copy"],
                stdin=decode_proc.stdout
            )
            decode_proc.stdout.close()  # Allow decode_proc to receive SIGPIPE
            copy_proc.communicate()
            
            self.close()
        except subprocess.CalledProcessError as e:
            print(f"Error pasting clipboard item: {e}", file=sys.stderr)

    def delete_item(self, item_id):
        """Delete the selected clipboard item"""
        try:
            subprocess.run(
                ["cliphist", "delete", item_id],
                check=True
            )
            self.load_clipboard_items()  # Refresh the list
        except subprocess.CalledProcessError as e:
            print(f"Error deleting clipboard item: {e}", file=sys.stderr)

    def clear_history(self):
        """Clear all clipboard history"""
        try:
            subprocess.run(["cliphist", "wipe"], check=True)
            self.load_clipboard_items()  # Refresh to show empty list
        except subprocess.CalledProcessError as e:
            print(f"Error clearing clipboard history: {e}", file=sys.stderr)

    def filter_items(self, entry, *_):
        """Filter clipboard items based on search text"""
        self.display_clipboard_items(entry.get_text())

    def on_search_entry_key_press(self, widget, event):
        """Handle key presses in the search entry"""
        if event.keyval == Gdk.KEY_Down:
            self.move_selection(1)
            return True
        elif event.keyval == Gdk.KEY_Up:
            self.move_selection(-1)
            return True
        elif event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self.use_selected_item()
            return True
        elif event.keyval == Gdk.KEY_Delete:
            self.delete_selected_item()
            return True
        elif event.keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def update_selection(self, new_index):
        """Update the selected item in the viewport"""
        children = self.viewport.get_children()
        
        # Unselect current
        if self.selected_index != -1 and self.selected_index < len(children):
            current_button = children[self.selected_index]
            current_button.get_style_context().remove_class("selected")
            
        # Select new
        if new_index != -1 and new_index < len(children):
            new_button = children[new_index]
            new_button.get_style_context().add_class("selected")
            self.selected_index = new_index
            self.scroll_to_selected(new_button)
        else:
            self.selected_index = -1

    def move_selection(self, delta):
        """Move the selection up or down"""
        children = self.viewport.get_children()
        if not children:
            return
            
        # Allow starting selection from nothing
        if self.selected_index == -1 and delta == 1:
            new_index = 0
        else:
            new_index = self.selected_index + delta
            
        new_index = max(0, min(new_index, len(children) - 1))
        self.update_selection(new_index)

    def scroll_to_selected(self, button):
        """Scroll to ensure the selected item is visible"""
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
            return False
        GLib.idle_add(scroll)

    def use_selected_item(self):
        """Use (paste) the selected clipboard item"""
        children = self.viewport.get_children()
        if not children or self.selected_index == -1 or self.selected_index >= len(self.clipboard_items):
            return
            
        # Get the item ID from the first part before the tab
        item_line = self.clipboard_items[self.selected_index]
        item_id = item_line.split('\t', 1)[0]
        self.paste_item(item_id)

    def delete_selected_item(self):
        """Delete the selected clipboard item"""
        children = self.viewport.get_children()
        if not children or self.selected_index == -1:
            return
            
        # Get the item ID from the first part before the tab
        item_line = self.clipboard_items[self.selected_index]
        item_id = item_line.split('\t', 1)[0]
        self.delete_item(item_id)

    def on_item_key_press(self, widget, event, item_id):
        """Handle key press events on clipboard items"""
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            # Copy item to clipboard and close
            self.paste_item(item_id)
            return True
        return False

    def __del__(self):
        """Clean up temporary files on destruction"""
        try:
            if hasattr(self, 'tmp_dir') and os.path.exists(self.tmp_dir):
                import shutil
                shutil.rmtree(self.tmp_dir)
        except Exception as e:
            print(f"Error cleaning up temporary files: {e}", file=sys.stderr)
