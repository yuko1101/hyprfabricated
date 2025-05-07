import gi

gi.require_version("Gray", "0.1")
from fabric.widgets.box import Box
from gi.repository import Gdk, GdkPixbuf, GLib, Gray, Gtk

import config.data as data
import logging # Added for logging

logger = logging.getLogger(__name__) # Added for logging


class SystemTray(Box):
    def __init__(self, pixel_size: int = 20, **kwargs) -> None:
        orientation = Gtk.Orientation.HORIZONTAL if not data.VERTICAL else Gtk.Orientation.VERTICAL
        super().__init__(
            name="systray",
            orientation=orientation,
            spacing=8,
            **kwargs
        )
        self.enabled = True
        self.set_visible(False)  # Initially hidden
        self.pixel_size = pixel_size
        
        self.buttons_by_id = {}  # Store Gtk.Button by item identifier
        self.items_by_id = {}    # Store Gray.Item by item identifier

        self.watcher = Gray.Watcher()
        self.watcher.connect("item-added", self.on_watcher_item_added)
        # self.watcher.connect("item-removed", self.on_watcher_item_removed) # If Gray.Watcher has this

    def set_visible(self, visible):
        """Override to track external visibility setting"""
        self.enabled = visible
        self._update_visibility() # Call the consolidated update logic

    def _update_visibility(self):
        # Update visibility based on the number of child widgets and enabled state
        if self.enabled and len(self.get_children()) > 0:
            if not self.get_visible():
                super().set_visible(True)
        else:
            if self.get_visible():
                super().set_visible(False)

    def _get_item_pixbuf(self, item: Gray.Item) -> GdkPixbuf.Pixbuf:
        """Fetches or creates a GdkPixbuf.Pixbuf for the given Gray.Item."""
        pixbuf = None
        try:
            pixmap = Gray.get_pixmap_for_pixmaps(item.get_icon_pixmaps(), self.pixel_size)
            if pixmap is not None:
                pixbuf = pixmap.as_pixbuf(self.pixel_size, GdkPixbuf.InterpType.HYPER)
            else:
                icon_name = item.get_icon_name()
                icon_theme_path = item.get_icon_theme_path()

                if icon_theme_path:
                    custom_theme = Gtk.IconTheme.new()
                    custom_theme.prepend_search_path(icon_theme_path)
                    try:
                        pixbuf = custom_theme.load_icon(
                            icon_name,
                            self.pixel_size,
                            Gtk.IconLookupFlags.FORCE_SIZE,
                        )
                    except GLib.Error: # Fallback to default theme if custom path fails for this icon
                        logger.debug(f"Failed to load icon '{icon_name}' from custom theme path '{icon_theme_path}'. Falling back to default theme.")
                        pixbuf = Gtk.IconTheme.get_default().load_icon(
                            icon_name,
                            self.pixel_size,
                            Gtk.IconLookupFlags.FORCE_SIZE,
                        )
                else:
                    pixbuf = Gtk.IconTheme.get_default().load_icon(
                        icon_name,
                        self.pixel_size,
                        Gtk.IconLookupFlags.FORCE_SIZE,
                    )
        except GLib.Error as e:
            # This catches errors from Gtk.IconTheme.get_default().load_icon or other GLib errors
            logger.error(f"GLib.Error loading icon for item (Name: {item.get_icon_name()}): {e}")
        
        if pixbuf is None: # If any step above failed or resulted in None
            item_title = "Unknown"
            try:
                item_title = item.get_title() if hasattr(item, 'get_title') else item.get_icon_name()
            except Exception: #NOSONAR
                pass # Ignore error getting title for fallback log
            logger.warning(f"Failed to load icon for item '{item_title}'. Using 'image-missing' fallback.")
            pixbuf = Gtk.IconTheme.get_default().load_icon(
                "image-missing",
                self.pixel_size,
                Gtk.IconLookupFlags.FORCE_SIZE,
            )
        return pixbuf

    def _refresh_item_ui(self, identifier: str, item: Gray.Item, button: Gtk.Button):
        """Refreshes the icon and tooltip of an existing button."""
        logger.debug(f"Refreshing UI for item ID: {identifier}")
        pixbuf = self._get_item_pixbuf(item)
        image_widget = button.get_image()
        
        if isinstance(image_widget, Gtk.Image):
            image_widget.set_from_pixbuf(pixbuf)
        else: # Should not happen if buttons always have a Gtk.Image
            logger.warning(f"Button for item ID '{identifier}' did not have a Gtk.Image. Creating new one.")
            new_image = Gtk.Image.new_from_pixbuf(pixbuf)
            button.set_image(new_image)
            new_image.show()
        
        # Update tooltip
        tooltip_text = None
        if hasattr(item, 'get_tooltip_text'): # Check if method exists
            tooltip_text = item.get_tooltip_text() 
        elif hasattr(item, 'get_title'): # Fallback to title for tooltip
            tooltip_text = item.get_title()

        if tooltip_text:
            button.set_tooltip_text(tooltip_text)
        else:
            button.set_has_tooltip(False) # Clear tooltip if none

    def on_watcher_item_added(self, _, identifier: str):
        logger.debug(f"Watcher 'item-added' for ID: {identifier}")
        item = self.watcher.get_item_for_identifier(identifier)
        if not item:
            logger.error(f"Could not get Gray.Item for identifier: {identifier}. Aborting add.")
            return

        if identifier in self.buttons_by_id:
            logger.warning(f"Item with identifier '{identifier}' is being re-added. Replacing existing button.")
            old_button = self.buttons_by_id.pop(identifier, None)
            old_item_instance = self.items_by_id.pop(identifier, None)
            
            if old_item_instance:
                # Disconnecting signals from old_item_instance can be complex without handler IDs.
                # We rely on GObject's lifecycle or the 'removed' signal of old_item_instance.
                # For safety, one might want to GObject.signal_handlers_disconnect_by_data(old_item_instance, self)
                # if signals were connected with self as user_data.
                pass # Assuming old item will be properly garbage collected or its 'removed' signal handled.

            if old_button:
                old_button.destroy()
        
        item_button = self.do_bake_item_button(item)
        
        self.buttons_by_id[identifier] = item_button
        self.items_by_id[identifier] = item

        try:
            # Connect to a signal that indicates the item's properties (like icon) have changed.
            # 'updated' is a common name for such a signal. If this is not correct for Gray.Item,
            # it might be 'new-icon', 'notify::icon-name', or another GObject signal.
            # The lambda captures 'identifier', 'item', and 'item_button' from this scope.
            item.connect("updated", lambda updated_item_obj: self._refresh_item_ui(identifier, updated_item_obj, item_button))
        except TypeError as e:
            logger.error(f"Failed to connect 'updated' signal for item {identifier}: {e}. Icon/tooltip updates on-the-fly may not work.")

        # Connect to the item's 'removed' signal.
        # The lambda captures 'identifier' and the specific 'item' instance.
        item.connect("removed", lambda removed_item_obj: self.on_item_instance_removed(identifier, removed_item_obj))
        
        self.add(item_button)
        item_button.show_all()
        self._update_visibility()

    def do_bake_item_button(self, item: Gray.Item) -> Gtk.Button:
        button = Gtk.Button()
        # The '_item=item' in lambda captures the current 'item' instance for this button.
        button.connect(
            "button-press-event",
            lambda btn_widget, event, _item=item: self.on_button_click(btn_widget, _item, event),
        )

        pixbuf = self._get_item_pixbuf(item)
        image = Gtk.Image.new_from_pixbuf(pixbuf)
        button.set_image(image)
        
        # Set initial tooltip
        tooltip_text = None
        if hasattr(item, 'get_tooltip_text'): # Check if method exists
            tooltip_text = item.get_tooltip_text()
        elif hasattr(item, 'get_title'): # Fallback to title for tooltip
            tooltip_text = item.get_title()
        
        if tooltip_text:
            button.set_tooltip_text(tooltip_text)
        
        return button

    def on_item_instance_removed(self, identifier: str, removed_item_instance: Gray.Item):
        """Called when a specific Gray.Item instance signals it's 'removed'."""
        logger.debug(f"Item instance 'removed' signal for ID '{identifier}' (instance: {removed_item_instance})")
        
        current_tracked_item = self.items_by_id.get(identifier)
        
        # Only remove the button if the 'removed' signal is from the currently tracked item instance for this ID.
        if current_tracked_item is removed_item_instance:
            button_to_remove = self.buttons_by_id.pop(identifier, None)
            self.items_by_id.pop(identifier, None) # Clean up items_by_id as well
            
            if button_to_remove:
                logger.debug(f"Destroying button for item ID '{identifier}' due to 'removed' signal.")
                button_to_remove.destroy()
            else:
                # This might happen if the button was already removed due to a re-add.
                logger.debug(f"No button found in buttons_by_id for '{identifier}' during its 'removed' signal processing. It might have been replaced.")
            
            self._update_visibility()
        else:
            # This 'removed' signal is for an old item instance that is no longer the primary one for this ID,
            # or for an item that was never fully registered / already cleaned up.
            logger.debug(f"Received 'removed' signal for an outdated/mismatched item instance for ID '{identifier}'. "
                         f"Tracked: {current_tracked_item}, Signaled: {removed_item_instance}. Usually, no action needed.")


    def on_button_click(self, button: Gtk.Button, item: Gray.Item, event: Gdk.EventButton):
        # 'item' here is the specific Gray.Item instance associated with 'button' at creation.
        if event.button == Gdk.BUTTON_PRIMARY:  # Left click
            try:
                item.activate(int(event.x_root), int(event.y_root)) # SNI expects root coordinates
            except Exception as e:
                item_id_for_log = identifier if 'identifier' in locals() else (item.get_icon_name() if hasattr(item, 'get_icon_name') else 'unknown')
                logger.error(f"Error activating item (ID/Name: {item_id_for_log}): {e}")
        elif event.button == Gdk.BUTTON_SECONDARY:  # Right click
            menu = item.get_menu()
            if menu and isinstance(menu, Gtk.Menu): # Ensure menu is a Gtk.Menu
                menu.set_name("system-tray-menu") # For styling
                # The popup_at_widget function positions the menu relative to the button.
                menu.popup_at_widget(
                    button,
                    Gdk.Gravity.SOUTH_WEST, # Usual gravity for menus
                    Gdk.Gravity.NORTH_WEST,
                    event, # Pass the event to allow Gtk to position correctly
                )
            else: # Fallback if item.get_menu() is not the primary way or returns non-Gtk.Menu
                if hasattr(item, 'context_menu'):
                    try:
                        item.context_menu(int(event.x_root), int(event.y_root)) # SNI expects root coordinates
                    except Exception as e:
                        item_id_for_log = identifier if 'identifier' in locals() else (item.get_icon_name() if hasattr(item, 'get_icon_name') else 'unknown')
                        logger.error(f"Error showing context menu for item (ID/Name: {item_id_for_log}): {e}")
                else:
                    logger.warning(f"Item has no Gtk.Menu from get_menu() and no context_menu method.")
